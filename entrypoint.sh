#!/bin/sh
set -e
# Install Chromium into the persistent volume on first start; skip if already present.
playwright install chromium
exec "$@"
