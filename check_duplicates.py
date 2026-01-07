import requests
import json
from collections import defaultdict

API_URL = "https://studconnect-backend.onrender.com/peer-counsellors"

try:
    response = requests.get(API_URL)
    data = response.json()
    
    by_name = defaultdict(list)
    for p in data:
        name = p.get('name', '').strip()
        by_name[name].append(p)
        
    with open("duplicates.txt", "w", encoding="utf-8") as f:
        f.write(f"Total records found: {len(data)}\n")
        found_any = False
        for name, items in by_name.items():
            if len(items) > 1:
                found_any = True
                f.write(f"\nGROUP: {name}\n")
                # Sort by ID to see which is first
                items.sort(key=lambda x: x['id'])
                for item in items:
                    email = item.get('email', '')
                    img = item.get('profile_image_url', '')
                    f.write(f"  ID: {item['id']}\n")
                    f.write(f"  Email repr: {repr(email)}\n")
                    f.write(f"  Image: {img}\n")
                    f.write("-" * 20 + "\n")
        
        if not found_any:
            f.write("No duplicates found.\n")

    print("Done writing to duplicates.txt")

except Exception as e:
    print(f"Error: {e}")
