import logging
import os
import threading
from datetime import datetime

from src.config_manager import ConfigManager
from src.core.history_mgr import history_mgr
from src.core.state import state
from src.live_processor import LiveTranscriptionManager
from src.llm.factory import LLMFactory
from src.recorder.visual_recorder import visual_recorder
from src.transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


class TranscriptionController:
    def __init__(self, config_mgr: ConfigManager, transcriber: WhisperTranscriber):
        self.config_mgr = config_mgr
        self.transcriber = transcriber
        self.live_mgr = None

    def start_file_transcription(self, file_path: str, model_name: str):
        # ... (no change here)
        if not file_path:
            return

        state.set("is_processing", True)
        state.set("status_text", "文字起こし中... (初回モデルDL時は時間がかかります)")
        state.set("progress_visible", True)

        def _worker():
            try:
                force_gpu = self.config_mgr.get_force_gpu()
                self.transcriber.load_model(model_name, force_gpu=force_gpu)

                if self.transcriber.last_warning:
                    state.set("gpu_warning", f"⚠️ {self.transcriber.last_warning}")
                else:
                    state.set("gpu_warning", "")

                result = self.transcriber.transcribe(file_path, model_name=model_name, force_gpu=force_gpu, language="ja")
                state.set("transcript_text", result)
                state.set("status_text", "文字起こし完了")
            except Exception as e:
                logger.error(f"Transcription error: {e}", exc_info=True)
                state.set("status_text", f"エラー: {e}")
            finally:
                state.set("is_processing", False)
                state.set("progress_visible", False)

        threading.Thread(target=_worker, daemon=True).start()

    def toggle_live_recording(self, model_name: str, source: str):
        if state.get("is_recording"):
            self.stop_live_recording()
        else:
            self.start_live_recording(model_name, source)

    def start_live_recording(self, model_name: str, source: str):
        state.set("is_recording", True)
        source_label = "システム音" if source == "system" else "マイク"
        state.set("status_text", f"{source_label}をリアルタイム録音・文字起こし中...")
        state.set("transcript_text", "")

        force_gpu = self.config_mgr.get_force_gpu()

        try:
            self.transcriber.load_model(model_name, force_gpu=force_gpu)
            if self.transcriber.last_warning:
                state.set("gpu_warning", f"⚠️ {self.transcriber.last_warning}")
            else:
                state.set("gpu_warning", "")

            from src.core.utils import sanitize_filename

            project_raw = state.get("project_name", "")
            if not project_raw or project_raw.strip() == "":
                project_raw = "その他"

            project_name = sanitize_filename(project_raw)
            category = state.get("category", "")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamp_ui = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 1. Create Placeholder Meeting in DB to get an ID
            meeting_id = history_mgr.add_meeting(
                title=f"会議録音 ({timestamp_ui})", transcript="", audio_path="", model_info=model_name, project_name=project_name, category=category
            )
            state.set("current_meeting_id", meeting_id)

            # 2. Setup audio path
            from src.core.constants import DEFAULT_RECORDS_DIR

            base_dir = project_name if project_name else "default"
            mp3_dir = os.path.join(os.getcwd(), DEFAULT_RECORDS_DIR, base_dir)
            os.makedirs(mp3_dir, exist_ok=True)

            mp3_path = os.path.join(mp3_dir, f"meeting_{timestamp}.mp3")
            state.set("current_mp3_path", mp3_path)

            # 3. Start Recorders
            self.live_mgr = LiveTranscriptionManager(
                transcriber=self.transcriber,
                model_name=model_name,
                force_gpu=force_gpu,
                on_text_added=self._on_live_text_added,
                source=source,
                mp3_path=mp3_path,
                language="ja",  # Force Japanese to avoid multilingual hallucinations
            )
            self.live_mgr.start()

            # Visual Recorder (Optional)
            if self.config_mgr.get_visual_capture_enabled():
                visual_recorder.start(meeting_id)
            else:
                logger.info("Visual capture is disabled. Skipping Screen capture.")

        except Exception as e:
            logger.error(f"Live recording start error: {e}")
            state.set("status_text", f"エラー: {e}")
            state.set("is_recording", False)

    def stop_live_recording(self):
        if not self.live_mgr:
            return

        state.set("status_text", "録音を終了し、最後のチャンクを処理中...")
        state.set("is_recording", False)

        # Stop Visual Recorder immediately
        visual_recorder.stop()

        def _stop_worker():
            full_text = self.live_mgr.stop()
            mp3_path = self.live_mgr.mp3_path
            meeting_id = state.get("current_meeting_id")
            category = state.get("category", "")

            # 2. Extract Category if empty
            if not category or category.strip() == "":
                try:
                    state.set("status_text", "内容からカテゴリーを自動抽出中...")
                    provider = self.config_mgr.get_active_provider()
                    conf = self.config_mgr.get_provider_config(provider)
                    llm_client = LLMFactory.create_client(provider, api_key=conf.get("api_key"), base_url=conf.get("base_url"))
                    # We use the same model as for minutes, or fallback to a fast one if needed
                    llm_model = self.config_mgr.get_last_model()
                    auto_category = llm_client.extract_category(full_text, llm_model)
                    category = auto_category
                    state.set("category", category)  # Reflect back to state
                except Exception as e:
                    logger.error(f"Failed to auto-extract category: {e}")
                    category = "未分類"

            # 3. Finalize record in DB
            history_mgr.update_meeting(
                meeting_id,
                transcript=full_text,
                audio_path=mp3_path,
                category=category,  # Update with auto-extracted category
            )

            state.set("transcript_text", full_text)
            state.set("status_text", f"ライブ文字起こし完了（大分類: {category}）")
            self.live_mgr = None

        threading.Thread(target=_stop_worker, daemon=True).start()

    def _on_live_text_added(self, text):
        current_text = state.get("transcript_text", "")
        # Very simple append logic
        state.set("transcript_text", current_text + text + " ")
