import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from pumpview_agent_kit import PumpView, PumpViewError, _NoRedirect


class ClientTests(unittest.TestCase):
    def test_public_policy_never_sends_configured_key(self):
        client = PumpView("secret-test-key")
        client._http = Mock()
        client._http.open.return_value = io.BytesIO(b'{"enabled":true}')
        self.assertTrue(client.trading_config()["enabled"])
        request = client._http.open.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))

    def test_build_preserves_intent_and_authentication(self):
        client = PumpView("secret-test-key")
        client._http = Mock()
        client._http.open.return_value = io.BytesIO(b'{"id":"abc"}')
        intent = dict(request_id="persistent-intent-0001", amount="9007199254740993", wallet="public")
        client.build_swap(intent)
        request = client._http.open.call_args.args[0]
        self.assertEqual(json.loads(request.data), intent)
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-test-key")
        self.assertEqual(client._http.open.call_count, 1)

    def test_rejects_ambiguous_amounts_and_invalid_ids_before_network(self):
        client = PumpView("key")
        client._http = Mock()
        for amount in (1.1, 10, "1.2", "0", "-1", "1e9"):
            with self.assertRaises(ValueError):
                client.build_swap(dict(amount=amount, request_id="persistent-intent-0001"))
        with self.assertRaises(ValueError):
            client.swap_status("../../v1/trades")
        client._http.open.assert_not_called()

    def test_submit_timeout_is_not_retried_or_rebuilt(self):
        client = PumpView("key")
        client._http = Mock()
        client._http.open.side_effect = URLError("timeout")
        with self.assertRaises(URLError):
            client.submit_swap("a" * 32, "same-signed-bytes")
        self.assertEqual(client._http.open.call_count, 1)
        request = client._http.open.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"signed_transaction_base64": "same-signed-bytes"})

    def test_server_error_keeps_retry_after_and_does_not_echo_secrets(self):
        client = PumpView("secret-test-key")
        client._http = Mock()
        client._http.open.side_effect = HTTPError("https://api.pumpview.fun", 429, "limit", {"Retry-After": "2"}, io.BytesIO(b'secret-test-key'))
        with self.assertRaises(PumpViewError) as result:
            client.trading_usage()
        self.assertEqual(result.exception.retry_after, "2")
        self.assertNotIn("secret-test-key", str(result.exception))

    def test_redirect_cannot_forward_key_or_signed_bytes(self):
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 307, "", {}, "https://example.org"))

    def test_missing_key_fails_before_network(self):
        client = PumpView()
        client._http = Mock()
        with self.assertRaises(ValueError):
            client.trading_usage()
        client._http.open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
