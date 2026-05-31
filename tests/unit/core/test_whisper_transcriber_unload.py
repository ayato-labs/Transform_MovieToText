import unittest
from unittest.mock import MagicMock, patch
import sys

# We will use patch to avoid global side effects
class TestWhisperTranscriberUnload(unittest.TestCase):
    @patch('src.core.whisper_transcriber.time.sleep')
    @patch('src.core.whisper_transcriber.gc.collect')
    def test_unload_memory_safety(self, mock_gc, mock_sleep):
        # We need to mock WhisperModel as well since it's imported at module level 
        # but used in methods we might call or that might be triggered.
        with patch('src.core.whisper_transcriber.WhisperModel'), \
             patch('src.core.whisper_transcriber.is_android', return_value=False), \
             patch('src.core.whisper_transcriber._is_cuda_available', return_value=True):
            
            from src.core.whisper_transcriber import WhisperTranscriber
            
            # Setup mock transcriber
            transcriber = WhisperTranscriber(cache_dir="dummy/path")
            transcriber.model = MagicMock()
            transcriber.current_model_name = "test-model"
            
            # Call unload
            transcriber.unload()
            
            # 1. Verify model reference is cleared safely (not using del, but assignment to None)
            self.assertIsNone(transcriber.model)
            self.assertIsNone(transcriber.current_model_name)
            
            # 2. Verify sleep was called to allow C++ backend to release handles
            mock_sleep.assert_called_once_with(0.1)
            
            # 3. Verify garbage collection was triggered
            mock_gc.assert_called_once()

if __name__ == "__main__":
    unittest.main()
