#!/usr/bin/env python
"""
Debug Serper API response format
"""

import requests
from aura_research.utils.config import SERPER_API_KEY
import json

url = "https://google.serper.dev/scholar"

payload = {
    "q": "Backpropagation",
    "num": 5
}

headers = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json"
}

print("Fetching from Serper API...")
response = requests.post(url, json=payload, headers=headers, timeout=30)

print(f"Status Code: {response.status_code}")
print(f"\nResponse JSON:")
data = response.json()

print(json.dumps(data, indent=2))

print(f"\nOrganic results count: {len(data.get('organic', []))}")

if data.get('organic'):
    print(f"\nFirst organic result:")
    first = data.get('organic')[0]
    print(json.dumps(first, indent=2))

    print(f"\nFirst result type: {type(first)}")
    print(f"First result keys: {first.keys() if isinstance(first, dict) else 'NOT A DICT'}")
