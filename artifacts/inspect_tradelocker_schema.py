import json
import urllib.request

request = urllib.request.Request('https://public-api.tradelocker.com/reference/getconfigusingget.md', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(request, timeout=20) as response:
    text = response.read().decode()
schema = json.loads(text.split('```json\n', 1)[1].split('```', 1)[0])
data = schema['components']['schemas']['ConfigResponse']['example']['d']
print(json.dumps({k: data[k] for k in ('rateLimits', 'ordersConfig', 'positionsConfig')}, indent=2))