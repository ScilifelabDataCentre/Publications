import json
import requests

base_url = "http://localhost:8885"
apikey = "5df4314c3d22467aad2a9ceb0d8b895e"

url = f"{base_url}/api/publication/dbef55e90af84b78b864bde76fe6dbe1/labels"
headers = {'X-API-key': apikey}

data = dict(labels={"Exposomics": "Technology Development"})

response = requests.post(url, headers=headers, json=data)

if response.status_code != 200:
    raise ValueError(f"Error {response.status_code}: {response.reason}")
else:
    print(json.dumps(response.json(), indent=2))
