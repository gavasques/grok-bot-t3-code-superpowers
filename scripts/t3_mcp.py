#!/usr/bin/env python3
"""Minimal client for T3 Code's MCP server (streamable HTTP, OAuth bearer token).

Config via environment variables:
  T3_MCP_URL         e.g. http://<host>:3773/mcp  (required)
  T3_MCP_TOKEN_FILE  JSON file with {"access_token": "..."}  (default ./t3-token.json)
  T3_SOCKS5          optional SOCKS5 proxy, e.g. localhost:1055 (Tailscale userspace mode)

Usage as a library:
  from t3_mcp import session, call, tools
  sid = session()
  print(call(sid, "t3_project_list", {}))
CLI:
  python3 t3_mcp.py tools
  python3 t3_mcp.py call <tool> '<json arguments>'
"""
import json, os, re, subprocess, sys

URL = os.environ.get("T3_MCP_URL", "")
TOKEN_FILE = os.environ.get("T3_MCP_TOKEN_FILE", "t3-token.json")
SOCKS = os.environ.get("T3_SOCKS5", "")
PROTO = "2025-06-18"


def _token():
    with open(TOKEN_FILE) as f:
        return json.load(f)["access_token"]


def raw(body, sid=None, timeout=120):
    if not URL:
        sys.exit("Set T3_MCP_URL (for example http://host:3773/mcp)")
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", "POST", URL, "-D", "-",
           "-H", "Authorization: Bearer " + _token(),
           "-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream"]
    if SOCKS:
        cmd += ["--socks5-hostname", SOCKS]
    if sid:
        cmd += ["-H", "MCP-Session-Id: " + sid, "-H", "MCP-Protocol-Version: " + PROTO]
    cmd += ["-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    m = re.search(r"(?i)mcp-session-id:\s*(\S+)", out)
    payload = re.split(r"\r?\n\r?\n", out, maxsplit=1)[-1]
    return (m.group(1) if m else sid), payload


def _parse(payload):
    payload = payload.strip()
    try:
        return json.loads(payload)
    except ValueError:
        # server-sent events: take the last "data:" line
        data = [l[5:].strip() for l in payload.splitlines() if l.startswith("data:")]
        return json.loads(data[-1]) if data else payload


def session():
    sid, _ = raw({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": PROTO, "capabilities": {},
                             "clientInfo": {"name": "t3-mcp-client", "version": "1"}}})
    raw({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    return sid


def call(sid, name, args=None, req_id=10):
    _, body = raw({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                   "params": {"name": name, "arguments": args or {}}}, sid)
    return _parse(body)


def tools(sid):
    _, body = raw({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sid)
    return _parse(body)["result"]["tools"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    s = session()
    if sys.argv[1] == "tools":
        for t in tools(s):
            print(t["name"], "-", (t.get("description") or "").split("\n")[0][:100])
    elif sys.argv[1] == "call" and len(sys.argv) >= 3:
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(json.dumps(call(s, sys.argv[2], args), indent=2))
    else:
        sys.exit(__doc__)
