#!/bin/bash
# Submit all SEO pages to Bing/Yandex via IndexNow API
# Run AFTER deploying the key file to bitcoinsapi.com

KEY="a3c0b8ac6666eb4e1683b0a3c6cd017e"
HOST="bitcoinsapi.com"

# First verify the key file is accessible
echo "Verifying key file..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${HOST}/${KEY}.txt")
if [ "$STATUS" != "200" ]; then
    echo "ERROR: Key file not accessible at https://${HOST}/${KEY}.txt (HTTP $STATUS)"
    echo "Deploy the updated static files first."
    exit 1
fi

echo "Key file verified. Submitting URLs..."

curl -s -X POST "https://api.indexnow.org/indexnow" \
  -H "Content-Type: application/json" \
  -d "{
    \"host\": \"${HOST}\",
    \"key\": \"${KEY}\",
    \"keyLocation\": \"https://${HOST}/${KEY}.txt\",
    \"urlList\": [
      \"https://${HOST}/\",
      \"https://${HOST}/vs-mempool\",
      \"https://${HOST}/vs-blockcypher\",
      \"https://${HOST}/best-bitcoin-api-for-developers\",
      \"https://${HOST}/bitcoin-api-for-ai-agents\",
      \"https://${HOST}/self-hosted-bitcoin-api\",
      \"https://${HOST}/bitcoin-fee-api\",
      \"https://${HOST}/bitcoin-mempool-api\",
      \"https://${HOST}/robots.txt\",
      \"https://${HOST}/sitemap.xml\"
    ]
  }" -w "\nHTTP Status: %{http_code}\n"

echo "Done. Bing/Yandex will crawl these URLs within 24-48 hours."
