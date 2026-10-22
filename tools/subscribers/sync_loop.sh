#!/usr/bin/env bash
# Sincroniza a cada 5 min. Uso: nohup tools/subscribers/sync_loop.sh >> /workspace/data/sync.log 2>&1 &
cd "$(dirname "$0")/../.." || exit 1
while true; do echo "$(date -Iseconds) $(python3 tools/subscribers/sync_sqlite.py 2>&1 | tail -1)"; sleep 300; done
