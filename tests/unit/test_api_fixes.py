import unittest
from unittest.mock import MagicMock, patch
from heart_speaks.repository import get_user_chat_logs, delete_chat_log, delete_bookmark

class TestNewFeatures(unittest.TestCase):
    @patch("heart_speaks.repository.get_firestore_client")
    def test_get_user_chat_logs(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_query = mock_db.collection.return_value.where.return_value.order_by.return_value.limit.return_value
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"question": "Q", "response": "R", "user_id": "u1"}
        mock_doc.id = "doc1"
        mock_query.stream.return_value = [mock_doc]
        
        logs = get_user_chat_logs("u1")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["id"], "doc1")

    @patch("heart_speaks.repository.get_firestore_client")
    def test_delete_chat_log_ownership(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_doc_ref = mock_db.collection.return_value.document.return_value
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"user_id": "u1"}
        mock_doc_ref.get.return_value = mock_doc
        
        # Test deletion by owner
        success = delete_chat_log("log1", user_id="u1")
        self.assertTrue(success)
        mock_doc_ref.delete.assert_called_once()
        
        # Test deletion by non-owner
        mock_doc_ref.delete.reset_mock()
        success = delete_chat_log("log1", user_id="u2")
        self.assertFalse(success)
        mock_doc_ref.delete.assert_not_called()

    @patch("heart_speaks.repository.get_firestore_client")
    def test_delete_bookmark_with_slashes(self, mock_get_db):
        # This test ensures the doc_id generation and delete call are triggered
        # even with slashes in the source_file.
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        source_file = "1991/August/Whisper.pdf"
        delete_bookmark("u1", source_file)
        
        # Verify document() was called with some hash (we don't check exact hash here as it's md5)
        self.assertTrue(mock_db.collection.return_value.document.called)
        mock_db.collection.return_value.document.return_value.delete.assert_called_once()

if __name__ == "__main__":
    unittest.main()
