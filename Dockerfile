# The Kingdom Library: a knowledge base with full-text search, a web UI on port 8090, a REST API and an MCP server.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" markdown "mcp>=2,<3" pyyaml pypdf icalendar recurring-ical-events
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 KB_DB=/data/library.db KB_OKF_DIR=/data/okf
WORKDIR /app
COPY . /app
EXPOSE 8090
ENTRYPOINT ["tini", "--", "sh", "/app/start.sh"]
