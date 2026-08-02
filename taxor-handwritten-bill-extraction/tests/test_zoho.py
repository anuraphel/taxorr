import pytest
import os
from zoho.zoho_client import ZohoBooksClient

def test_zoho_mock_mode_detection():
    # Force mock mode by clearing env vars (or leaving them as placeholder)
    os.environ["ZOHO_CLIENT_ID"] = "your_client_id"
    os.environ["ZOHO_CLIENT_SECRET"] = "your_client_secret"
    os.environ["ZOHO_REFRESH_TOKEN"] = "your_refresh_token"
    
    client = ZohoBooksClient()
    assert client.is_mock is True

def test_zoho_mock_methods():
    client = ZohoBooksClient()
    # Confirm refresh token works in mock
    assert client.refresh_access_token() is True
    assert client.access_token == "mock_access_token_xyz123"
    
    # Confirm fetching mock orgs & accounts
    orgs = client.get_organizations()
    assert len(orgs) > 0
    assert orgs[0]["organization_id"] == "mock_org_9988"
    
    accounts = client.get_expense_accounts("mock_org_9988")
    assert len(accounts) > 0
    assert accounts[0]["account_id"] == "mock_acc_101"

def test_zoho_mock_expense_creation():
    client = ZohoBooksClient()
    resp = client.create_expense(
        organization_id="mock_org_9988",
        account_id="mock_acc_101",
        amount=500.0,
        date="2026-07-20",
        vendor_name="Sharma Kirana Store",
        description="Office catering expense"
    )
    
    assert resp["success"] is True
    assert resp["is_mock"] is True
    assert resp["expense"]["amount"] == 500.0
    assert resp["expense"]["expense_id"] == "mock_exp_556677"
