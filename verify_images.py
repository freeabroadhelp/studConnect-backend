import requests
from urllib.parse import urlparse

# List of image URLs to verify
image_urls = [
    "https://pub-e63ee2f49d7e4f94b98011a5350eea0f.r2.dev/sofia.jpg",
    "https://media.licdn.com/dms/image/v2/D5603AQFwP0wWQ2xx5Q/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1706663723339?e=2147483647&v=beta&t=ho3rTd-1ZxmhSYs3_T-aw2TSvN6fmbqQQJqzyH57vbY",
    "https://media.licdn.com/dms/image/v2/D4E03AQEDnr-dbqNsoQ/profile-displayphoto-scale_200_200/B4EZsT1aBTKUAY-/0/1765564326692?e=2147483647&v=beta&t=LFzecktMstpLsmMGoTWWgxeageNDVpdkbTl_0uYvgRc",
    "https://media.licdn.com/dms/image/v2/D4E35AQGHcAGw0Jfihw/profile-framedphoto-shrink_400_400/B4EZjO33uTGoAc-/0/1755817409683?e=1767783600&v=beta&t=m0lRLghFwS41EIDVc3Q4xfoLsc251cx6JU0eabD4OqA",
    "https://media.licdn.com/dms/image/v2/D4E03AQGK39LMgCAbcQ/profile-displayphoto-scale_200_200/B4EZre5w9UKkAY-/0/1764676276794?e=2147483647&v=beta&t=Wg6kMLBDgUMzMZgGaJY2Qu5r_17OyGWrNit51K0OAgo",
    "https://pub-e63ee2f49d7e4f94b98011a5350eea0f.r2.dev/Navjot%20Singh.HEIC",
    "https://pub-e63ee2f49d7e4f94b98011a5350eea0f.r2.dev/Adarsh.jpg",
    "https://media.licdn.com/dms/image/v2/C4D03AQHT248XGnMNfA/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1655185683632?e=2147483647&v=beta&t=G8tUfQ6a83bdx4w_fipoRLa5PODLAxFxdu9wCkRk4zM",
    "https://media.licdn.com/dms/image/v2/C4D03AQE2xipsYabvug/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1610456587335?e=1769040000&v=beta&t=ZJfJ6mlTupD1skQtLH_PQCDepdssqW6G4-2bIL8PDIc",
    "https://media.licdn.com/dms/image/v2/C5103AQEwyI6-CTbNuw/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1549604196130?e=1769040000&v=beta&t=8chP25EWxmWzWnx1j0arXbmUsrAZUKvZG5bWH1MlPr4",
    "https://media.licdn.com/dms/image/v2/D5603AQFf14t7zuF-1A/profile-displayphoto-scale_400_400/B56Zqrq7wEIcAk-/0/1763816781914?e=1769040000&v=beta&t=WpMVu-RlMIuPUEy7HFUz9sz8ziLhTfa0Db1UtWYcf8o",
    "https://media.licdn.com/dms/image/v2/D5603AQEW7rkf2-tVbA/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1726990956230?e=1769040000&v=beta&t=xIPtrCXOZ2qMZ7D06be-R9s9SOb6wq5jxJTwtpr6FLU",
    "https://media.licdn.com/dms/image/v2/D4D03AQEVz3_3LSZb4g/profile-displayphoto-scale_400_400/B4DZkRCXxiIYAs-/0/1756927460546?e=1769040000&v=beta&t=JdMTzV4Me_qVThsHZ0YtJawX4KDOnut06FZLnBA8F8w",
    "https://media.licdn.com/dms/image/v2/D5603AQFwk6QHywlWGQ/profile-displayphoto-scale_400_400/B56Zel.aKFH8Ao-/0/1750836293236?e=1769040000&v=beta&t=sq53x5O2cTWpdL9L0Xgr6KAs9PspLfrq0s7BqXqXpCA"
]

def verify_image_urls():
    print("Verifying image URLs...")
    
    for i, url in enumerate(image_urls):
        try:
            print(f"Checking image {i+1}: {url}")
            
            # Check if URL is accessible
            response = requests.head(url, timeout=10)  # Use HEAD to just check headers
            
            if response.status_code == 200:
                print(f"✓ Image {i+1} is accessible")
            else:
                print(f"✗ Image {i+1} returned status code: {response.status_code}")
                
                # Try with GET request if HEAD fails
                response_get = requests.get(url, timeout=10)
                if response_get.status_code == 200:
                    print(f"✓ Image {i+1} is accessible with GET request")
                else:
                    print(f"✗ Image {i+1} is not accessible with GET request either: {response_get.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"✗ Error checking image {i+1}: {str(e)}")
        
        print()  # Empty line for readability

if __name__ == "__main__":
    verify_image_urls()