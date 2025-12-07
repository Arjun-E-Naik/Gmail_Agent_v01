from models.embeddings import embed_text
from models.vectorstore import search
from gmail.gmail_api import get_message
from gmail.oauth import gmail_authenticate
from app.config import VECTOR_COLLECTION_NAME

def tool_search_emails(user_id: str, query: str):
    """
    Convert query -> embedding -> vector search.
    """
    embedding = embed_text(query)
    # Search expects list of lists [[0.1, ...]]
    results = search(
        collection_name=VECTOR_COLLECTION_NAME, 
        query_embeddings=[embedding], 
        n_results=5 
    )
    return results

def tool_read_emails(user_id: str, email_id: str):
    """
    Fetch full email content.
    """
    service = gmail_authenticate(user_id=user_id)
    return get_message(service, email_id)  

def tool_summerize_emails(llm, email_doc: dict):
    """
    Summarize using LangChain LLM object.
    """      
    text = f"""
     Summarize the following email into key points and action items:
    
    Subject: {email_doc.get("subject")}
    From: {email_doc.get("from")}
    Body: {email_doc.get("body")}
    """
    
    # LangChain usage: .invoke() or .predict()
    response = llm.invoke(text)
    
    # Handle response types (AIMessage or string)
    if hasattr(response, 'content'):
        return response.content
    return str(response)