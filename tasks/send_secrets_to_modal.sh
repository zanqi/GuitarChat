#!/bin/bash
# shellcheck source=tasks/pretty_log.sh
set -euo pipefail

GANTRY_API_KEY=${GANTRY_API_KEY:-""}

# clear command-line parameters
set --
source tasks/pretty_log.sh

modal secret create mongodb-guitar MONGODB_USER="$MONGODB_USER" MONGODB_HOST="$MONGODB_HOST" MONGODB_PASSWORD="$MONGODB_PASSWORD"
modal secret create openai-api-key-guitar OPENAI_API_KEY="$OPENAI_API_KEY"

if [ "$GANTRY_API_KEY" = "" ]; then
  pretty_log "GANTRY_API_KEY not set. Logging will not be available."
fi

modal secret create gantry-api-key-guitar GANTRY_API_KEY="$GANTRY_API_KEY"
