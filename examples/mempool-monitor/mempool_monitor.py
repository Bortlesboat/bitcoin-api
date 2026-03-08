"""Bitcoin Mempool Monitor — Track mempool congestion.

Powered by bitcoinsapi.com — Free Bitcoin API for developers.
"""
import requests
import time
import json

API_URL = "https://bitcoinsapi.com/api/v1/mempool"

def main():
    print("Monitoring Bitcoin mempool...")
    print("Powered by bitcoinsapi.com\n")

    while True:
        try:
            resp = requests.get(API_URL)
            data = resp.json().get('data', resp.json())
            size = data.get('bytes', data.get('size', 0))
            size_mb = size / 1_000_000 if size else 0
            tx_count = data.get('size', data.get('tx_count', data.get('count', '?')))
            print(f"Mempool | Size: {size_mb:.1f} MB | Transactions: {tx_count}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(30)

if __name__ == "__main__":
    main()
