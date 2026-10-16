# Integration reference

## Access

Account users: https://pumpview.fun/developers#account → sign in → link the
signing wallet → create a dedicated key. Use `Authorization: Bearer <key>`.

Agents with an authorized local wallet can use REST without browser registration:

1. `POST /v1/agent/challenge` with `{"wallet":"PUBLIC_KEY"}`.
2. Verify the message identifies PumpView and that wallet; sign its exact UTF-8
   bytes locally. Encode the Ed25519 signature in base58 (not base64).
3. `POST /v1/agent/access` with wallet, returned nonce, signature and optional name.
   Store the returned `key` as a secret. Do not display the response in logs.

A challenge expires after 300 seconds and is single use. A linked wallet resolves
to its existing account. HTTP onboarding creates access; it does not authorize
spending or purchase a package. An MCP-only runtime must use an existing account
key if it cannot perform the HTTP wallet-proof exchange.

## Trade

`GET /v1/swaps/config` is public. Read it before building.

```json
{
  "request_id": "persist-a-unique-intent-id",
  "wallet": "YOUR_LINKED_PUBLIC_KEY",
  "input_mint": "USDC",
  "output_mint": "SOL",
  "amount": "10000000",
  "slippage_bps": 100,
  "tip_lamports": 2000000,
  "max_priority_fee_lamports": 1000000
}
```

Send the intent to `POST /v1/swaps/build`. The response's `transaction_base64`
is unsigned. Its `id` is the swap ID, different from your `request_id`.
Review the versioned transaction with the authorized wallet adapter. Sign the
exact message, then call `POST /v1/swaps/{id}/submit` with
`{"signed_transaction_base64":"..."}`. Persist the build/ID before signing
and persist the signed bytes securely before submission so a lost response does
not force rebuilding. Treat those bytes as sensitive until the blockhash expires.

Query `GET /v1/swaps/{id}`. `submitted` does not mean executed. At `confirmed`,
the receipt reports actual wallet changes, platform fee and network fee. Native
SOL balance changes also include tips and rent; they are not swap output alone.
Use `receipt.volume` for executed base-asset notional when present. Continue
polling if finalized settlement is needed.

For timeout/delivery uncertainty, query the same ID. A deliberate resubmission
uses the same signed bytes and same ID; never automatically sign a replacement.
For 429, honor Retry-After; space polling to stay within account limits. For 422,
review validation/simulation failure. For 410, inspect any existing signature
before the user authorizes a replacement intent.

Current defaults: 0.5% platform fee, tips from 0.002 SOL, $5 minimum without
Unlimited. One leg must be SOL/WSOL/USDC. Slippage is explicit; swaps are ExactIn.
Even USDC trades need SOL for network costs, tips and potentially account rent.

## Volume and live data

`GET /v1/swaps/usage` / MCP `get_trading_usage`: all-time confirmed volume for
the account and originating API key. Failed builds and repeated status polls
do not add volume. An unavailable response is not zero volume.

Live data uses `GET /v1/trades` or `wss://api.pumpview.fun/v1/stream`.
Read current plans at `/v1/plans`. A data subscription is separate from trading.
Payments use native USDC and PumpView invoices; Coinbase is not required.
Payment instructions and verification are documented in the authoritative
quickstart; never infer permission to pay from a data query or a 402 response.

All keys share one WSS connection and the account's HTTP/MCP rate limit.
Persist the replay cursor and deduplicate event_id; record a gap on expired
cursors. Existing suspicious-price filtering remains enabled. The feed covers
supported decoder SOL pairs, not an exhaustive Solana ledger.
