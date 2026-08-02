import os
import requests
from dotenv import load_dotenv

def diagnose():
    load_dotenv()
    client_id = os.environ.get("ZOHO_CLIENT_ID")
    client_secret = os.environ.get("ZOHO_CLIENT_SECRET")
    refresh_token = os.environ.get("ZOHO_REFRESH_TOKEN")
    region = os.environ.get("ZOHO_REGION", "com")
    
    print("--- Zoho Diagnostics ---")
    print(f"Region: {region}")
    print(f"Client ID: {client_id[:10]}...")
    print(f"Client Secret: {client_secret[:5]}... (Length: {len(client_secret) if client_secret else 0})")
    print(f"Refresh Token: {refresh_token[:15]}... (Length: {len(refresh_token) if refresh_token else 0})")
    
    # 1. Test token refresh
    url = f"https://accounts.zoho.{region}/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    
    print("\nRefreshing Access Token...")
    try:
        response = requests.post(url, params=params)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print("Response JSON:")
        print(data)
        
        if "access_token" in data:
            access_token = data["access_token"]
            print("\n[SUCCESS] Successfully got access token!")
            
            # 2. Test fetching organizations
            org_url = f"https://books.zoho.{region}/api/v3/organizations"
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            print(f"\nFetching organizations from {org_url}...")
            org_response = requests.get(org_url, headers=headers)
            print(f"Status Code: {org_response.status_code}")
            org_data = org_response.json()
            print("Response JSON:")
            print(org_data)
        else:
            print("\n[FAIL] Failed to get access token from Zoho.")
            
    except Exception as e:
        print(f"Exception during request: {e}")

if __name__ == "__main__":
    diagnose()
