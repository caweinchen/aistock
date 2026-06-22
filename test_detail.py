import requests

# 测试获取股票详情
url = "http://localhost:8000/api/stocks/000001"
response = requests.get(url)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:1000] if response.text else 'Empty'}")
