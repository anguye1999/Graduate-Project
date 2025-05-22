import unittest
from unittest.mock import patch, MagicMock
from app import app

class TestOpenAIChatEndpoint(unittest.TestCase):

    @patch("app.client")
    def test_chat_endpoint_with_mocked_openai(self, mock_openai):
        # Setup mocks for OpenAI Assistant API
        mock_thread = MagicMock()
        mock_thread.id = "mock-thread-id"
        mock_openai.beta.threads.create.return_value = mock_thread

        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = [MagicMock(type="text", text=MagicMock(value="Take COSC 237 next."))]

        mock_openai.beta.threads.messages.list.return_value.data = [mock_message]

        mock_run = MagicMock()
        mock_run.id = "mock-run-id"
        mock_openai.beta.threads.runs.create.return_value = mock_run
        mock_openai.beta.threads.runs.retrieve.return_value.status = "completed"

        # Use Flask test client to simulate POST request
        with app.test_client() as client:
            response = client.post("/api/chat", json={
                "message": "What should I take after COSC 236?",
                "session_id": "test123"
            })

            data = response.get_json()

            self.assertEqual(response.status_code, 200)
            self.assertIn("Take COSC 237 next", data["message"])