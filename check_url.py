import requests

url = "https://drive.google.com/uc?export=view&id=1jGThh1gYm1rCL8ACICjZO2OjV4w5tnR6"
try:
    response = requests.head(url, allow_redirects=True)
    print(f"Final URL: {response.url}")
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error: {e}")
