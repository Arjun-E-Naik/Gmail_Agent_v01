from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from agents.graph import create_agent, AgentState
from gmail.sync import sync_new_emails

app = FastAPI()
agent = create_agent()

class QueryRequest(BaseModel):
    query: str

class SyncRequest(BaseModel):
    user_id: str = "dev_user"
    max_emails: int = 10

@app.post("/sync")
def sync_endpoint(req: SyncRequest, background_tasks: BackgroundTasks):
    """
    Trigger email sync in background.
    """
    background_tasks.add_task(sync_new_emails, req.user_id, "", req.max_emails)
    return {"status": "Sync started in background", "user": req.user_id}

@app.post("/search")
def search_api(request: QueryRequest):
    print("Received Query:", request.query)
    try:
        # Initialize state with the raw user query
        initial_state = AgentState(query=request.query)
        
        # Invoke graph
        final_state = agent.invoke(initial_state)

        # Check if final_state is a dict (LangGraph behavior) or Pydantic object
        # LangGraph typically returns a dict matching the State schema
        if isinstance(final_state, dict):
            refined_q = final_state.get("query")
            summary = final_state.get("summary")
            email_data = final_state.get("selected_email")
        else:
            refined_q = final_state.query
            summary = final_state.summary
            email_data = final_state.selected_email

        return {
            "refined_query": refined_q,
            "summary": summary,
            "selected_email_subject": email_data.get("subject") if email_data else None,
            "selected_email_id": email_data.get("email_id") if email_data else None,
        }
    except Exception as e:
        print("❌ BACKEND ERROR:", e)
        return {"error": str(e)}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)