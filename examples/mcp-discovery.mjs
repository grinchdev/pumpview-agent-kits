// Public MCP discovery and configuration only. No wallet or API key needed.
const url = "https://api.pumpview.fun/mcp/";
let version = "2025-11-25";
async function rpc(method, params, id) {
  const response = await fetch(url, {method: "POST", redirect: "error", signal: AbortSignal.timeout(15000),
    headers: {"Content-Type": "application/json", Accept: "application/json, text/event-stream", "MCP-Protocol-Version": version},
    body: JSON.stringify({jsonrpc: "2.0", method, params, ...(id === undefined ? {} : {id})})});
  if (!response.ok) throw new Error(`MCP HTTP ${response.status}`);
  if (id === undefined) return;
  const body = await response.json();
  if (body.error) throw new Error(JSON.stringify(body.error));
  return body.result;
}
const init = await rpc("initialize", {protocolVersion: version, capabilities: {},
  clientInfo: {name: "pumpview-agent-kit", version: "1.0.0"}}, 1);
version = init.protocolVersion;
await rpc("notifications/initialized", {});
const list = await rpc("tools/list", {}, 2);
console.log(JSON.stringify({server: init.serverInfo, tools: list.tools.map(t => t.name)}, null, 2));
console.log(JSON.stringify(await rpc("tools/call", {name: "get_trading_config", arguments: {}}, 3), null, 2));
