from langgraph.graph import StateGraph
from agents.tools import tool_search_emails, tool_read_emails, tool_summerize_emails
import os
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
load_dotenv()
# Initialize LLM
groq_api_key = os.getenv('GROQ_API_KEY')
llm = ChatGroq(
    api_key=groq_api_key,

    model_name='llama-3.3-70b-versatile' # Standard generic model
)

# ------------------------------------------
# State definition
# ------------------------------------------
class AgentState(BaseModel):
    query: str
    search_results: Optional[Dict[str, Any]] = None
    selected_email: Optional[Dict[str, Any]] = None
    summary: str = ""

# ------------------------------------------
# Node: Refine Query
# ------------------------------------------
def refine_query(state: AgentState):
    prompt_template = ChatPromptTemplate.from_template(
        "Refine the following user query into a concise search keyword string for email retrieval:\n\nUser Query: {query}"
    )
    chain = prompt_template | llm | StrOutputParser()
    refined = chain.invoke({"query": state.query})
    state.query = refined
    return state

# ------------------------------------------
# Node: Search
# ------------------------------------------
def search_node(state: AgentState):
    # Hardcoded user_id for dev
    res = tool_search_emails("dev_user", state.query)
    state.search_results = res
    return state

# ------------------------------------------
# Node: Pick Top Email
# ------------------------------------------
def pick_email(state: AgentState):
    # Check if we have results
    if not state.search_results or "ids" not in state.search_results:
        return state
    
    ids_list = state.search_results["ids"]
    if not ids_list or not ids_list[0]:
        return state

    email_id = ids_list[0][0] # Chroma returns list of lists of ids
    email_doc = tool_read_emails("dev_user", email_id)
    state.selected_email = email_doc
    return state

# ------------------------------------------
# Node: Summarize
# ------------------------------------------
def summarize_node(state: AgentState):
    if not state.selected_email:
        state.summary = "No relevant email found to summarize."
        return state

    summary = tool_summerize_emails(llm, state.selected_email)
    state.summary = summary
    return state

# ------------------------------------------
# Build Graph
# ------------------------------------------
def create_agent():
    graph = StateGraph(AgentState)

    graph.add_node("refine_query", refine_query)
    graph.add_node("search", search_node)
    graph.add_node("pick", pick_email)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("refine_query")

    graph.add_edge("refine_query", "search")
    graph.add_edge("search", "pick")
    graph.add_edge("pick", "summarize")

    return graph.compile()