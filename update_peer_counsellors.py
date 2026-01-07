import requests
import json

# API Configuration
# Use localhost for local testing: "http://127.0.0.1:8001"
API_BASE = "https://studconnect-backend.onrender.com"

peer_counsellors_data = [
    # 1. Navjot Navjot
    {
        "name": "Navjot Navjot",
        "email": "n0aveen0@gmail.com",
        "university": "Niagara College",
        "program": "Graduated",
        "location": "Scarborough, Canada",
        "profile_image_url": "https://lh3.googleusercontent.com/d/16LUdOulQMx8Q6RX_ESb7QiTm5Eh5HlUc",
        "about": "Business student with strong experience in customer service and administrative support. Passionate about helping students plan their study abroad journey with clear guidance and reliable assistance.",
        "charges": 699,
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
        "about": "A curious and solutions-driven MIT Sydney networking graduate with a passion for deconstructing and troubleshooting technology. Currently honing my analytical and customer-centric skills in the fast-paced retail industry. I'm also passionately developing my skills in the art of coffee brewing, expanding my reading list, and elevating my badminton game.",
        "charges": 699,
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
        "about": "Currently pursuing studies at Trinity College Dublin, I bring 1.5 years of experience as an Admission Support Officer at RMIT University. I am passionate about guiding students through their international education journey with first hand insights and honest advice.",
        "charges": 699,
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
        "about": "Pursuing a Master of Management at the University of Technology Sydney with a focus on data analytics, consulting and marketing strategy. Dedicated to empowering organizations with effective solutions while fostering strong relationships through exceptional customer service.",
        "charges": 699,
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
        "charges": 699,
        "languages": "English, Hindi"
    },
    # 6. Vijayan
    {
        "name": "Vijayan",
        "email": "vijayantrikha1998@gmail.com",
        "university": "George Brown College - St.James Campus, Toronto",
        "program": "Project Management - 2025",
        "location": "Toronto, Canada",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1ZCES9uhhGj2SeRaQA8aX-UfI6Eo5eCBN",
        "about": "Over 2 years of learning life abroad and achieving education milestones - Life is like a roller coaster and we gotta two choices, either suffer or enjoy and I am on the thrilling side taking steps towards success",
        "charges": 699,
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
        "charges": 699,
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
        "about": "Myself Adarsh Rana, I came UK back in 2024 for my post graduation (MBA) and have tackled Alot of problems in this journey till now.",
        "charges": 699,
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
        "charges": 699,
        "languages": "English"
    },
    # 10. Shrit Singh
    {
        "name": "Shrit Singh",
        "email": "shrit7@icloud.com",
        "university": "Auckland University",
        "program": "Level 5 Disability Aging and Health Care",
        "location": "India",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1ZCES9uhhGj2SeRaQA8aX-UfI6Eo5eCBN",
        "about": "I am a good learner",
        "charges": 699,
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
        "charges": 699,
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
        "about": "I am an MBA candidate at the University of Adelaide with a strong interest in strategy, leadership, and marketing. I am driven by curiosity, growth, and creating meaningful impact in teams and organisations.",
        "charges": 699,
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
        "charges": 699,
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
        "about": "I am a medical student currently living in Russia doing my studies. Belongs to a decent family and I have experienced many good and bad things in my life. Can be a good advisor for people regarding the things I have been through.",
        "charges": 699,
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
        "about": "Hi, My name is Navjot. Im a marketing graduate working as a learning ambassador in Amazon Canada helping new hires to onboard. Living in Canada from the last 2 years and completely enjoying the country and its opportunities.",
        "charges": 699,
        "languages": "English, Hindi"
    },
    # 16. Nandini Pandey
    {
        "name": "Nandini Pandey",
        "email": "nandinipandey083@gmail.com",
        "university": "Queen Mary University of London",
        "program": "MSc Biotechnology & Synthetic Biology, 2025-2026",
        "location": "Ggn-India / London-UK",
        "profile_image_url": "https://lh3.googleusercontent.com/d/1ZCES9uhhGj2SeRaQA8aX-UfI6Eo5eCBN",
        "about": "Nandini Pandey, Emerging Biotechnology graduate & Climate Youth Leader working at the intersection of science, sustainability & community impact. Works with Commonwealth (INDIA) and student organizations in UK.",
        "charges": 699,
        "languages": "English, Hindi"
    }
]

def update_peer_counsellors():
    print(f"Starting update process on: {API_BASE}")
    
    updated_count = 0
    failed_count = 0

    for counsellor in peer_counsellors_data:
        try:
            # Note: Ensure all required fields are filled before running
            response = requests.post(f"{API_BASE}/peer-counsellors/upsert", json=counsellor)
            
            if response.status_code in [200, 201]:
                print(f"Updated: {counsellor['name']}")
                updated_count += 1
            else:
                print(f"Failed: {counsellor['name']} (Status: {response.status_code}) - {response.text}")
                failed_count += 1
                
        except Exception as e:
            print(f"Error updating {counsellor['name']}: {str(e)}")
            failed_count += 1
    
    print(f"\nUpdate complete. Success: {updated_count}, Failed: {failed_count}")

if __name__ == "__main__":
    update_peer_counsellors()