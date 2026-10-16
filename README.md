# Grok Bot x T3 Code

A skill that lets an AI agent, such as a Grok Bot, drive [T3 Code](https://github.com/pingdotgg/t3code) on a remote machine (for example a VPS) through T3's built-in MCP server.

From chat, the agent can start Claude, Codex, Grok and other coding-agent threads in your projects, follow them, answer approval requests, create projects and worktrees, schedule tasks and watch pull requests, without using each provider's CLI directly.

Not affiliated with T3 Tools, Ping Labs or xAI. T3 Code is a separate project and its Nightly builds change often: check `tools/list` if a tool is missing.

## What is inside

- `SKILL.md`: the full playbook (connection over Tailscale or T3 Connect, OAuth sign-in, the tool catalog, orchestration patterns, troubleshooting, safety rules).
- `docs/SETUP.md`: a step-by-step guide that says what you do and what your Grok Bot does to get connected.
- `scripts/t3_oauth.py`: manual OAuth + PKCE sign-in for agents that have no browser to receive the callback.
- `scripts/t3_mcp.py`: a small MCP client (stdlib Python plus `curl`) to list and call T3's tools.

## Quick start

1. Make the T3 server reachable from the agent's machine (see section 0 of `SKILL.md`).
2. Sign in, read-only first:
   ```bash
   export T3_BASE_URL=http://<host>:3773
   python3 scripts/t3_oauth.py start --scope read     # prints a URL for you to open and approve
   T3_CALLBACK_URL='<the localhost:8976 URL your browser ended on>' python3 scripts/t3_oauth.py finish
   ```
3. Use it:
   ```bash
   export T3_MCP_URL=$T3_BASE_URL/mcp
   python3 scripts/t3_mcp.py tools
   python3 scripts/t3_mcp.py call t3_project_list '{}'
   ```

Set `T3_SOCKS5=localhost:1055` if the agent reaches your network through Tailscale in userspace mode.

## Safety

The sign-in token and callback URL are passwords: keep them out of logs, chat and screenshots. Start with read-only access and new threads in plan mode with approvals required, and escalate only when you decide to. Tokens last 30 days and can be revoked in T3's Settings > Connections.

## License

MIT
