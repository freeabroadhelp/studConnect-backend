from sqlalchemy.orm import Session
from sqlalchemy import text
from db import get_db
from models.models import PeerCounsellor, PeerCounsellorAvailability, PeerCounsellorBooking

# 1. Define Correct Data (Merged)
peers_data = [
    # 1. Navjot Navjot
    {
        "name": "Navjot Navjot",
        "email": "n0aveen0@gmail.com",
        "university": "Niagara College",
        "program": "Graduated",
        "location": "Scarborough, Canada",
        "profile_image_url": "https://lh3.googleusercontent.com/d/16LUdOulQMx8Q6RX_ESb7QiTm5Eh5HlUc",
        "about": "Business student with strong experience... clear guidance and reliable assistance.",
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
        "about": "A curious and solutions-driven MIT Sydney networking graduate...",
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
        "about": "Currently pursuing studies at Trinity College Dublin...",
        "charges": 699.0, 
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
        "about": "Pursuing a Master of Management...",
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
        "profile_image_url": "/peers/vijayan.jpg",
        "about": "Over 2 years of learning life abroad...",
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
        "about": "Zubia, a recent MSc cancer biology graduate...",
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
        "about": "Myself Adarsh Rana, I came UK back in 2024...",
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
        "profile_image_url": "/peers/nandini.jpg",
        "about": "Nandini Pandey, Emerging Biotechnology graduate...",
        "charges": 699.0,
        "languages": "English, Hindi"
    }
]

def force_cleanup():
    print("Connecting to DB...")
    db = next(get_db())
    try:
        print("FORCING CLEANUP: Deleting bookings, availability, and counsellors...")
        
        # 1. Delete dependent children (Bookings, Availabilities)
        # We use raw SQL or ORM delete. ORM is safer for ongoing session.
        deleted_bookings = db.query(PeerCounsellorBooking).delete()
        print(f"Deleted {deleted_bookings} bookings.")
        
        deleted_slots = db.query(PeerCounsellorAvailability).delete()
        print(f"Deleted {deleted_slots} availability slots.")
        
        deleted_peers = db.query(PeerCounsellor).delete()
        print(f"Deleted {deleted_peers} peer counsellors.")
        
        db.commit()
        print("Database wiped (peer tables only).")

        # 2. Re-insert Correct Data
        print(f"Inserting {len(peers_data)} clean records...")
        for p_data in peers_data:
            peer = PeerCounsellor(**p_data)
            db.add(peer)
            
        db.commit()
        print("Success! Database populated with clean data.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    force_cleanup()
