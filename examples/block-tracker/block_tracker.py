"""Bitcoin Block Tracker — Get alerted when new blocks are mined.

Powered by bitcoinsapi.com — Free Bitcoin API for developers.
"""
import requests

API_URL = "https://bitcoinsapi.com/api/v1/stream/blocks"

def main():
    print("Watching for new Bitcoin blocks...")
    print("Powered by bitcoinsapi.com\n")

    with requests.get(API_URL, stream=True) as response:
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    import json
                    data = json.loads(line[5:].strip())
                    block = data.get('data', data)
                    height = block.get('height', 'unknown')
                    hash_val = block.get('hash', 'unknown')[:16] + '...'
                    txs = block.get('tx_count', block.get('nTx', '?'))
                    print(f"New Block #{height} | Hash: {hash_val} | Txs: {txs}")

if __name__ == "__main__":
    main()
