# Kingdom Library

A knowledge base you run on your own computer: full-text search, a web UI, a REST API and an MCP server so AI agents
can look things up and contribute. It's a bolt-on for [Kingdom One](https://github.com/Nestcore-Dan/kingdom-starter),
and works on its own too.

It starts with **starter knowledge**: 338 entries about AI agents, tools, models and techniques, gathered from public
videos and datasets, each citing its source. It's machine-written and unreviewed; check anything important.

## Install (Docker)
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. In this folder: `docker compose up -d`
3. Open http://localhost:8090. The first start adds the starter knowledge (a minute or so).
4. In Kingdom One: Settings → Connections → Kingdom Library → Connect.

Optional: install [Ollama](https://ollama.com) and `ollama pull qwen3:4b` so new material is tidied and the desk can
answer questions. Set `KB_OWNER=Your name` before `docker compose up -d` to put your name on the library.

## Add knowledge
- **YouTube videos and playlists:** install the [Kingdom YouTube downloader](https://github.com/Nestcore-Dan/kingdom-youtube),
  paste a link with Transcribe and Analyze ticked (Analyze needs Ollama with a vision model). What each video teaches
  is filed here.
- **Documents, notes and other knowledge bases:** put a folder or .zip in this folder's `import` folder (Markdown, text,
  HTML, CSV, JSON, YAML or PDF; Obsidian vaults and Open Knowledge Format bundles work too). Then in the library open
  Libraries → Import a library and give the path `/import/<its name>`. It arrives unreviewed, in its own namespace.
- **One item from a script:** `POST /api/v1/ingest` (see http://localhost:8090/docs).
- **Agents:** the MCP server (`docker exec -i kb python mcp_server.py`) lets agents search, read and submit material.

## Rules
`RULES.md` holds the house rules for what goes in and how it's rated. Edit them to suit you.

## Licence
MIT, see `LICENSE`. Includes three.js (MIT) and the OKF validator (Apache-2.0), each with its licence.
