import requests

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/peer-counsellors/upsert"

updates = [
    {"email": "vijayantrikha1998@gmail.com", "image": "/peers/vijayan.jpg"},
    {"email": "vijayan.peer@example.com", "image": "/peers/vijayan.jpg"},
    {"email": "shrit7@icloud.com", "image": "/peers/shrit.jpg"},
    {"email": "shrit.singh@example.com", "image": "/peers/shrit.jpg"},
    {"email": "nandinipandey083@gmail.com", "image": "/peers/nandini.jpg"},
    {"email": "nandini.pandey@example.com", "image": "/peers/nandini.jpg"},
]

for item in updates:
    payload = {
        "email": item["email"],
        "profile_image_url": item["image"]
    }
    try:
        response = requests.post(ENDPOINT, json=payload)
        if response.status_code == 201:
            print(f"Success: {item['email']}")
        else:
            print(f"Failed: {item['email']} - {response.text}")
    except Exception as e:
        print(f"Error: {item['email']} - {e}")
