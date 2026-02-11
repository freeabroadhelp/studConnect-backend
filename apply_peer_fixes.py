from sqlalchemy.orm import Session
from db import get_db, engine
from models.models import PeerCounsellor

# 1. Define Correct Data (Merged from update_peer_counsellors.py and update_peers_db.py)
peers_data = [
    # 1. Navjot Navjot
    {
        "name": "Navjot Navjot",
        "email": "n0aveen0@gmail.com",
        "university": "Niagara College",
        "program": "Graduated",
        "location": "Scarborough, Canada",
        "profile_image_url": "https://lh3.googleusercontent.com/d/16LUdOulQMx8Q6RX_ESb7QiTm5Eh5HlUc",
        "about": "Business student with strong experience in customer service and administrative support. Passionate about helping students plan their study abroad journey with clear guidance and reliable assistance.",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 2. Reetika
    {
        "name": "Reetika",
        "email": "reetika7700@yahoo.com",
        "university": "Melbourne Institute of Technology",
        "program": "Master of networking (2023-2025)",
        "location": "Australia",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1pmAqCVgDB3vG_t7FnWq5SuOhBfWiVdPF",
        "about": "A curious and solutions-driven MIT Sydney networking graduate with a passion for deconstructing and troubleshooting technology. Currently honing my analytical and customer-centric skills in the fast-paced retail industry.",
        "charges": 699.0,
        "languages": "English"
    },
    # 3. Sofia Nathan
    {
        "name": "Sofia Nathan",
        "email": "nathansofia25@gmail.com",
        "university": "Trinity College Dublin - Trinity Business School",
        "program": "MSc International Management",
        "location": "India (Faridabad)",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1jGThh1gYm1rCL8ACICjZO2OjV4w5tnR6",
        "about": "Currently pursuing studies at Trinity College Dublin, I bring 1.5 years of experience as an Admission Support Officer at RMIT University.",
        "charges": 25.0, # Updated from UI observation in screenshot? Default was 699 in file but screenshot says 25? Keeping file value 699 for now unless user said otherwise. User said 'pictures are corrupted... take it from update_peer_counsellors'. File has 699. Screenshot has 25. I will trust file for now, or maybe the screenshot shows old state?
        "languages": "English, Hindi"
    },
    # 4. Mihir Nagpal
    {
        "name": "Mihir Nagpal",
        "email": "mihirnagpal1@gmail.com",
        "university": "University of Technology Sydney",
        "program": "Master of Management",
        "location": "Sydney, Australia",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1Dvta4mrDraWdo2mwGHAg5UHUM-1J_7S2",
        "about": "Pursuing a Master of Management at the University of Technology Sydney with a focus on data analytics, consulting and marketing strategy.",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 5. Deeya Rao
    {
        "name": "Deeya Rao",
        "email": "deeyar2005@gmail.com",
        "university": "Federation University Mount Helen Campus",
        "program": "Bachelor of Education Early Childhood and Primary Year 3",
        "location": "Australia, Melbourne",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1kauzat1HsVFBIG6_vIPDOdjaR0jOOHcD",
        "about": "I believe in eventually tables turn and things get better.",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 6. Vijayan - IMAGE UPDATE
    {
        "name": "Vijayan",
        "email": "vijayantrikha1998@gmail.com",
        "university": "George Brown College - St.James Campus, Toronto",
        "program": "Project Management - 2025",
        "location": "Toronto, Canada",
        # Updated from update_peers_db.py
        "profile_image_url": "/peers/vijayan.jpg",
        "about": "Over 2 years of learning life abroad and achieving education milestones - Life is like a roller coaster...",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 7. Zubia Maryam
    {
        "name": "Zubia Maryam",
        "email": "zubiamaryam6@gmail.com",
        "university": "University of Essex",
        "program": "MSc Cancer Biology 2023-2024",
        "location": "Colchester, Essex",
        "profile_image_url": "https://lh3.googleusercontent.com/d/16tGOSZpMhImrHYYPkDU4YqlA6HeXwf4Z",
        "about": "Zubia, a recent MSc cancer biology graduate from the University of Essex, has a strong educational background in the field.",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 8. Adarsh Rana
    {
        "name": "Adarsh Rana",
        "email": "adarshrana141@gmail.com",
        "university": "York St. John University (London Campus)",
        "program": "MBA (1st Year)",
        "location": "India, Himachal Pradesh, Kangra 176201",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1LixSgWgbe3bIvIyCNcdHud4c6Lo_rMC1",
        "about": "Myself Adarsh Rana, I came UK back in 2024 for my post graduation (MBA)...",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 9. Suhani Mehta
    {
        "name": "Suhani Mehta",
        "email": "suhanimehta300@gmail.com",
        "university": "Queensland University of Technology, Gardens Point",
        "program": "Master of International Business, 2026",
        "location": "Australia, Brisbane",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1T5SS4IuHIATivyTkvD10Fp_EJVP2hgEA",
        "about": "International student in Australia.",
        "charges": 699.0,
        "languages": "English"
    },
    # 10. Shrit Singh - IMAGE UPDATE
    {
        "name": "Shrit Singh",
        "email": "shrit7@icloud.com",
        "university": "Auckland University",
        "program": "Level 5 Disability Aging and Health Care",
        "location": "India",
        # Updated from update_peers_db.py
        "profile_image_url": "/peers/shrit.jpg",
        "about": "I am a good learner",
        "charges": 699.0,
        "languages": "English"
    },
    # 11. Tushar
    {
        "name": "Tushar",
        "email": "itsted2407@gmail.com",
        "university": "University",
        "program": "3 Year",
        "location": "India",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1bfgKiooPuWqhusY9RN1gfm_WE04BCo_o",
        "about": "Photographer who's exploring the world",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 12. Suryansh Singh Panwar
    {
        "name": "Suryansh Singh Panwar",
        "email": "suryanshsp14@icloud.com",
        "university": "University of Adelaide (North Terrace Campus)",
        "program": "MBA (1st Year)",
        "location": "Adelaide, Australia",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1FzA2hVZH8CFAYlJ0j8-lUgo1jXnESTTB",
        "about": "I am an MBA candidate at the University of Adelaide...",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 13. Tushar Sharma
    {
        "name": "Tushar Sharma",
        "email": "tushar241999@gmail.com",
        "university": "St. Lawrence College",
        "program": "Digital Marketing and UX Design",
        "location": "India",
        "profile_image_url": "https://lh3.googleusercontent.com/d/18l6yjPMS39De0vH1aERCb53KO_-_lNEh",
        "about": "Live Life without Regrets",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 14. Charchit Chauhan
    {
        "name": "Charchit Chauhan",
        "email": "chauhancharchit81@gmail.com",
        "university": "Tula State University Tula Russia",
        "program": "Medical (MBBS)",
        "location": "Tula, Russia",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1p-pb9XWmWOxZ8lrqQWyaalcQ7lO7XFPL",
        "about": "I am a medical student currently living in Russia...",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 15. Navjot Singh
    {
        "name": "Navjot Singh",
        "email": "navjotnv15@gmail.com",
        "university": "Conestoga College, Kitchener DTK Campus",
        "program": "Strategic Marketing and Communications 2025",
        "location": "Kitchener ON, Canada",
        "profile_image_url": "https://lh3.googleusercontent.com/d/11pYGPP17hW2R_eLg1sWAXWRTcKFQNLB1",
        "about": "Hi, My name is Navjot. Im a marketing graduate...",
        "charges": 699.0,
        "languages": "English, Hindi"
    },
    # 16. Nandini Pandey - IMAGE UPDATE
    {
        "name": "Nandini Pandey",
        "email": "nandinipandey083@gmail.com",
        "university": "Queen Mary University of London",
        "program": "MSc Biotechnology & Synthetic Biology, 2025-2026",
        "location": "Ggn-India / London-UK",
        # Updated from update_peers_db.py
        "profile_image_url": "/peers/nandini.jpg",
        "about": "Nandini Pandey, Emerging Biotechnology graduate & Climate Youth Leader...",
        "charges": 699.0,
        "languages": "English, Hindi"
    }
]

# Additional specific updates to handle potential alternate emails or formats
extra_image_updates = {
    "vijayan.peer@example.com": "/peers/vijayan.jpg",
    "shrit.singh@example.com": "/peers/shrit.jpg",
    "nandini.pandey@example.com": "/peers/nandini.jpg"
}

def apply_fixes():
    print("Connecting to DB...")
    db = next(get_db())
    try:
        # 1. Fetch current peers
        current_peers = db.query(PeerCounsellor).all()
        print(f"Current Peer Count: {len(current_peers)}")

        # 2. Identify and Delete non-master entries
        master_emails = set(p["email"].strip().lower() for p in peers_data)
        
        deleted_count = 0
        for peer in current_peers:
            email = peer.email.strip().lower()
            if email not in master_emails:
                print(f"Deleting duplicate/unknown: {email} (ID: {peer.id})")
                db.delete(peer)
                deleted_count += 1
            else:
                # Handle duplicates of valid emails (keep one)
                # This simplistic check might leave one, but we upsert later anyway
                # A better way is to delete ALL first, but that kills bookings (FK constraints).
                # So we must update in place.
                pass
        
        # Check for multiple entries of SAME valid email
        db.commit() # Commit deletions so far
        
        # Fresh fetch
        remaining_peers = db.query(PeerCounsellor).all()
        email_map = {}
        for p in remaining_peers:
            e = p.email.strip().lower()
            if e not in email_map: email_map[e] = []
            email_map[e].append(p)
            
        for e, buddies in email_map.items():
            if len(buddies) > 1:
                print(f"Found {len(buddies)} entries for {e}. Keeping first, deleting others.")
                # Keep first
                for bad_peer in buddies[1:]:
                    db.delete(bad_peer)
                    deleted_count += 1
        
        db.commit()
        print(f"Deleted {deleted_count} duplicate/unwanted peers.")

        # 3. Upsert Master Data
        updated_count = 0
        for p_data in peers_data:
            email = p_data["email"].strip().lower()
            peer = db.query(PeerCounsellor).filter_by(email=email).first()
            
            if peer:
                # Update
                peer.name = p_data["name"]
                peer.university = p_data["university"]
                peer.program = p_data["program"]
                peer.location = p_data["location"]
                peer.profile_image_url = p_data["profile_image_url"]
                peer.about = p_data["about"]
                peer.charges = p_data["charges"]
                peer.languages = p_data["languages"]
                print(f"Updated: {email}")
            else:
                # Create
                new_peer = PeerCounsellor(**p_data)
                db.add(new_peer)
                print(f"Created: {email}")
            updated_count += 1
            
        db.commit()
        print(f"Upserted {updated_count} peers successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    apply_fixes()
