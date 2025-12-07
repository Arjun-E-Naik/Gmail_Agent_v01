import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Gmail AI Agent", layout="wide")

st.title("🤖 Gmail AI Agent")

# Sidebar for controls
with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Sync Recent Emails"):
        with st.spinner("Syncing..."):
            try:
                res = requests.post(f"{API_URL}/sync", json={"user_id": "dev_user", "max_emails": 100})
                if res.status_code == 200:
                    st.success("Sync started! Wait a moment for indexing.")
                else:
                    st.error("Sync failed.")
            except Exception as e:
                st.error(f"Connection error: {e}")

# Main Chat Interface
query = st.text_input("Ask about your emails:", placeholder="What was the last invoice I received?")

if st.button("Search & Analyze") and query:
    with st.spinner("Thinking..."):
        try:
            payload = {"query": query}
            response = requests.post(f"{API_URL}/search", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if "error" in data:
                    st.error(f"Backend Error: {data['error']}")
                else:
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.subheader("🔍 Logic")
                        st.info(f"**Refined Query:** {data.get('refined_query')}")
                        st.write(f"**Found Email ID:** {data.get('selected_email_id')}")
                        st.write(f"**Subject:** {data.get('selected_email_subject')}")

                    with col2:
                        st.subheader("📝 AI Summary")
                        st.markdown(data.get("summary"))
                        
            else:
                st.error(f"API Error: {response.status_code}")
                
        except Exception as e:
            st.error(f"Could not connect to backend: {e}")