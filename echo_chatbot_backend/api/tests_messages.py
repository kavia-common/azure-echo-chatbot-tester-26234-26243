from rest_framework.test import APITestCase
from django.urls import reverse


class MessagesEndpointTests(APITestCase):
    # PUBLIC_INTERFACE
    def _valid_activity(self):
        return {
            "type": "message",
            "text": "hello",
            "from": {"id": "user1"},
            # recipient is optional for Emulator; adapter can populate
            "conversation": {"id": "conv1"},
            "channelId": "emulator",
            "serviceUrl": "http://localhost",
        }

    def test_messages_returns_200_for_valid_activity(self):
        url = reverse("bot-messages")
        payload = self._valid_activity()
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_emulator_bypasses_auth_even_with_header(self):
        url = reverse("bot-messages")
        payload = self._valid_activity()
        # Simulate Emulator sending an Authorization header (should be ignored)
        resp = self.client.post(
            url,
            data=payload,
            format="json",
            HTTP_AUTHORIZATION="Bearer fake.emulator.token"
        )
        self.assertEqual(resp.status_code, 200)

    def test_messages_returns_415_for_wrong_content_type(self):
        url = reverse("bot-messages")
        payload = '{"type":"message"}'
        # Send wrong content type
        resp = self.client.post(url, data=payload, content_type="text/plain")
        self.assertEqual(resp.status_code, 415)
        self.assertIn("Unsupported Media Type", str(resp.content))

    def test_messages_returns_400_for_malformed_json(self):
        url = reverse("bot-messages")
        bad_json = '{"type": "message", '  # malformed
        resp = self.client.post(url, data=bad_json, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"Invalid JSON payload", resp.content)

    def test_messages_returns_400_for_missing_required_field(self):
        url = reverse("bot-messages")
        payload = self._valid_activity()
        del payload["conversation"]
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"Missing required field", resp.content)

    def test_emulator_style_payload_random_port_and_no_recipient_returns_200(self):
        """
        Verify Emulator-style activity with random localhost port in serviceUrl,
        missing recipient, and no id fields returns 200.
        """
        url = reverse("bot-messages")
        payload = {
            "type": "message",
            "channelId": "emulator",
            "serviceUrl": "http://localhost:62157",
            "from": {"id": "emulatorUser"},
            "conversation": {"id": "emulatorConv"},
            "text": "Ping"
        }
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, 200)
