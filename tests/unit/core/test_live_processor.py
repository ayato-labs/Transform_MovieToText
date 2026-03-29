import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from src.live_processor import LiveTranscriptionManager


class TestLiveProcessor(unittest.TestCase):
    def setUp(self):
        self.mock_transcriber = MagicMock()
        self.mock_recorder = MagicMock()
        import queue

        self.mock_recorder.chunk_queue = queue.Queue()

        with patch("src.live_processor.create_recorder", return_value=self.mock_recorder):
            self.manager = LiveTranscriptionManager(transcriber=self.mock_transcriber, on_text_added=MagicMock())

    def test_handle_audio_data_numpy(self):
        # Create a dummy chunk with random noise to pass silence suppression
        audio_data = np.random.uniform(-0.1, 0.1, 16000).astype(np.float32)

        self.mock_transcriber.transcribe.return_value = "Hello numpy world"

        self.manager._handle_audio_data(audio_data)

        # Verify transcription was called with numpy array
        self.mock_transcriber.transcribe.assert_called()
        args, kwargs = self.mock_transcriber.transcribe.call_args
        self.assertTrue(isinstance(args[0], np.ndarray))
        self.assertEqual(kwargs["model_name"], "base")

        # Verify text was added to transcript
        self.assertIn("Hello numpy world", self.manager.full_transcript)
        # Verify callback was called
        self.manager.on_text_added.assert_called_with("Hello numpy world")

    def test_worker_loop_consumes_queue(self):
        # Push 2 chunks to recorder's queue with enough signal
        chunk1 = np.random.uniform(-0.1, 0.1, 8000).astype(np.float32)
        chunk2 = np.random.uniform(-0.1, 0.1, 8000).astype(np.float32)

        self.manager.recorder.chunk_queue.put(chunk1)
        self.manager.recorder.chunk_queue.put(chunk2)

        self.mock_transcriber.transcribe.side_effect = ["One", "Two"]

        # Set stop event so loop runs until queue is empty
        self.manager.stop_event.set()

        # Run the loop manually
        self.manager._process_chunks_loop()

        # Verify both chunks were processed
        self.assertEqual(self.manager.chunks_processed, 2)
        self.assertIn("One Two", self.manager.full_transcript)


if __name__ == "__main__":
    unittest.main()
