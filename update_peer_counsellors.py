import requests
import json

# Define the API endpoint
# API_BASE = "https://studconnect-backend.onrender.com"
# If running locally, use: API_BASE = "http://127.0.0.1:8001"
API_BASE = "http://127.0.0.1:8001"

# Define the new peer counsellors data
peer_counsellors_data = [
    {
        "email": "sofia.nathan@example.com",
        "name": "Sofia Nathan",
        "university": "Trinity College Dublin - Trinity Business School",
        "program": "MSc International Management",
        "location": "India (Faridabad)",
        "profile_image_url": "https://pub-e63ee2f49d7e4f94b98011a5350eea0f.r2.dev/sofia.jpg",
        "about": "Experienced peer counsellor with expertise in international management studies.",
        "charges": 25.00,
        "languages": "English, Hindi"
    },
    {
        "email": "deeya.rao@example.com",
        "name": "Deeya Rao",
        "university": "Federation University Mount Helen Campus",
        "program": "Bachelor of Education",
        "location": "Australia, Melbourne",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D5603AQFwP0wWQ2xx5Q/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1706663723339?e=2147483647&v=beta&t=ho3rTd-1ZxmhSYs3_T-aw2TSvN6fmbqQQJqzyH57vbY",
        "about": "Education specialist providing guidance on teaching programs and career paths.",
        "charges": 20.00,
        "languages": "English"
    },
    {
        "email": "vijayan.peer@example.com",
        "name": "Vijayan",
        "university": "Trinity College Dublin",
        "program": "Computer Science",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D4E03AQEDnr-dbqNsoQ/profile-displayphoto-scale_200_200/B4EZsT1aBTKUAY-/0/1765564326692?e=2147483647&v=beta&t=LFzecktMstpLsmMGoTWWgxeageNDVpdkbTl_0uYvgRc",
        "about": "Technology expert helping students with computer science and software engineering programs.",
        "charges": 30.00,
        "languages": "English, Tamil"
    },
    {
        "email": "zubia.maryam@example.com",
        "name": "Zubia Maryam",
        "university": "Trinity College Dublin",
        "program": "Biomedical Engineering",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D4E35AQGHcAGw0Jfihw/profile-framedphoto-shrink_400_400/B4EZjO33uTGoAc-/0/1755817409683?e=1767783600&v=beta&t=m0lRLghFwS41EIDVc3Q4xfoLsc251cx6JU0eabD4OqA",
        "about": "Biomedical engineering specialist with experience in research and industry applications.",
        "charges": 30.00,
        "languages": "English, Urdu"
    },
    {
        "email": "nandini.pandey@example.com",
        "name": "Nandini Pandey",
        "university": "University College Dublin",
        "program": "Business Administration",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D4E03AQGK39LMgCAbcQ/profile-displayphoto-scale_200_200/B4EZre5w9UKkAY-/0/1764676276794?e=2147483647&v=beta&t=Wg6kMLBDgUMzMZgGaJY2Qu5r_17OyGWrNit51K0OAgo",
        "about": "Business administration expert with focus on marketing and strategy.",
        "charges": 28.00,
        "languages": "English, Hindi"
    },
    {
        "email": "navjot.singh@example.com",
        "name": "Navjot Singh",
        "university": "Dublin City University",
        "program": "International Relations",
        "location": "Ireland",
        "profile_image_url": "https://pub-e63ee2f49d7e4f94b98011a5350eea0f.r2.dev/Navjot%20Singh.HEIC",
        "about": "International relations specialist with expertise in global studies and diplomacy.",
        "charges": 27.00,
        "languages": "English, Punjabi, Hindi"
    },
    {
        "email": "adarsh.kumar@example.com",
        "name": "Adarsh",
        "university": "National University of Ireland, Galway",
        "program": "Mechanical Engineering",
        "location": "Ireland",
        "profile_image_url": "https://pub-e63ee2f49d7e4f94b98011a5350eea0f.r2.dev/Adarsh.jpg",
        "about": "Mechanical engineering expert with experience in design and manufacturing.",
        "charges": 29.00,
        "languages": "English, Hindi"
    },
    {
        "email": "suhani.sharma@example.com",
        "name": "Suhani",
        "university": "Trinity College Dublin",
        "program": "Psychology",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/C4D03AQHT248XGnMNfA/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1655185683632?e=2147483647&v=beta&t=G8tUfQ6a83bdx4w_fipoRLa5PODLAxFxdu9wCkRk4zM",
        "about": "Psychology expert specializing in student wellbeing and academic success.",
        "charges": 26.00,
        "languages": "English, Hindi"
    },
    {
        "email": "shrit.singh@example.com",
        "name": "Shrit Singh",
        "university": "University College Cork",
        "program": "Law",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/C4D03AQE2xipsYabvug/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1610456587335?e=1769040000&v=beta&t=ZJfJ6mlTupD1skQtLH_PQCDepdssqW6G4-2bIL8PDIc",
        "about": "Legal expert providing guidance on law programs and career paths.",
        "charges": 32.00,
        "languages": "English, Hindi"
    },
    {
        "email": "tushar.sharma@example.com",
        "name": "Tushar Sharma",
        "university": "Dublin Institute of Technology",
        "program": "Computer Science",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/C5103AQEwyI6-CTbNuw/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1549604196130?e=1769040000&v=beta&t=8chP25EWxmWzWnx1j0arXbmUsrAZUKvZG5bWH1MlPr4",
        "about": "Computer science specialist with industry experience in software development.",
        "charges": 30.00,
        "languages": "English, Hindi"
    },
    {
        "email": "suryansh.gupta@example.com",
        "name": "Suryansh",
        "university": "Trinity College Dublin",
        "program": "Finance",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D5603AQFf14t7zuF-1A/profile-displayphoto-scale_400_400/B56Zqrq7wEIcAk-/0/1763816781914?e=1769040000&v=beta&t=WpMVu-RlMIuPUEy7HFUz9sz8ziLhTfa0Db1UtWYcf8o",
        "about": "Finance expert with experience in investment banking and financial analysis.",
        "charges": 33.00,
        "languages": "English, Hindi"
    },
    {
        "email": "tushar.mehra@example.com",
        "name": "Tushar",
        "university": "University College Dublin",
        "program": "Data Science",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D5603AQEW7rkf2-tVbA/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1726990956230?e=1769040000&v=beta&t=xIPtrCXOZ2qMZ7D06be-R9s9SOb6wq5jxJTwtpr6FLU",
        "about": "Data science specialist with expertise in machine learning and analytics.",
        "charges": 31.00,
        "languages": "English, Hindi"
    },
    {
        "email": "charchit.agarwal@example.com",
        "name": "Charchit",
        "university": "Dublin City University",
        "program": "Marketing",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D4D03AQEVz3_3LSZb4g/profile-displayphoto-scale_400_400/B4DZkRCXxiIYAs-/0/1756927460546?e=1769040000&v=beta&t=JdMTzV4Me_qVThsHZ0YtJawX4KDOnut06FZLnBA8F8w",
        "about": "Marketing expert with experience in digital marketing and brand strategy.",
        "charges": 28.00,
        "languages": "English, Hindi"
    },
    {
        "email": "navjot.kaur@example.com",
        "name": "Navjot",
        "university": "University College Cork",
        "program": "Nursing",
        "location": "Ireland",
        "profile_image_url": "https://media.licdn.com/dms/image/v2/D5603AQFwk6QHywlWGQ/profile-displayphoto-scale_400_400/B56Zel.aKFH8Ao-/0/1750836293236?e=1769040000&v=beta&t=sq53x5O2cTWpdL9L0Xgr6KAs9PspLfrq0s7BqXqXpCA",
        "about": "Nursing specialist with clinical experience and academic guidance.",
        "charges": 27.00,
        "languages": "English, Punjabi"
    }
]

def update_peer_counsellors():
    print("Updating peer counsellors data...")
    
    for counsellor in peer_counsellors_data:
        try:
            print(f"Updating: {counsellor['name']}")
            response = requests.post(f"{API_BASE}/peer-counsellors/upsert", json=counsellor)
            
            if response.status_code == 201:
                print(f"✓ Successfully updated {counsellor['name']}")
            else:
                print(f"✗ Failed to update {counsellor['name']}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"✗ Error updating {counsellor['name']}: {str(e)}")
    
    print("Peer counsellors update process completed.")

if __name__ == "__main__":
    update_peer_counsellors()