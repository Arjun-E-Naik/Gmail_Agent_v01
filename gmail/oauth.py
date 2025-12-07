import json
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from db.firestore_client import save_token_for_user, load_token_for_user
from app.config import SCOPES, GOOGLE_GMAIL_CREDENTIALS_PATH

def gmail_authenticate(user_id: str):
    creds = None
    token_json = load_token_for_user(user_id)
    
    if token_json:
        creds = Credentials.from_authorized_user_info(token_json, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GOOGLE_GMAIL_CREDENTIALS_PATH):
                raise FileNotFoundError(f"Credentials file not found at: {GOOGLE_GMAIL_CREDENTIALS_PATH}")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_GMAIL_CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        save_token_for_user(user_id, json.loads(creds.to_json()))

    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=creds)