import requests
import re

API_URL = "https://studconnect-backend.onrender.com/peer-counsellors/upsert"

# Data derived from duplicates.txt and update_peer_counsellors.py
# Format: (Real Email, Duplicate Email, Name, Image URL)
# I will parse duplicates.txt to build this dynamically or hardcode the known pairs if the file is complete.
# The file seems complete for the broken ones.

mappings = [
    {
        "name": "Sofia Nathan",
        "email": "sofia.nathan@example.com", 
        "image_url": "https://drive.google.com/thumbnail?id=1Y6F517o9OgRR1lyL-DF-4D7-r1BQNLOr&sz=w1000"
    },
    {
        "name": "Suhani Mehta",
        "email": "suhani.sharma@example.com",
        "image_url": "" # Original was empty/http site, we keep it empty or try to find one? 
        # Update: Suhani had a `suhanimehta.com` link which was removed. So duplicate should also be empty.
    },
    {
        "name": "Adarsh Rana",
        "email": "adarsh.kumar@example.com",
        "image_url": "https://drive.google.com/thumbnail?id=1LixSgWgbe3bIvIyCNcdHud4c6Lo_rMC1&sz=w1000"
    },
    {
        "name": "Shrit Singh",
        "email": "shrit.singh@example.com",
        "image_url": "" # Original empty
    },
    {
        "name": "Tushar Sharma",
        "email": "tushar.sharma@example.com",
        "image_url": "" # Original empty
    },
    {
        "name": "Navjot Singh",
        "email": "navjot.singh@example.com",
        "image_url": "https://drive.google.com/thumbnail?id=11pYGPP17hW2R_eLg1sWAXWRTcKFQNLB1&sz=w1000"
    },
    {
        "name": "Deeya Rao",
        "email": "deeya.rao@example.com",
        "image_url": "" # Original empty
    },
    {
        "name": "Vijayan",
        "email": "vijayan.peer@example.com",
        "image_url": "" # Original empty
    },
    {
        "name": "Zubia Maryam",
        "email": "zubia.maryam@example.com",
        "image_url": "https://drive.google.com/thumbnail?id=16tGOSZpMhImrHYYPkDU4YqlA6HeXwf4Z&sz=w1000"
    },
    {
        "name": "Nandini Pandey",
        "email": "nandini.pandey@example.com",
        "image_url": "https://drive.google.com/thumbnail?id=1WoiULVOpM7OyAYQiKt8JUatCyVxWRRqm&sz=w1000"
    },
    # Add others if missed, but these cover the duplicates.txt list
]

def sync_duplicates():
    print(f"Syncing {len(mappings)} duplicate records...")
    success_count = 0
    
    for m in mappings:
        payload = {
            "name": m["name"],
            "email": m["email"],
            "profile_image_url": m["image_url"]
        }
        
        try:
            resp = requests.post(API_URL, json=payload)
            if resp.status_code in [200, 201]:
                print(f"Updated duplicate: {m['name']} ({m['email']})")
                success_count += 1
            else:
                print(f"Failed to update {m['name']}: {resp.text}")
        except Exception as e:
            print(f"Error updating {m['name']}: {e}")
            
    print(f"Sync complete. Updated {success_count} records.")

if __name__ == "__main__":
    sync_duplicates()
