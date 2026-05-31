import unittest
import os
from unittest.mock import MagicMock, patch

from src.core.config_manager import ConfigManager
from src.core.history_mgr import HistoryManager
from src.platforms.desktop.controllers.transcription_ctrl import TranscriptionController
from src.platforms.desktop.controllers.minutes_ctrl import MinutesController

class TestGoldStandardWorkflow(unittest.TestCase):
    """
    Consolidated End-to-End System Test (The Golden Path).
    Verifies the core value chain: Transcription -> AI Transformation -> History Persistence.
    """

    def setUp(self):
        self.test_db = "tests/gold_standard.db"
        self.history_mgr = HistoryManager(self.test_db)
        self.config_mgr = ConfigManager()
        
        # Mock Transcriber Engine
        self.mock_transcriber = MagicMock()
        self.mock_transcriber.transcribe.return_value = {
            "text": "This is a pizza party meeting.",
            "segments": [{"start": 0.0, "end": 2.0, "text": "This is a pizza party meeting."}]
        }
        
        self.trans_ctrl = TranscriptionController(
            self.config_mgr, 
            self.mock_transcriber, 
            history_mgr=self.history_mgr
        )
        self.minutes_ctrl = MinutesController(self.config_mgr)
        # Inject our history_mgr into the minutes service
        self.minutes_ctrl.service.history_mgr = self.history_mgr

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    @patch("src.llm.factory.LLMFactory.create_client")
    def test_end_to_end_transcription_to_minutes(self, mock_create_client):
        """Tests the full flow from raw audio/file to AI generated minutes in history."""
        # 1. Setup Mock LLM
        mock_llm = MagicMock()
        mock_llm.generate_minutes.return_value = "## Pizza Meeting Minutes\n- Decided to add pineapple."
        mock_llm.generate_title.return_value = "Pizza Strategy"
        mock_llm.extract_category.return_value = "Food"
        mock_create_client.return_value = mock_llm

        # 2. Execute Transcription (The Core Action)
        with patch("shutil.copy2"), \
             patch("os.path.exists", return_value=True), \
             patch("os.path.abspath", side_effect=lambda x: x), \
             patch("src.core.transcription_service.TranscriptionService._generate_title_internal", return_value="Pizza Strategy"), \
             patch("src.core.transcription_service.TranscriptionService._extract_category_internal", return_value="Food"):
             
            result = self.trans_ctrl.service.transcribe_file_sync(
                "dummy_audio.mp3", 
                model_name="base",
                project_name="PizzaProject"
            )
        
        meeting_id = result.get("meeting_id")
        self.assertIsNotNone(meeting_id)
        
        # 3. Verify History Persistence
        meeting = self.history_mgr.get_meeting(meeting_id)
        self.assertEqual(meeting["title"], "Pizza Strategy (dummy_audio.mp3)")
        self.assertIn("pizza party", meeting["transcript"])

        # 4. Execute AI Transformation (Minutes Generation)
        self.minutes_ctrl.service.generate_minutes_sync(
            transcript=meeting["transcript"],
            provider="ollama_local",
            model="gemma4:e2b",
            meeting_id=meeting_id
        )
        
        # 5. Verify Final Output
        updated_meeting = self.history_mgr.get_meeting(meeting_id)
        self.assertEqual(updated_meeting["minutes"], "## Pizza Meeting Minutes\n- Decided to add pineapple.")

if __name__ == "__main__":
    unittest.main()
