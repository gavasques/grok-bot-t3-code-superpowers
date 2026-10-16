#!/usr/bin/env python3
"""Manual OAuth (PKCE) sign-in to T3 Code's MCP server, for agents without a browser callback.

Step 1:  python3 t3_oauth.py start  [--scope read|operate]
         Registers a client, saves state, prints the authorize URL for the human.
Step 2:  The human opens the URL, enters a pairing code, picks the access level, approves.
         The browser then fails to load http://localhost:8976/callback?code=...  They copy that URL.
Step 3:  T3_CALLBACK_URL='<pasted url>' python3 t3_oauth.py finish
         Exchanges the code for a token (30 days) and writes it to the token file (mode 0600).

Environment:
  T3_BASE_URL        server origin, e.g. http://<host>:3773   (required)
  T3_OAUTH_DIR       where to keep state (default ./.t3oauth)
  T3_TOKEN_FILE      output token file (default ./t3-token.json)
  T3_SOCKS5          optional SOCKS5 proxy, e.g. localhost:1055
Never print or log the callback URL or the token: both are passwords.
"""
import base64, hashlib, json, os, secrets, subprocess, sys, urllib.parse

BASE = os.environ.get("T3_BASE_URL", "").rstrip("/")
DIR = os.environ.get("T3_OAUTH_DIR", ".t3oauth")
TOKEN_FILE = os.environ.get("T3_TOKEN_FILE", "t3-token.json")
SOCKS = os.environ.get("T3_SOCKS5", "")
REDIRECT = "http://localhost:8976/callback"
SCOPES = {"read": "orchestration:read", "operate": "orchestration:read orchestration:operate"}


def curl(args):
    cmd = ["curl", "-sS", "-m", "60"] + (["--socks5-hostname", SOCKS] if SOCKS else []) + args
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def start(scope):
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    reg = json.loads(curl(["-X", "POST", BASE + "/oauth/mcp/register", "-H", "Content-Type: application/json", "-d",
                           json.dumps({"client_name": "agent", "redirect_uris": [REDIRECT],
                                       "grant_types": ["authorization_code"], "response_types": ["code"],
                                       "token_endpoint_auth_method": "none"})]))
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    for name, val in (("reg.json", json.dumps(reg)), ("verifier", verifier), ("state", state)):
        p = os.path.join(DIR, name)
        with open(p, "w") as f:
            f.write(val)
        os.chmod(p, 0o600)
    q = urllib.parse.urlencode({"response_type": "code", "client_id": reg["client_id"], "redirect_uri": REDIRECT,
                                "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
                                "scope": SCOPES[scope], "resource": BASE + "/mcp"})
    print(BASE + "/oauth/mcp/authorize?" + q)


def finish():
    cb = os.environ.get("T3_CALLBACK_URL")
    if not cb:
        sys.exit("Set T3_CALLBACK_URL to the full callback URL the browser ended on")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(cb).query)
    rd = lambda n: open(os.path.join(DIR, n)).read().strip()
    if qs.get("state", [""])[0] != rd("state"):
        sys.exit("State mismatch: start over")
    reg = json.loads(rd("reg.json"))
    out = curl(["-X", "POST", BASE + "/oauth/mcp/token", "-d", "grant_type=authorization_code",
                "-d", "code=" + qs["code"][0], "-d", "redirect_uri=" + REDIRECT,
                "-d", "client_id=" + reg["client_id"], "-d", "code_verifier=" + rd("verifier"),
                "-d", "resource=" + BASE + "/mcp"])
    tok = json.loads(out)
    if "access_token" not in tok:
        sys.exit("Token exchange failed: " + str({k: v for k, v in tok.items() if k != "access_token"}))
    with open(TOKEN_FILE, "w") as f:
        json.dump(tok, f)
    os.chmod(TOKEN_FILE, 0o600)
    print("Token saved to", TOKEN_FILE, "- scopes:", tok.get("scope"))


if __name__ == "__main__":
    if not BASE:
        sys.exit("Set T3_BASE_URL (for example http://host:3773)")
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        sc = sys.argv[sys.argv.index("--scope") + 1] if "--scope" in sys.argv else "read"
        start(sc)
    elif len(sys.argv) > 1 and sys.argv[1] == "finish":
        finish()
    else:
        sys.exit(__doc__)
