// Node 22.18+ can run this TypeScript file directly. It never signs or submits.
// Provide a PERSISTED, unique PUMPVIEW_REQUEST_ID for this intent before running.
const required = (name: string): string => {
  const value = process.env[name];
  if (!value) throw new Error(`Missing ${name}`);
  return value;
};
const amount = required("PUMPVIEW_AMOUNT");
if (!/^[1-9][0-9]*$/.test(amount)) throw new Error("Use an integer string in atomic units");
const response = await fetch("https://api.pumpview.fun/v1/swaps/build", {
  method: "POST", redirect: "error", signal: AbortSignal.timeout(65000),
  headers: {"Content-Type": "application/json", Authorization: `Bearer ${required("PUMPVIEW_API_KEY")}`},
  body: JSON.stringify({
    request_id: required("PUMPVIEW_REQUEST_ID"), wallet: required("PUMPVIEW_WALLET"),
    input_mint: process.env.PUMPVIEW_INPUT || "SOL", output_mint: required("PUMPVIEW_OUTPUT"),
    amount, slippage_bps: Number(required("PUMPVIEW_SLIPPAGE_BPS")),
    tip_lamports: 2000000, max_priority_fee_lamports: 1000000,
  }),
});
if (!response.ok) throw new Error(`PumpView HTTP ${response.status}; keep the same request ID`);
console.log(JSON.stringify(await response.json(), null, 2));
