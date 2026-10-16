<p align="center"><img src="https://pumpview.fun/static/favicon.svg" width="64" alt="PumpView"></p>

# PumpView Agent Kit

**Solana trading and live trade data for AI agents.** Build a swap, sign locally,
submit through PumpView, and read the execution receipt from confirmed onward.

[Trading API](https://pumpview.fun/solana-trading-api) ·
[Dashboard](https://pumpview.fun/developers#account) ·
[Quickstart](https://pumpview.fun/developers/quickstart) ·
[OpenAPI](https://api.pumpview.fun/v1/openapi.json)

Listed in the [official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers/fun.pumpview%2Ftrading/versions/latest)
as `fun.pumpview/trading`. The hosted server uses the verified `pumpview.fun` domain namespace.
Also available in the [Glama MCP directory](https://glama.ai/mcp/connectors/fun.pumpview.api/pump-view-solana-trading-and-live-data).

## Connect an agent

Install the skill from this repository:

```sh
npx skills add grinchdev/pumpview-agent-kits --skill pumpview-trading
```

Or configure a remote MCP connection in a client that supports custom headers:

```text
URL: https://api.pumpview.fun/mcp/
Transport: Streamable HTTP
Authorization: Bearer <PUMPVIEW_API_KEY>
```

Header configuration syntax depends on your client. PumpView uses API keys,
not OAuth. Keep the real key in your client's secret store. Initialization,
tool discovery and trading configuration are public; account operations require
your key. Installing a skill does not create an account or authorize spending.

Try public discovery without a key (Node 18+):

```sh
node examples/mcp-discovery.mjs
```

## Get access

**Existing PumpView account:** sign in to the
[dashboard](https://pumpview.fun/developers#account), link your signing wallet
and create an API key.

**Agent-owned wallet:** request `/v1/agent/challenge`, sign its exact message
locally and exchange the signature at `/v1/agent/access`. This creates a key
without browser registration. See the
[wallet onboarding reference](skills/pumpview-trading/references/workflow.md).
Never send PumpView a private key or seed phrase.

## Python client

Python 3.10+; the client has no runtime dependencies. Install from a local clone:

```sh
git clone https://github.com/grinchdev/pumpview-agent-kits.git
cd pumpview-agent-kits
python -m pip install -e .
```

Load `PUMPVIEW_API_KEY` through your environment or secret manager, then build
an unsigned 0.06 SOL → USDC swap with 1% slippage:

```sh
python examples/build_swap.py --wallet YOUR_LINKED_PUBLIC_KEY --output USDC --amount 60000000 --slippage-bps 100 --state state/intent-001.json
```

The example persists its request ID before contacting PumpView. Run it with the
same file and arguments to recover after a build timeout. It only builds and
simulates; it never signs or submits. USD minimum checks use current prices, so
the amount in this example may need adjustment before starting a new intent.

The client also provides `wallet_challenge`, `complete_wallet_access`,
`trading_config`, `swap_status`, `trading_usage`, `recent_trades`, and
`submit_swap`. **`submit_swap` broadcasts a transaction and can spend funds.**
Supply only bytes reviewed and signed by the user's authorized local wallet.

```python
import os
from pumpview_agent_kit import PumpView

client = PumpView(os.environ["PUMPVIEW_API_KEY"])
policy = client.trading_config()
volume = client.trading_usage()
# Recover a known submission without creating or sending another trade:
# receipt = client.swap_status(saved_swap_id)
```

For TypeScript, `examples/build_swap.mts` runs directly on Node 22.18+.
Provide `PUMPVIEW_API_KEY`, `PUMPVIEW_WALLET`, `PUMPVIEW_OUTPUT`,
`PUMPVIEW_AMOUNT`, `PUMPVIEW_SLIPPAGE_BPS` and a **previously persisted**
`PUMPVIEW_REQUEST_ID`; `PUMPVIEW_INPUT` defaults to SOL. Run
`node examples/build_swap.mts`. This example also only builds/simulates.

## Trading workflow

1. Read `/v1/swaps/config` for availability, supported pairs and current costs.
2. Persist a unique request ID and exact intent. Build with REST or MCP.
3. Review the returned versioned message, minimum output, fees and tips against
   the approved intent; sign the exact message using your own wallet adapter.
4. Persist the build ID and signed bytes securely. Submit the signed transaction.
5. Poll the same swap ID. A `submitted` response is not execution. Receipts start
   at `confirmed`; continue polling when you need `finalized` settlement.

The SDK deliberately has **no automatic request retries or wallet signer**.
After a build timeout, reuse the request ID; after a submit timeout, query the
same swap ID. Do not automatically change the blockhash or create a replacement.
Honor `Retry-After` on 429. The full
[integration reference](skills/pumpview-trading/references/workflow.md) covers
authentication, recovery and atomic units.

## Costs and supported pairs

- Trading API access has no subscription charge. Executed swaps have a **0.5%
  platform fee**, plus tips and network costs. Minimum tips: **0.002 SOL**.
- At least one leg must be **SOL, WSOL or native Solana USDC**. Other TOKEN–TOKEN
  swaps and wrapping-only SOL–WSOL requests are unsupported. Routing uses Jupiter;
  availability depends on the token and current pools.
- `SOL` means native SOL with wrap/unwrap; `WSOL` means the SPL token balance.
  ExactIn amounts are integer strings in atomic units; slippage is explicit.
- Minimum swap: **$5 equivalent** without Unlimited. Unlimited removes that
  minimum. All trades still require enough SOL for costs and applicable rent.
- PumpView sends through its landing infrastructure to 4 validators simultaneously
  with MEV protection. PumpView reports measured inclusion in the current block
  under 100 ms; this is its own benchmark, not a confirmed/finalized timing SLA.
- Authenticated HTTP and MCP calls share **3 / 5 / 20 requests per second per
  account** for Free or Day Pass / Starter / Unlimited. Keys do not multiply limits.

## Live data and volume

Trading and live-data access are separate. Data requires an active package;
[current plans](https://api.pumpview.fun/v1/plans) are authoritative. Unlimited
currently costs 49 USDC for 30 days. Every plan shares **one WSS connection per
account**. Direct USDC invoice payment does not require Coinbase.

`get_recent_trades` returns accepted swap summaries; `get_stream_connection`
describes `wss://api.pumpview.fun/v1/stream`. Your agent runtime maintains the
socket and replay cursor. The feed preserves PumpView's suspicious-price filter
and decoder coverage; it is not every individual Solana swap or archival history.

`get_trading_usage` / `/v1/swaps/usage` returns account and per-key executed
volume. Confirmed swaps count once; finalization and repeated polls do not add
volume. USD totals use build-time price estimates; unpriced swaps remain visible.

## Development

```sh
python -m unittest discover -s tests
```

`server.json` describes the hosted MCP for the official Registry. Publishing the
manifest does not deploy a new server. The hosted service retains its own access
controls and fees. This repository contains client code, examples and agent
instructions under MIT; it does not contain backend credentials or signing keys.
