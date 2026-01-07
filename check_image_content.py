import requests

url = "https://lh3.googleusercontent.com/d/16LUdOulQMx8Q6RX_ESb7QiTm5Eh5HlUc"
try:
    response = requests.get(url, allow_redirects=True, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    content_preview = response.content[:20]
    print(f"Content Start: {content_preview}")
    
    if b'html' in content_preview.lower() or b'<!doctype' in content_preview.lower():
        print("DETECTED HTML (Likely Login Page)")
    else:
        print("DETECTED BINARY (Likely Image)")

except Exception as e:
    print(f"Error: {e}")
