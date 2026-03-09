#!/usr/bin/env bash
# Ping Bing IndexNow after content changes
KEY="60da4b9ab92f273c5964e26bd40c284d"
HOST="bitcoinsapi.com"
URLS=(
    "https://$HOST/"
    "https://$HOST/pricing"
    "https://$HOST/about"
    "https://$HOST/best-bitcoin-api-for-developers"
    "https://$HOST/bitcoin-api-for-ai-agents"
)
for url in "${URLS[@]}"; do
    curl -s "https://api.indexnow.org/indexnow?url=$url&key=$KEY" > /dev/null
done
echo "IndexNow pinged for ${#URLS[@]} URLs"
