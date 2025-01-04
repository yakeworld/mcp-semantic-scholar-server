---
noteId: "96e17bb0cad111ef947d13551760d7dd"
tags: []

---

# Semantic Scholar API MCP server

Made with [FastMCP](https://github.com/jlowin/fastmcp)

Requirements: `pip install fastmcp aiohttp pydantic uvicorn`

Run `fastmcp dev run path/to/semantic-scholar-plugin.py` to initialize the server.

RUn `fastmcp install path/to/semantic-scholar-plugin.py` to install to claude or add following to claude/cline config:

```json
"semantic-scholar": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "fastmcp",
        "run",
        "\path\to\semantic-scholar-plugin.py"
      ]
    }
```