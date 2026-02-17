#!/usr/bin/env bash
set -euo pipefail

# Appel local du backend (évite réseau)
URL="http://127.0.0.1:8000/prices/update-daily"

# Timeout pour éviter un job bloqué
curl -fsS --max-time 120 -X POST "$URL"
echo
