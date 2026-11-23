#!/bin/sh
# First start: fill the empty library with the starter knowledge, once. After that the library is yours.
set -e
if [ ! -f /data/library.db ] && [ -d /app/seed ]; then
  echo "First start: adding the starter knowledge..."
  python kb.py import-library /app/seed --name "Starter knowledge" --namespace KB || echo "(the starter knowledge couldn't be added; the library still works)"
fi
exec python kb.py serve --host 0.0.0.0 --port 8090
