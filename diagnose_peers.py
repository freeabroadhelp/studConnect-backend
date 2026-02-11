from sqlalchemy.orm import Session
from db import get_db, engine
from models.models import PeerCounsellor

def diagnose_duplicates():
    # Create a session
    db = next(get_db())
    try:
        peers = db.query(PeerCounsellor).all()
        print(f"Total Peer Counsellors: {len(peers)}")
        
        email_map = {}
        for p in peers:
            # Normalize email
            email = p.email.strip().lower()
            if email not in email_map:
                email_map[email] = []
            email_map[email].append(p)
            
        duplicates = {e: ps for e, ps in email_map.items() if len(ps) > 1}
        
        print("\n--- DUPLICATES FOUND ---")
        if not duplicates:
            print("No duplicates based on normalized email.")
        
        for email, ps in duplicates.items():
            print(f"Email: {email} (Count: {len(ps)})")
            for p in ps:
                print(f"  - ID: {p.id}, Name: {p.name}, Image: {p.profile_image_url}")
        
        print("\n--- ALL EMAILS ---")
        item_count = 0
        for email, ps in email_map.items():
            print(f"- {email} ({len(ps)}) [Image: {ps[0].profile_image_url}]")
            item_count += len(ps)

        print(f"\nTotal Unique Emails: {len(email_map)}")
        print(f"Total Records: {item_count}")

    finally:
        db.close()

if __name__ == "__main__":
    diagnose_duplicates()
