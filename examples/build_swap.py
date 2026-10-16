"""Build/simulate an unsigned swap; never signs or submits a transaction."""
import argparse
import json
import os
import uuid
from pathlib import Path
from pumpview_agent_kit import PumpView


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wallet", required=True, help="Public wallet linked to the API key")
    parser.add_argument("--input", default="SOL")
    parser.add_argument("--output", required=True, help="Token mint, SOL, WSOL or USDC")
    parser.add_argument("--amount", required=True, help="Integer atomic units as a string")
    parser.add_argument("--slippage-bps", type=int, required=True)
    parser.add_argument("--tip-lamports", type=int, default=2000000)
    parser.add_argument("--state", type=Path, required=True, help="New intent file, e.g. state/buy-001.json; reuse to recover")
    args = parser.parse_args()
    intent = dict(wallet=args.wallet, input_mint=args.input, output_mint=args.output, amount=args.amount,
                  slippage_bps=args.slippage_bps, tip_lamports=args.tip_lamports, max_priority_fee_lamports=1000000)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.state.open("x", encoding="utf-8") as output:
            intent["request_id"] = uuid.uuid4().hex
            json.dump(intent, output, indent=2)
    except FileExistsError:
        saved = json.loads(args.state.read_text(encoding="utf-8"))
        if {k: v for k, v in saved.items() if k != "request_id"} != {k: v for k, v in intent.items() if k != "request_id"}:
            raise SystemExit("Existing state belongs to a different intent. Do not overwrite it.")
        intent = saved
    result = PumpView(os.environ["PUMPVIEW_API_KEY"]).build_swap(intent)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
