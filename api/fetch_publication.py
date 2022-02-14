import json
import requests

base_url = "http://localhost:8885"
apikey = "5df4314c3d22467aad2a9ceb0d8b895e"

url = f"{base_url}/api/publication"
headers = {"X-Publications-API-key": apikey}

data = dict(identifier="1557129", labels={"Exposomics": "Service"})

response = requests.post(url, headers=headers, json=data)

if response.status_code != 200:
    raise ValueError(f"Error {response.status_code}: {response.reason}")
else:
    print(json.dumps(response.json(), indent=2))
