import base64
from typing import List, Dict
from googleapiclient.errors import HttpError

def list_messages(service, query: str = "", max_results: int = 100) -> List[Dict]:
    """
    Fetches a list of message IDs.
    """
    messages = []
    try:
        # Corrected usage: service.users().messages().list(...)
        request = service.users().messages().list(userId='me', q=query, maxResults=min(max_results, 500))
        
        while request is not None and len(messages) < max_results:
            response = request.execute()
            messages.extend(response.get('messages', []))
            
            if len(messages) >= max_results:
                break
                
            request = service.users().messages().list_next(previous_request=request, previous_response=response)
            
        return messages[:max_results]
    
    except HttpError as err:
        print(f"Gmail API Error in list_messages: {err}")
        return []

def get_message(service, msg_id: str) -> Dict:
    """
    Fetches a single message's full details.
    """
    try:
        # ✅ FIX IS HERE: Added .users() before .messages()
        message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        
        # Extract headers
        header_map = {h["name"].lower(): h["value"] for h in headers}
        
        # Extract body
        body = ""
        if "data" in payload.get("body", {}):
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors='ignore')
        else:
            parts = payload.get("parts", [])
            for part in parts:
                if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                    data = part["body"]["data"]
                    body = base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="ignore")
                    break
        
        return {
            "email_id": message["id"],
            "thread_id": message.get("threadId"),
            "snippet": message.get("snippet"),
            "subject": header_map.get("subject", "No Subject"),
            "from": header_map.get("from", "Unknown"),
            "to": header_map.get("to", ""),
            "date": header_map.get("date", ""),
            "body": body,
        }
    except HttpError as e:
        print(f"Error fetching message {msg_id}: {e}")
        return {}