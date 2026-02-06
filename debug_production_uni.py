import os
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not set in environment.")
    exit(1)

# Connect to database
engine = create_engine(DATABASE_URL)

def inspect_university(name_pattern):
    print(f"\n--- Searching for university: '{name_pattern}' ---")
    with engine.connect() as conn:
        # Use simple text query to bypass model issues
        query = text("""
            SELECT id, attributes 
            FROM universities 
            WHERE attributes->>'name' ILIKE :pattern
            LIMIT 1
        """)
        
        result = conn.execute(query, {"pattern": f"%{name_pattern}%"}).fetchone()
        
        if result:
            uni_id, attributes = result
            print(f"Found ID: {uni_id}")
            print("Raw Attributes JSON:")
            print(json.dumps(attributes, indent=2))
            
            # Key Analysis
            print("\n--- Key Check ---")
            print(f"Name: {attributes.get('name')}")
            print(f"City: {attributes.get('city')}")
            print(f"State keys check: province={attributes.get('province')}, state={attributes.get('state')}, region={attributes.get('region')}")
            print(f"Country: {attributes.get('country')}")
            print(f"Tuition keys check: avg_tuition={attributes.get('avg_tuition')}, tuition_minimum={attributes.get('tuition_minimum')}, tuitionMinimum={attributes.get('tuitionMinimum')}")
            print(f"Levels keys check: program_levels={attributes.get('program_levels')}, levels_offered={attributes.get('levels_offered')}, degreeTypes={attributes.get('degreeTypes')}")
            print(f"Scholarships keys check: {attributes.get('scholarships')}")
        else:
            print("No university found matching that name.")

if __name__ == "__main__":
    import sys
    # Redirect stdout to a file
    with open("debug_output.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        inspect_university("Trinity College Dublin")
        print("\n--- Done ---")
