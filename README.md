# Semantic Scholar API MCP server

Made with [mcp-python-sdk](https://github.com/modelcontextprotocol/python-sdk)

> [!IMPORTANT]  
> if you are still using FastMCP version of this mcp server, please consider pull this repo again and update to newer versions as FastMCP is already deprecated.

## Usage

Requirements: `pip install -r requirements.txt`

Run `mcp dev path/to/semantic-scholar-plugin.py` to initialize the server.

Run `mcp install path/to/semantic-scholar-plugin.py` to install to claude or add following to claude/cline config:

```json
"semantic-scholar": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp",
        "mcp",
        "run",
        "/path/to/semantic-scholar-plugin.py"
      ]
    }
```

> [!NOTE]
> Currently using `uv` with `mcp` seems to break certain Linux/macOS version of Claude-desktop, you might need to set as:
> ```json
> "semantic-scholar": {
>       "command": "/path/to/mcp",
>       "args": [
>         "run",
>         "/path/to/semantic-scholar-plugin.py"
>       ]
>     }
> ```
> instead, with `/path/to/mcp` got from running `which mcp` in terminal

## API Key

To use the Semantic Scholar API with higher rate limits, you can set your API key as an environment variable:

```bash
export SEMANTIC_SCHOLAR_API_KEY="your_api_key"
```

or set by adding an `env` key in mcp settings by:

```json
"semantic-scholar": {
      "command": ...,
      "args": ...,
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your_api_key"
      }
}
```

You can get an API key by filling out the form at: https://www.semanticscholar.org/product/api

## Suggested Agent System prompt

See: [benhaotang/my_agent_system_prompt](https://github.com/benhaotang/my_agent_system_prompt/blob/main/msty_ai_preresearch.md), the AI pre-research agent that can make full use of this mcp server.

## Known issues

- If you see things like `INFO Processing request of type __init__.py:431 ListToolsRequest` in cline, you can ignore them as this will not affect it from working, this is because cline parse tool list together with console debug infos, and current python-sdk cannot disable console messages. This will not affect any function calling part other than seeing this warning.
