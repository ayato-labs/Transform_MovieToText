import logging
import os
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.live_processor import LiveTranscriptionManager

from src.core.config_manager import ConfigManager
from src.core.event_bus import (
    EVENT_STATUS_UPDATE,
    EVENT_TRANSCRIPTION_FINISHED,
    EVENT_TRANSCRIPTION_PROGRESS,
    event_bus,
)
from src.core.history_mgr import history_mgr as _history_mgr
from src.core.whisper_transcriber import WhisperTranscriber
from src.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Handles business logic for transcription workflows.
    Decoupled from UI state.
    """

    def __init__(self, config_mgr: ConfigManager, transcriber: WhisperTranscriber, history_mgr=None):
        self.config_mgr = config_mgr
        self.transcriber = transcriber
        self.history_mgr = history_mgr or _history_mgr
        self.live_mgr: LiveTranscriptionManager | None = None
        self._live_start_time: float | None = None
        self._current_meeting_id: int | None = None
        self._current_mp3_path: str | None = None
        # Cancel flag: set immediately when stop is requested, even during model loading
        self._cancel_event = threading.Event()

    def transcribe_file_sync(
        self,
        file_path: str,
        model_name: str,
        language: str | None = None,
        project_name: str = "その他",
        category: str = "",
        progress_callback: Callable[[float], None] | None = None,
        use_visual: bool = False,
    ) -> dict:
        """Synchronously transcribes a file and saves it to history."""
        logger.info(f"transcribe_file_sync: Starting for {file_path} (model={model_name}, project={project_name}, visual={use_visual})")
        if not file_path or not os.path.exists(file_path):
            logger.error(f"transcribe_file_sync: File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        force_gpu = self.config_mgr.get_force_gpu()
        event_bus.publish(EVENT_STATUS_UPDATE, f"モデル読み込み中 (GPU={force_gpu})...")
        self.transcriber.load_model(model_name, force_gpu=force_gpu)

        event_bus.publish(EVENT_STATUS_UPDATE, "文字起こし実行中...")

        def _internal_progress(progress):
            event_bus.publish(EVENT_TRANSCRIPTION_PROGRESS, progress)
            if progress_callback:
                progress_callback(progress)

        result_data = self.transcriber.transcribe(
            file_path, model_name=model_name, force_gpu=force_gpu, language=language, progress_callback=_internal_progress
        )
        full_text = result_data["text"]
        segments = result_data["segments"]

        logger.info("transcribe_file_sync: Transcription core finished.")

        visual_contexts = []
        if use_visual and file_path.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            event_bus.publish(EVENT_STATUS_UPDATE, "映像コンテキスト抽出中...")
            try:
                visual_contexts = self.extract_visual_frames(file_path)
            except Exception as e:
                logger.warning(f"Failed to extract visual frames: {e}")

        # Auto-save to history
        from pathlib import Path
        from src.core.constants import DEFAULT_RECORDS_DIR
        from src.core.utils import sanitize_filename

        safe_project = sanitize_filename(project_name or "その他")
        records_dir = Path.cwd().joinpath(*DEFAULT_RECORDS_DIR.split("/")).joinpath(safe_project)
        records_dir.mkdir(parents=True, exist_ok=True)

        base_name = os.path.basename(file_path)
        final_file_path = str(records_dir / base_name)

        if os.path.abspath(file_path) != os.path.abspath(final_file_path):
            import shutil

            logger.info(f"transcribe_file_sync: Copying {file_path} to {final_file_path}")
            shutil.copy2(file_path, final_file_path)

        # 1. Generate AI Title & Category
        event_bus.publish(EVENT_STATUS_UPDATE, "タイトル自動生成中...")
        ai_title = ""
        try:
            ai_title = self._generate_title_internal(full_text)
            if not category:
                category = self._extract_category_internal(full_text)
        except Exception as e:
            logger.warning(f"AI Title/Category generation failed for file: {e}")

        final_title = f"{ai_title} ({base_name})" if ai_title else f"ファイル文字起こし: {base_name}"

        meeting_id = self.history_mgr.add_meeting(
            title=final_title,
            transcript=full_text,
            transcript_segments=segments,
            audio_path=final_file_path,
            model_info=model_name,
            project_name=safe_project,
            category=category,
        )

        # Save visual contexts
        for ctx in visual_contexts:
            self.history_mgr.add_visual_context(meeting_id=meeting_id, timestamp_sec=ctx["timestamp_sec"], image_path=ctx["image_path"])

        event_bus.publish(EVENT_TRANSCRIPTION_FINISHED, {"meeting_id": meeting_id, "text": full_text})
        return {"transcript": full_text, "segments": segments, "visual_contexts": visual_contexts, "meeting_id": meeting_id}

    def extract_visual_frames(self, video_path: str, interval_sec: float = 10.0) -> list[dict]:
        """Extracts significant frames from a video file as visual context."""
        from pathlib import Path

        import cv2

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        from src.core.constants import TEMP_VIDEO_DIR

        temp_dir = Path(TEMP_VIDEO_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)

        contexts = []
        curr_sec = 0.0
        while curr_sec < duration:
            cap.set(cv2.CAP_PROP_POS_MSEC, curr_sec * 1000)
            ret, frame = cap.read()
            if not ret:
                break

            frame_path = temp_dir / f"frame_{curr_sec:.1f}s.jpg"
            cv2.imwrite(str(frame_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])

            contexts.append({"image_path": str(frame_path), "timestamp_sec": curr_sec})
            curr_sec += interval_sec

        cap.release()
        logger.info(f"extract_visual_frames: Extracted {len(contexts)} frames.")
        return contexts

    def start_live_recording(
        self,
        model_name: str,
        source: str,
        language: str | None = None,
        project_name: str = "その他",
        category: str = "",
        on_text_added: Callable[[str], None] | None = None,
    ) -> int:
        """Starts a live recording session. Returns meeting_id."""
        logger.info(f"start_live_recording: Request for {model_name} (project={project_name})")
        event_bus.publish(EVENT_STATUS_UPDATE, "🔄 準備中... (機材の初期化とモデルのロード)")

        # 1. Start Model Loading in Background
        # We don't wait for this to finish to start the recorder.
        # This keeps the 'Stop' button responsive from the very first second.
        force_gpu = self.get_config().get_force_gpu() if hasattr(self, "get_config") else self.config_mgr.get_force_gpu()

        def _load_model_worker():
            try:
                logger.info(f"_load_model_worker: Starting async load for {model_name}...")
                self.transcriber.load_model(model_name, force_gpu=force_gpu)
                logger.info("_load_model_worker: Async load finished.")
            except Exception as e:
                logger.error(f"_load_model_worker: Failed to load model: {e}")

        threading.Thread(target=_load_model_worker, daemon=True).start()

        # 2. Prepare Storage and Metadata Immediately
        logger.info("start_live_recording: Preparing storage...")
        from src.core.utils import sanitize_filename

        safe_project = sanitize_filename(project_name or "その他")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_ui = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Create Placeholder
        meeting_id = self.history_mgr.add_meeting(
            title=f"会議録音 ({timestamp_ui})", transcript="", audio_path="", model_info=model_name, project_name=safe_project, category=category
        )
        self._current_meeting_id = meeting_id
        self._live_start_time = time.time()

        # 2. Setup audio path
        from src.core.constants import DEFAULT_RECORDS_DIR

        mp3_dir = os.path.join(os.getcwd(), DEFAULT_RECORDS_DIR, safe_project)
        os.makedirs(mp3_dir, exist_ok=True)
        mp3_path = os.path.join(mp3_dir, f"meeting_{timestamp}.mp3")
        self._current_mp3_path = mp3_path

        # 3. Start Recorders
        logger.info(f"start_live_recording: Initializing LiveTranscriptionManager (mp3={mp3_path})")
        from src.core.live_processor import LiveTranscriptionManager

        self.live_mgr = LiveTranscriptionManager(
            transcriber=self.transcriber,
            model_name=model_name,
            force_gpu=force_gpu,
            on_text_added=on_text_added,
            source=source,
            mp3_path=mp3_path,
            language=language,
        )
        self.live_mgr.start()
        event_bus.publish(EVENT_STATUS_UPDATE, "🔴 録音中...")

        # Visual Recorder
        if self.config_mgr.get_visual_capture_enabled():
            logger.info("start_live_recording: Starting VisualRecorder.")
            from src.recorder.visual_recorder import visual_recorder

            visual_recorder.start(meeting_id)

        logger.info(f"start_live_recording: Successfully started session (id={meeting_id})")
        return meeting_id

    def stop_live_recording(self, finalize_callback: Callable[[str, str], None] | None = None):
        """Stops live recording and finalizes results in background."""
        logger.info("stop_live_recording: Stop command received.")
        event_bus.publish(EVENT_STATUS_UPDATE, "⏹️ 停止中... (最終処理と保存を実行中)")
        # Always set the cancel flag FIRST, regardless of live_mgr state.
        # This handles the race condition where stop is called during model loading.
        self._cancel_event.set()
        logger.info("stop_live_recording: Cancel event set.")

        if not self.live_mgr:
            # Was called during model loading; the cancel flag will abort start_live_recording.
            # Notify the caller that we've been cancelled cleanly.
            logger.warning("stop_live_recording: live_mgr not ready yet (likely still loading model); cancellation queued.")
            if finalize_callback:
                finalize_callback("", "")
            return

        logger.info("stop_live_recording: Terminating recorders and starting finalization...")
        from src.recorder.visual_recorder import visual_recorder

        visual_recorder.stop()

        def _finalize_worker():
            logger.info("_finalize_worker: Starting background finalization...")
            full_text = ""
            category = ""
            try:
                full_text, all_segments = self.live_mgr.stop()
                logger.info(f"_finalize_worker: live_mgr stopped. Text length: {len(full_text)}, Segments: {len(all_segments)}")
                meeting_id = self._current_meeting_id
                mp3_path = self._current_mp3_path
                duration = time.time() - (self._live_start_time or time.time())

                if duration >= 30 and full_text.strip():
                    # Auto-category and title extraction
                    category = ""
                    ai_title = ""
                    try:
                        category = self._extract_category_internal(full_text)
                    except Exception as e:
                        logger.warning(f"Category extraction failed: {e}")
                        category = "未分類"

                    try:
                        ai_title = self._generate_title_internal(full_text)
                    except Exception as e:
                        logger.warning(f"AI Title generation failed: {e}")

                    timestamp_ui = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    final_title = f"{ai_title} ({timestamp_ui})" if ai_title else f"会議録音 ({timestamp_ui})"

                    self.history_mgr.update_meeting(
                        meeting_id, title=final_title, transcript=full_text, transcript_segments=all_segments, audio_path=mp3_path, category=category
                    )
                else:
                    logger.info(f"Recording discarded (duration={duration:.1f}s)")
                    if meeting_id:
                        self.history_mgr.delete_meeting(meeting_id)

                if finalize_callback:
                    finalize_callback(full_text, category)

                # Publish finish event so UI knows processing is done
                event_bus.publish(EVENT_TRANSCRIPTION_FINISHED, {"text": full_text})

            except Exception as e:
                logger.error(f"Error finalizing live recording: {e}", exc_info=True)
            finally:
                self.live_mgr = None
                self._live_start_time = None
                self._current_meeting_id = None
                self._current_mp3_path = None

        threading.Thread(target=_finalize_worker, daemon=True).start()

    def generate_minutes_for_meeting(self, meeting_id: int, transcript: str, provider: str | None = None, model: str | None = None) -> str:
        """Generates minutes for an existing meeting and updates the record."""
        if not transcript or len(transcript.strip()) < 50:
            raise ValueError("文字起こしデータが不足しています（50文字以上必要です）。")

        active_provider = provider or self.config_mgr.get_active_provider()
        conf = self.config_mgr.get_provider_config(active_provider)
        llm_client = LLMFactory.create_client(active_provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
        llm_model = model or self.config_mgr.get_last_model()

        # Fetch visual context if available
        visual_contexts = self.history_mgr.get_visual_context(meeting_id)
        image_paths = [ctx["image_path"] for ctx in visual_contexts]

        # Generate minutes using the client directly
        minutes = llm_client.generate_minutes(transcript=transcript, model_name=llm_model, image_paths=image_paths)

        # Update history
        self.history_mgr.update_minutes(meeting_id, minutes, model_name=llm_model)

        return minutes

    def _get_best_llm_model(self, provider: str) -> str:
        """Helper to find the best available LLM model for the given provider."""
        # Try to get from config first
        model = self.config_mgr.get_provider_config(provider).get("model")
        if model:
            return model

        # Fallback to defaults or first available
        try:
            conf = self.config_mgr.get_provider_config(provider)
            client = LLMFactory.create_client(provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
            available = client.get_available_models()
            if available:
                return available[0]
        except Exception as e:
            logger.debug(f"_get_best_llm_model: Automated model lookup failed for {provider}: {e}")

        # Hardcoded defaults as last resort
        defaults = {"gemini": "gemini-1.5-flash", "google": "gemini-1.5-flash", "ollama_local": "llama3", "ollama_cloud": "llama3"}
        return defaults.get(provider, "gemini-1.5-flash")

    def _extract_category_internal(self, text: str) -> str:
        provider = self.config_mgr.get_active_provider()
        llm_model = self._get_best_llm_model(provider)

        logger.info(f"_extract_category_internal: Using {provider}/{llm_model} for tagging.")
        conf = self.config_mgr.get_provider_config(provider)
        llm_client = LLMFactory.create_client(provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))

        category = llm_client.extract_category(text, llm_model)
        logger.info(f"_extract_category_internal: Result -> {category}")
        return category

    def _generate_title_internal(self, text: str) -> str:
        if not text or len(text.strip()) < 50:
            return ""
        provider = self.config_mgr.get_active_provider()
        llm_model = self._get_best_llm_model(provider)

        logger.info(f"_generate_title_internal: Using {provider}/{llm_model} for titling.")
        conf = self.config_mgr.get_provider_config(provider)
        llm_client = LLMFactory.create_client(provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))

        title = llm_client.generate_title(text, llm_model)
        logger.info(f"_generate_title_internal: Result -> {title}")
        return title
