# Setup guide: connect a Grok Bot to T3 Code

This guide says who does what. Steps marked **You** are done by you, on the machine that runs T3 Code or in your browser. Steps marked **Grok Bot** are things you ask your bot to do, or that it does on its own computer. Nothing here needs your bot to see your passwords: it only ever holds an access token that you can revoke.

## What you need

- T3 Code ([pingdotgg/t3code](https://github.com/pingdotgg/t3code)) installed and running on a machine you control (your laptop, a VPS, a home server). A recent Nightly build is recommended, since the MCP server is newer.
- A Grok Bot with a computer of its own (it needs to run Python 3 and `curl`).
- A way for the two to talk. Pick one path:
  - **Path A: Tailscale** (private, what this guide describes in detail). Your bot joins your tailnet.
  - **Path B: T3 Connect** (public HTTPS address). Use this if you do not want to install anything on the bot's computer. In T3, open Settings > Connections and copy the MCP URL, then use that URL as the base address below.

## Path A, step by step

### 1. You: make T3 reachable from your tailnet

By default T3 only listens on `127.0.0.1`. Make it listen on a non-loopback address.

- On a headless Linux host, keep T3 running as a service: `t3 service install` (on Linux also run `sudo loginctl enable-linger "$(id -un)"`).
- Then set the host. One way is a systemd user drop-in at `~/.config/systemd/user/t3code.service.d/host.conf`:
  ```ini
  [Service]
  Environment=T3CODE_HOST=0.0.0.0
  ```
  followed by `systemctl --user daemon-reload` and `t3 service restart`. Only do this behind a firewall or on a tailnet-only machine, because `0.0.0.0` means every network interface.
- Check it with `t3 service status`. The default port is `3773`.

### 2. You: give your bot a Tailscale auth key

In the Tailscale admin console, create an auth key (a reusable key is not needed; a single-use, short-lived one is safer). Send it to your bot through a secret field, not in plain chat.

### 3. Grok Bot: join your tailnet

Ask your bot: "Install Tailscale on your computer and join my tailnet with the key I gave you, in userspace mode." Under the hood it runs:

```bash
tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &
tailscale up --authkey "$TS_AUTHKEY" --hostname=grok-bot
```

In userspace mode the bot reaches your machines through a local SOCKS5 proxy, so every request uses `curl --socks5-hostname localhost:1055`. The included scripts do this when you set `T3_SOCKS5=localhost:1055`.

Then ask it to test the T3 port itself, not just a ping:

```bash
curl --socks5-hostname localhost:1055 -I http://<your-tailnet-ip-or-name>:3773/
```

The first attempt after joining can fail; retry a few times.

### 4. Grok Bot: install the skill and scripts

Ask your bot to save `SKILL.md` as a skill and to keep `scripts/` on its computer. Then set:

```bash
export T3_BASE_URL=http://<your-tailnet-ip-or-name>:3773
export T3_MCP_URL=$T3_BASE_URL/mcp
export T3_SOCKS5=localhost:1055
```

### 5. Grok Bot and You: sign in with OAuth (read-only first)

T3's MCP accepts only OAuth tokens. Your bot has no browser to catch the callback, so the sign-in is manual:

1. **Grok Bot** runs `python3 scripts/t3_oauth.py start --scope read` and gives you a link.
2. **You** open the link in a browser that can reach T3 (on your tailnet). Create a fresh pairing code on the T3 host with `t3 auth pairing create --scope orchestration:read --ttl 30m` (or in Settings > Connections), paste it on the page, and approve with **Read only**.
3. The browser then ends on a page that fails to load, with an address starting with `http://localhost:8976/callback?code=...`. Copy that whole address and send it to your bot through a secret field. It is a password.
4. **Grok Bot** runs `T3_CALLBACK_URL='<that address>' python3 scripts/t3_oauth.py finish`. The token is stored in a private file and lasts 30 days.

Do not ask a model to create pairing codes for you. You make them on the host yourself.

### 6. Grok Bot: check that it works

```bash
python3 scripts/t3_mcp.py tools
python3 scripts/t3_mcp.py call t3_project_list '{}'
```

You should see the tool list and your projects.

### 7. Optional: give it more power

Repeat step 5 with `--scope operate` (and choose a higher access level on the approval page) only when you want the bot to start and message threads. A launched thread can never exceed the permission mode you approved. Ask the bot to start new threads with approvals required and in plan mode until you trust the flow.

## Staying safe

- Start read-only, escalate only when you decide to.
- Treat the token, pairing codes and the callback address as passwords.
- You can revoke the bot at any time in T3's Settings > Connections.
- Keep T3 private: do not expose port 3773 to the open internet.

## Troubleshooting

- **Cannot reach the port**: a Tailscale ping working does not prove the T3 port is open. Check `t3 service status`, the firewall, and that T3 listens on `0.0.0.0`.
- **401 or invalid token**: the token expired (30 days) or was revoked. Repeat step 5.
- **400 from the MCP**: the client must send `MCP-Protocol-Version: 2025-06-18` after `initialize`. The included script does.
- **A thread seems stuck**: it may be waiting for an approval inside T3. Approve it there or interrupt it.

More host-side commands (`t3 update`, `t3 doctor`, `t3 connect`) are in section 5 of `SKILL.md`.
