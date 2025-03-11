# Semantic Scholar API MCP server

Made with [FastMCP](https://github.com/jlowin/fastmcp)

Requirements: `pip install fastmcp aiohttp pydantic uvicorn`

## API Key

To use the Semantic Scholar API with higher rate limits, you can set your API key as an environment variable:

```bash
export SEMANTIC_SCHOLAR_API_KEY="your_api_key"
```

You can get an API key by filling out the form at: https://www.semanticscholar.org/product/api

## Usage

Run `fastmcp dev path/to/semantic-scholar-plugin.py` to initialize the server.

Run `fastmcp install path/to/semantic-scholar-plugin.py` to install to claude or add following to claude/cline config:

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

If you see things like `INFO Processing request of type __init__.py:431 ListToolsRequest` in cline, you can ignore them as this will not affect it from working, this is due to current incomplete impliementation of the function discription and listing support.
