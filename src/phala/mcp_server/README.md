# Phala MCP Server

A reference [Model Context Protocol](https://modelcontextprotocol.io/)
server that exposes Phala's five primitive validators and the
BU-Privacy invariant check as MCP tools. Uses stdio transport. Works
with any MCP-compatible client; see the VSCode section below for one
concrete configuration.

## Install

From the repository root:

```bash
pip install -e '.[mcp]'
```

This installs the MCP Python SDK alongside the Phala package and
registers the `phala-mcp` console script.

## Run

```bash
phala-mcp
```

Or without the script wrapper:

```bash
python -m phala.mcp_server
```

The server writes MCP protocol messages on stdout and reads requests
on stdin. It is not interactive from a shell; an MCP client starts it
as a subprocess.

## Tools exposed

| Tool | Purpose |
|---|---|
| `validate_outcome_event` | Structural validation of an OutcomeEvent (§3.1). |
| `validate_satisfaction_record` | Structural validation of a SatisfactionRecord (§3.2). |
| `validate_belief_update` | Structural validation of a BeliefUpdate (§3.3). |
| `validate_principal_satisfaction_model` | Structural validation of a PSM (§3.4). |
| `validate_welfare_trace` | Structural validation of a WelfareTrace (§3.5). |
| `validate_belief_privacy` | BU-Privacy invariant (§3.3, BU-1) check on a serialized payload. |

All tools take and return JSON. See `src/phala/mcp_server/tools.py`
for input schemas and output shapes.

## Wire into VSCode

Add this to `.vscode/mcp.json` at your workspace root (or configure
globally via your VSCode user settings, under the MCP section):

```json
{
  "servers": {
    "phala": {
      "type": "stdio",
      "command": "/absolute/path/to/your/.venv/bin/phala-mcp"
    }
  }
}
```

Reload the workspace. The tools appear in any MCP-aware VSCode
extension under the `phala` server name.

## Sample payloads

See [`EXAMPLES.md`](./EXAMPLES.md) for ready-to-paste JSON per tool,
covering the happy path and the failure variant for each one.

## Doctor check

Run a structural self-check (tool registry intact, schemas
well-formed) without spawning the stdio loop:

```bash
phala-mcp --doctor
```

Exit code is 0 when all tools register correctly, 1 otherwise.

## Testing

```bash
pytest tests/mcp_server/
```

Handler-level tests hit `tools.py` directly; one stdio smoke test
launches the server as a subprocess and completes the MCP handshake,
confirming the end-to-end transport.
