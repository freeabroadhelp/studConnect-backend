import sqlite3
import os

DB_FILE = "studConnect.db"

def fix_duplicates():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found!")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Fetch all peer counsellors
        cursor.execute("SELECT * FROM peer_counsellors ORDER BY id ASC")
        rows = cursor.fetchall()
        
        # Group by normalized NAME
        by_name = {}
        for row in rows:
            name_key = row['name'].strip().lower()
            if name_key not in by_name:
                by_name[name_key] = []
            by_name[name_key].append(dict(row))

        duplicates_removed = 0
        
        for name, records in by_name.items():
            if len(records) > 1:
                print(f"Processing duplicates for: {records[0]['name']}")
                
                # First record is likely the original (lowest ID)
                original = records[0]
                duplicates = records[1:]
                
                # Identify the "best" image URL to keep
                # We prefer the one that has 'thumbnail' format if available
                best_image_url = original['profile_image_url']
                for r in records:
                    url = r['profile_image_url']
                    if url and "thumbnail" in url:
                        best_image_url = url
                        break # Found a good one, stick with it? Or maybe check others? 
                        # Actually, if we have multiple, just take the first good one.
                
                # Ensure the original record gets this image URL
                if original['profile_image_url'] != best_image_url:
                    print(f"  Updating original ID {original['id']} with new image URL...")
                    cursor.execute(
                        "UPDATE peer_counsellors SET profile_image_url = ? WHERE id = ?",
                        (best_image_url, original['id'])
                    )
                
                # Delete duplicate records
                for dup in duplicates:
                    print(f"  Deleting duplicate ID {dup['id']} (Email: {dup['email']})...")
                    cursor.execute("DELETE FROM peer_counsellors WHERE id = ?", (dup['id'],))
                    duplicates_removed += 1

        conn.commit()
        print(f"\nCleanup complete. Removed {duplicates_removed} duplicate records.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_duplicates()
