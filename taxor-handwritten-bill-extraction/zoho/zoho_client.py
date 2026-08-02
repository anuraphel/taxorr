import os
import requests
import json
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load env variables at initialization
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZohoBooksClient")

class ZohoBooksClient:
    def __init__(self):
        self.client_id = os.environ.get("ZOHO_CLIENT_ID", "")
        self.client_secret = os.environ.get("ZOHO_CLIENT_SECRET", "")
        self.refresh_token = os.environ.get("ZOHO_REFRESH_TOKEN", "")
        self.access_token: Optional[str] = None
        self.region = os.environ.get("ZOHO_REGION", "com").lower()
        # Zoho Books REST API base URL uses zohoapis.<region> domain (not books.zoho.<region>)
        # e.g. https://www.zohoapis.in/books/v3 for India
        if self.region == "in":
            self.api_base_url = "https://www.zohoapis.in/books/v3"
        elif self.region == "eu":
            self.api_base_url = "https://www.zohoapis.eu/books/v3"
        elif self.region == "com.au":
            self.api_base_url = "https://www.zohoapis.com.au/books/v3"
        else:
            self.api_base_url = "https://www.zohoapis.com/books/v3"
        self.is_mock = self._check_is_mock()

    def _check_is_mock(self) -> bool:
        """Determines if the client should run in mock mode."""
        missing_creds = not (self.client_id and self.client_secret and self.refresh_token)
        placeholder_creds = any("your_" in token for token in [self.client_id, self.client_secret, self.refresh_token])
        return missing_creds or placeholder_creds

    def refresh_access_token(self) -> bool:
        """Refreshes the OAuth 2.0 access token using the refresh token."""
        if self.is_mock:
            logger.info("[Mock Mode] Simulated successful OAuth access token refresh.")
            self.access_token = "mock_access_token_xyz123"
            return True

        url = f"https://accounts.zoho.{self.region}/oauth/v2/token"
        params = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(url, params=params)
            response_json = response.json()
            if response.status_code == 200 and "access_token" in response_json:
                self.access_token = response_json["access_token"]
                logger.info("Successfully refreshed Zoho access token.")
                return True
            else:
                logger.error(f"Failed to refresh Zoho token: {response_json}")
                return False
        except Exception as e:
            logger.error(f"Exception during Zoho token refresh: {e}")
            return False

    def get_organizations(self) -> List[Dict[str, Any]]:
        """Retrieves list of organizations in the Zoho Books account."""
        if self.is_mock:
            return [{"organization_id": "mock_org_9988", "name": "Mock Sandbox Organization"}]

        if not self.access_token and not self.refresh_access_token():
            return []

        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }
        url = f"{self.api_base_url}/organizations"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json().get("organizations", [])
            else:
                logger.error(f"Error fetching organizations: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Exception fetching organizations: {e}")
            return []

    def get_expense_accounts(self, organization_id: str) -> List[Dict[str, Any]]:
        """Retrieves list of active expense chart of accounts."""
        if self.is_mock:
            return [
                {"account_id": "mock_acc_101", "account_name": "Travel Expense"},
                {"account_id": "mock_acc_102", "account_name": "Office Supplies"},
                {"account_id": "mock_acc_103", "account_name": "Meals and Entertainment"},
                {"account_id": "mock_acc_104", "account_name": "General Expense"}
            ]

        if not self.access_token and not self.refresh_access_token():
            return []

        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }

        # Zoho Books /chartofaccounts supports filter_by=AccountType.Expense
        # to return only expense-type accounts which are valid for expense creation
        url = (
            f"{self.api_base_url}/chartofaccounts"
            f"?organization_id={organization_id}"
            f"&filter_by=AccountType.Expense"
        )
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                accounts = response.json().get("chartofaccounts", [])
                logger.info(f"Fetched {len(accounts)} expense accounts from Zoho Books.")
                return accounts
            else:
                logger.error(f"Error fetching chart of accounts: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Exception fetching chart of accounts: {e}")
            return []

    def create_expense(
        self,
        organization_id: str,
        account_id: str,
        amount: float,
        date: str,
        vendor_name: str,
        description: str,
        paid_through_account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates an expense entry in Zoho Books."""
        payload = {
            "account_id": account_id,
            "amount": amount,
            "date": date,
            "description": f"{description} | Vendor: {vendor_name}".strip(" | "),
        }
        if paid_through_account_id:
            payload["paid_through_account_id"] = paid_through_account_id

        if self.is_mock:
            logger.info(f"[Mock Mode] Created expense entry with payload: {payload}")
            return {
                "success": True,
                "is_mock": True,
                "message": "Expense created successfully (Mock Mode).",
                "expense": {
                    "expense_id": "mock_exp_556677",
                    "organization_id": organization_id,
                    "account_id": account_id,
                    "amount": amount,
                    "date": date,
                    "vendor_name": vendor_name,
                    "description": payload["description"]
                }
            }

        if not self.access_token and not self.refresh_access_token():
            return {"success": False, "message": "Failed to authenticate with Zoho Books."}

        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        # Zoho Books expects JSONString under URL encoded form parameter 'JSONString'
        url = f"{self.api_base_url}/expenses?organization_id={organization_id}"
        
        try:
            data = {"JSONString": json.dumps(payload)}
            response = requests.post(url, headers=headers, data=data)
            response_json = response.json()
            if response.status_code in [200, 201] and response_json.get("code") == 0:
                logger.info("Expense successfully created in Zoho Books.")
                return {
                    "success": True,
                    "is_mock": False,
                    "message": "Expense created successfully in Zoho Books.",
                    "expense": response_json.get("expense", {})
                }
            else:
                logger.error(f"Zoho Books API error creating expense: {response_json}")
                return {
                    "success": False,
                    "message": response_json.get("message", "API Error"),
                    "details": response_json
                }
        except Exception as e:
            logger.error(f"Exception creating expense in Zoho Books: {e}")
            return {"success": False, "message": f"Connection/Request Exception: {str(e)}"}
