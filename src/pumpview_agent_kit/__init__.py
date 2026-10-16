"""PumpView HTTP client. No custody, wallet-key loading, or automatic retries."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.pumpview.fun"
MCP_URL = BASE_URL + "/mcp/"


class PumpViewError(Exception):
    def __init__(self, status, detail, retry_after=None):
        self.status, self.detail, self.retry_after = status, detail, retry_after
        super().__init__(f"PumpView HTTP {status}: {detail}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API key or a signed transaction to another URL.
        return None


class PumpView:
    def __init__(self, api_key=None, *, timeout=65):
        self._api_key = api_key
        self.timeout = timeout
        self._http = urllib.request.build_opener(_NoRedirect())

    def _request(self, method, path, body=None, *, authenticated=True):
        headers = {"Accept": "application/json", "User-Agent": "pumpview-agent-kit/1.0.0"}
        if authenticated:
            if not self._api_key:
                raise ValueError("Set a PumpView API key before authenticated requests")
            headers["Authorization"] = "Bearer " + self._api_key
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
        try:
            with self._http.open(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Avoid echoing raw upstream responses, which might contain credentials.
            messages = {400: "Invalid request or signature", 401: "Authentication required",
                        402: "Data allowance required", 403: "Account or wallet not authorized",
                        409: "Conflict; reconcile the existing intent or invoice",
                        410: "Expired; reconcile any existing signature before replacing",
                        422: "Validation or simulation failed; inspect the intent and current policy",
                        429: "Rate limit exceeded", 503: "Service temporarily unavailable"}
            raise PumpViewError(error.code, messages.get(error.code, "Request failed"),
                                error.headers.get("Retry-After")) from None

    def trading_config(self):
        return self._request("GET", "/v1/swaps/config", authenticated=False)

    def wallet_challenge(self, wallet):
        return self._request("POST", "/v1/agent/challenge", {"wallet": wallet}, authenticated=False)

    def complete_wallet_access(self, wallet, nonce, signature, name="PumpView agent"):
        """signature is a base58 signature of the challenge's exact UTF-8 message.

        The returned key is a secret. Store it in a secret manager, never a log.
        """
        return self._request("POST", "/v1/agent/access",
                             dict(wallet=wallet, nonce=nonce, signature=signature, name=name), authenticated=False)

    def build_swap(self, intent):
        """Build only. Persist request_id before calling; reuse after a timeout."""
        if not isinstance(intent.get("amount"), str) or not re.fullmatch(r"[1-9][0-9]*", intent["amount"]):
            raise ValueError("amount must be a positive integer string in atomic units")
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", intent.get("request_id", "")):
            raise ValueError("Persist a unique 16-80 character request_id before building")
        return self._request("POST", "/v1/swaps/build", intent)

    @staticmethod
    def _swap_path(swap_id):
        if not re.fullmatch(r"[0-9a-f]{32}", swap_id):
            raise ValueError("Invalid PumpView swap ID")
        return "/v1/swaps/" + swap_id

    def submit_swap(self, swap_id, signed_transaction_base64):
        """Broadcast approved, externally signed bytes. This can spend funds.

        No implicit retries: after a timeout, query swap_status with this ID.
        """
        return self._request("POST", self._swap_path(swap_id) + "/submit",
                             {"signed_transaction_base64": signed_transaction_base64})

    def swap_status(self, swap_id):
        return self._request("GET", self._swap_path(swap_id))

    def trading_usage(self):
        return self._request("GET", "/v1/swaps/usage")

    def recent_trades(self, *, mint=None, wallet=None, after=None, limit=100):
        params = {k: v for k, v in dict(mint=mint, wallet=wallet, after=after, limit=limit).items() if v is not None}
        return self._request("GET", "/v1/trades?" + urllib.parse.urlencode(params))
