"""Bitcoin Fee Monitor — Track fee estimates in real time.

Powered by bitcoinsapi.com — Free Bitcoin API for developers.
"""
import requests
import json

API_URL = "https://bitcoinsapi.com/api/v1/stream/fees"

def main():
    print("Monitoring Bitcoin fee estimates...")
    print("Powered by bitcoinsapi.com\n")

    with requests.get(API_URL, stream=True) as response:
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    data = json.loads(line[5:].strip())
                    fees = data.get('data', data)
                    fast = fees.get('fastest', fees.get('high_priority', '?'))
                    medium = fees.get('half_hour', fees.get('medium_priority', '?'))
                    slow = fees.get('economy', fees.get('low_priority', '?'))
                    print(f"Fees (sat/vB) | Fast: {fast} | Medium: {medium} | Economy: {slow}")

if __name__ == "__main__":
    main()
