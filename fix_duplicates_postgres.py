import psycopg2
import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

def fix_duplicates():
    if not DB_URL:
        print("DATABASE_URL not found in .env!")
        return

    print("Connecting to database...")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Fetch all peer counsellors
        cursor.execute("SELECT id, name, email, profile_image_url FROM peer_counsellors ORDER BY id ASC")
        rows = cursor.fetchall()
        
        # Convert to list of dicts for easier handling
        peers = []
        for r in rows:
            peers.append({
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "profile_image_url": r[3]
            })

        print(f"Fetched {len(peers)} records.")
        
        # Group by normalized NAME
        by_name = {}
        for p in peers:
            name_key = p['name'].strip().lower()
            if name_key not in by_name:
                by_name[name_key] = []
            by_name[name_key].append(p)

        duplicates_removed = 0
        
        for name, records in by_name.items():
            if len(records) > 1:
                print(f"Processing duplicates for: {records[0]['name']}")
                
                # First record is original (lowest ID)
                original = records[0]
                duplicates = records[1:]
                
                # Find best image URL
                best_image_url = original['profile_image_url']
                for r in records:
                    url = r['profile_image_url']
                    if url and "thumbnail" in url:
                        best_image_url = url
                        break
                
                # Update original if needed
                if original['profile_image_url'] != best_image_url:
                    print(f"  Updating original ID {original['id']} with new image URL...")
                    cursor.execute(
                        "UPDATE peer_counsellors SET profile_image_url = %s WHERE id = %s",
                        (best_image_url, original['id'])
                    )
                
                # Delete duplicates
                for dup in duplicates:
                    print(f"  Deleting duplicate ID {dup['id']} (Email: {dup['email']})...")
                    cursor.execute("DELETE FROM peer_counsellors WHERE id = %s", (dup['id'],))
                    duplicates_removed += 1

        conn.commit()
        print(f"\nCleanup complete. Removed {duplicates_removed} duplicate records.")
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_duplicates()
