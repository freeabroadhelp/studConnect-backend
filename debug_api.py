import requests
import json

try:
    print("Fetching peer counsellors...")
    res = requests.get('https://studconnect-backend.onrender.com/peer-counsellors')
    print(f"Status Code: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"Count: {len(data)}")
        if len(data) > 0:
            print("First item sample:")
            print(json.dumps(data[0], indent=2))
            
            # Check for email matches
            valid_emails = [
                "n0aveen0@gmail.com",
                "reetika7700@yahoo.com",
                "nathansofia25@gmail.com",
                "mihirnagpal1@gmail.com",
                "deeyar2005@gmail.com",
                "vijayantrikha1998@gmail.com",
                "zubiamaryam6@gmail.com",
                "adarshrana141@gmail.com",
                "suhanimehta300@gmail.com",
                "shrit7@icloud.com",
                "itsted2407@gmail.com",
                "suryanshsp14@icloud.com",
                "tushar241999@gmail.com",
                "chauhancharchit81@gmail.com",
                "navjotnv15@gmail.com",
                "nandinipandey083@gmail.com"
            ]
            
            matches = 0
            for c in data:
                if c.get('email', '').strip().lower() in valid_emails:
                    matches += 1
                else:
                    print(f"Skipped (not in whitelist): {c.get('email')}")
            
            print(f"Whitelisted Count: {matches}")
        else:
            print("Data is empty array")
    else:
        print("Request failed")
except Exception as e:
    print(f"Error: {e}")
