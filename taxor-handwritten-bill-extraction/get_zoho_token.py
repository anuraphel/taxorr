import os
import requests
from dotenv import load_dotenv

def get_refresh_token():
    load_dotenv()
    
    client_id = os.environ.get("ZOHO_CLIENT_ID", "")
    client_secret = os.environ.get("ZOHO_CLIENT_SECRET", "")
    
    if "your_" in client_id or not client_id:
        client_id = input("Enter Zoho Client ID: ").strip()
    if "your_" in client_secret or not client_secret:
        client_secret = input("Enter Zoho Client Secret: ").strip()
        
    auth_code = input("Enter the generated Authorization Code: ").strip()
    
    # Try different regional Zoho OAuth endpoints
    regions = ["in", "com", "eu", "com.au"]
    success = False
    
    for region in regions:
        url = f"https://accounts.zoho.{region}/oauth/v2/token"
        params = {
            "code": auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code"
        }
        
        print(f"Trying region '{region}' OAuth endpoint...")
        try:
            response = requests.post(url, params=params)
            data = response.json()
            
            if "refresh_token" in data:
                refresh_token = data["refresh_token"]
                print(f"\n🎉 Success! Detected region: Zoho {region.upper()}")
                print(f"Refresh Token: {refresh_token}")
                
                # Write to .env
                import re
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
                with open(env_path, "r") as f:
                    content = f.read()
                
                # Always replace existing values using regex (works even if token was already set)
                content = re.sub(r"ZOHO_REFRESH_TOKEN=.*", f"ZOHO_REFRESH_TOKEN={refresh_token}", content)
                
                # Update region
                if "ZOHO_REGION=" not in content:
                    content += f"\nZOHO_REGION={region}\n"
                else:
                    content = re.sub(r"ZOHO_REGION=\S*", f"ZOHO_REGION={region}", content)
                    
                with open(env_path, "w") as f:
                    f.write(content)
                print("Updated .env file successfully!")
                success = True
                break
            else:
                # If it's a real invalid client, we continue to check other domains.
                # If it's a code expiration, it might fail for all.
                if data.get("error") == "invalid_code":
                    print(f"❌ Authorization code is invalid or expired. Please generate a new code in Zoho console.")
                    return
                print(f"Region '{region}' failed: {data.get('error')}")
        except Exception as e:
            print(f"Exception for region '{region}': {e}")
            
    if not success:
        print("\n❌ Failed to acquire refresh token from all Zoho regional servers. Please check:")
        print("1. Did you copy the Client ID and Secret correctly?")
        print("2. Is your Self-Client registered under the same account region?")
        print("3. Ensure your authorization code is fresh (it expires in 3 minutes).")

if __name__ == "__main__":
    get_refresh_token()
