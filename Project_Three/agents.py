import re
import threading
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from database import (
    get_albums_by_artist,
    get_tracks_by_artist,
    get_songs_by_genre,
    check_for_songs,
    get_invoices_by_customer_sorted_by_date,
    get_invoices_sorted_by_unit_price,
    get_employee_by_invoice_and_customer,
    execute_query
)

# In-memory store for long term preferences
LONG_TERM_MEMORY = {}

class State(TypedDict):
    customer_id: str
    messages: Annotated[list[AnyMessage], add_messages]
    loaded_memory: str
    next_agent: str
    visited: Annotated[list[str], lambda x, y: x + y]

import os

def get_llm():
    model_name = os.environ.get("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing. Please set os.environ['GROQ_API_KEY'] = 'gsk_...' before running agent queries.")
    return ChatGroq(model=model_name, api_key=api_key)

def get_fast_llm():
    # Use the ultra-fast 8B model for routing, verification, and memory extraction
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing. Please set os.environ['GROQ_API_KEY'] = 'gsk_...' before running agent queries.")
    return ChatGroq(model="llama-3.1-8b-instant", api_key=api_key)

from pydantic import BaseModel, Field, field_validator

class Credential(BaseModel):
    has_credential: bool = Field(description="Whether the user provided a customer ID, email, or phone number.")
    type: str = Field(default="", description="Type of credential: 'id', 'email', or 'phone'. Empty string if none.")
    value: str = Field(default="", description="The value of the credential. Empty string if none.")

    @field_validator("has_credential", mode="before")
    @classmethod
    def parse_bool(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

def verify_customer(credential_type: str, credential_value: str) -> str:
    """Returns CustomerId if found, else None"""
    try:
        credential_value = str(credential_value).strip()
        if credential_type == "id":
            query = "SELECT CustomerId FROM Customer WHERE CustomerId = ?"
            res = execute_query(query, (credential_value,))
            if res: return str(res[0]["CustomerId"])
        elif credential_type == "email":
            query = "SELECT CustomerId FROM Customer WHERE Email LIKE ?"
            res = execute_query(query, (f"%{credential_value}%",))
            if res: return str(res[0]["CustomerId"])
        elif credential_type == "phone":
            query = "SELECT CustomerId FROM Customer WHERE Phone LIKE ?"
            res = execute_query(query, (f"%{credential_value}%",))
            if res: return str(res[0]["CustomerId"])
    except Exception as e:
        print(f"Error in verify_customer: {e}")
    return None

def verify_info(state: State):
    customer_id = state.get("customer_id")
    if customer_id:
        return {"visited": []}
    
    user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_msg = msg.content
            break
            
    # Deterministic DB match (Instant & 100% reliable for Phone/Email/ID)
    try:
        customers = execute_query("SELECT CustomerId, Email, Phone FROM Customer")
        msg_clean = re.sub(r'[\s\(\)\-\+]', '', user_msg.lower())
        
        for c in customers:
            cid_str = str(c["CustomerId"])
            email = (c["Email"] or "").lower()
            phone = (c["Phone"] or "")
            phone_clean = re.sub(r'[\s\(\)\-\+]', '', phone.lower())
            
            if phone_clean and len(phone_clean) >= 7 and phone_clean in msg_clean:
                return {"customer_id": cid_str, "visited": []}
            if email and email in user_msg.lower():
                return {"customer_id": cid_str, "visited": []}
            
            id_match = re.search(r'\b(?:customer\s*id|id)\s*[:=]?\s*(\d+)\b', user_msg, re.IGNORECASE)
            if id_match and id_match.group(1) == cid_str:
                return {"customer_id": cid_str, "visited": []}
    except Exception as e:
        print(f"Deterministic verification note: {e}")

    # Fallback to LLM extraction if deterministic match wasn't found
    try:
        llm = get_fast_llm().with_structured_output(Credential)
        cred = llm.invoke(f"Extract customer credentials from this message. Look for an ID, email, or phone number. Message: {user_msg}")
        if cred and cred.has_credential:
            cid = verify_customer(cred.type, cred.value)
            if cid:
                return {"customer_id": cid, "visited": []}
    except Exception as e:
        print(f"Extraction error: {e}")
        
    return {"customer_id": None, "visited": []}

def route_after_verification(state: State):
    if state.get("customer_id"):
        return "load_memory"
    return "ask_human"

def ask_human(state: State):
    return {"messages": [AIMessage(content="I need to verify your account. Please provide your Customer ID, phone number, or email address to proceed.")]}

def load_memory(state: State):
    cid = state.get("customer_id")
    memory = LONG_TERM_MEMORY.get(cid, "No specific preferences found yet.")
    return {"loaded_memory": memory}

class RouterOutput(BaseModel):
    next_node: Literal["music_catalog", "invoice_info", "FINISH"] = Field(
        description="The next sub-agent to route to, or FINISH if the user's request has been fully answered."
    )

def supervisor(state: State):
    messages = state["messages"]
    visited = state.get("visited", [])
    
    user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break

    query_lower = user_query.lower()
    
    # Deterministic routing checks (Invoice first, then Music for multi-part queries)
    invoice_keywords = ["invoice", "purchase", "bought", "spent", "total", "cost", "price", "receipt", "order"]
    music_keywords = ["song", "music", "album", "artist", "track", "preference", "recommend", "stones", "genre", "catalog"]

    if any(k in query_lower for k in invoice_keywords) and "invoice_info" not in visited:
        return {"next_agent": "invoice_info"}

    if any(k in query_lower for k in music_keywords) and "music_catalog" not in visited:
        return {"next_agent": "music_catalog"}

    sys_msg = SystemMessage(content=f"""
You are the supervisor for Edges Music Store Customer Support.
User query: "{user_query}"
Sub-agents visited in this turn: {visited}

Decide the next step:
- "invoice_info": if user asks about purchases/invoices/total AND "invoice_info" is NOT in {visited}.
- "music_catalog": if user asks about music/albums/artists/songs/recommendations AND "music_catalog" is NOT in {visited}.
- "FINISH": if all parts of the user request have been answered by the visited sub-agents, or for general greetings.
""")
    llm = get_llm().with_structured_output(RouterOutput)
    try:
        res = llm.invoke([sys_msg])
        return {"next_agent": res.next_node}
    except Exception as e:
        return {"next_agent": "FINISH"}

def route_supervisor(state: State):
    nxt = state.get("next_agent", "FINISH")
    visited = state.get("visited", [])
    
    # Programmatic loop prevention:
    # If the supervisor tries to route back to an already visited sub-agent during this turn, force finish!
    if nxt in visited:
        return "create_memory"
        
    if nxt == "music_catalog":
        return "music_catalog"
    elif nxt == "invoice_info":
        return "invoice_info"
    else:
        return "create_memory"

def filter_messages(messages):
    return [m for m in messages if isinstance(m, (HumanMessage, AIMessage, ToolMessage, SystemMessage))]

def music_node(state: State):
    mem = state.get("loaded_memory", "")
    sys_prompt = f"You are the Music Catalog Sub-Agent for Edges Music Store.\nUser preferences loaded from long-term memory: {mem}.\nIMPORTANT: When the user asks for recommendations or songs matching their preferences, you MUST look up tracks for their preferred artists (e.g. Rolling Stones) or genres using your tools (get_tracks_by_artist or get_songs_by_genre) and list the song names in your response."
    tools = [get_albums_by_artist, get_tracks_by_artist, get_songs_by_genre, check_for_songs]
    
    msgs = filter_messages(state["messages"])
    try:
        agent = create_react_agent(get_llm(), tools, prompt=sys_prompt)
        res = agent.invoke({"messages": msgs})
        new_msgs = res["messages"][len(msgs):] 
        text_contents = [m.content for m in new_msgs if isinstance(m, AIMessage) and m.content]
        if text_contents:
            combined = "\n\n".join(text_contents)
            combined = re.sub(r'</?function[^>]*>', '', combined)
            combined = '\n'.join([line for line in combined.split('\n') if not line.strip().startswith('=function>') and not line.strip().startswith('</function>')])
            return {"messages": [AIMessage(content=combined.strip(), name="music_catalog")], "visited": ["music_catalog"]}
    except Exception as e:
        print(f"Music node tool handling note: {e}")
        # Direct tool query fallback if Groq API parser encounters syntax formatting glitch:
        query_text = mem if mem else "Rock"
        if "rolling stones" in query_text.lower():
            db_res = get_tracks_by_artist.invoke({"artist": "Rolling Stones"})
        else:
            db_res = get_songs_by_genre.invoke({"genre": "Rock"})
        
        prompt_fallback = SystemMessage(content=f"You are the Music Catalog Sub-Agent. Database results: {db_res}.\nPresent these recommended songs clearly to the user matching their preferences.")
        fallback_ans = get_llm().invoke([prompt_fallback] + msgs[-3:])
        return {"messages": [AIMessage(content=fallback_ans.content.strip(), name="music_catalog")], "visited": ["music_catalog"]}

    return {"messages": [], "visited": ["music_catalog"]}

def invoice_node(state: State):
    cid = state.get("customer_id")
    sys_prompt = f"You are the Invoice Sub-Agent for Edges Music Store. The current customer's ID is {cid}.\nIMPORTANT: Use your tools to retrieve invoice details for this customer ID."
    tools = [get_invoices_by_customer_sorted_by_date, get_invoices_sorted_by_unit_price, get_employee_by_invoice_and_customer]
    
    msgs = filter_messages(state["messages"])
    try:
        agent = create_react_agent(get_llm(), tools, prompt=sys_prompt)
        res = agent.invoke({"messages": msgs})
        new_msgs = res["messages"][len(msgs):] 
        text_contents = [m.content for m in new_msgs if isinstance(m, AIMessage) and m.content]
        if text_contents:
            combined = "\n\n".join(text_contents)
            combined = re.sub(r'</?function[^>]*>', '', combined)
            combined = '\n'.join([line for line in combined.split('\n') if not line.strip().startswith('=function>') and not line.strip().startswith('</function>')])
            return {"messages": [AIMessage(content=combined.strip(), name="invoice_info")], "visited": ["invoice_info"]}
    except Exception as e:
        print(f"Invoice node tool handling note: {e}")
        db_res = get_invoices_by_customer_sorted_by_date.invoke({"customer_id": str(cid)})
        prompt_fallback = SystemMessage(content=f"You are the Invoice Sub-Agent. Database invoice results for customer {cid}: {db_res}.\nSummarize the invoice information for the user.")
        fallback_ans = get_llm().invoke([prompt_fallback] + msgs[-3:])
        return {"messages": [AIMessage(content=fallback_ans.content.strip(), name="invoice_info")], "visited": ["invoice_info"]}

    return {"messages": [], "visited": ["invoice_info"]}

def create_memory(state: State):
    cid = state.get("customer_id")
    messages = state["messages"]
    
    # If the last message is a HumanMessage, it means no sub-agent responded to it (e.g. general chat, hi, hello)
    # We must generate and append a response from a general assistant.
    new_messages = []
    if messages and isinstance(messages[-1], HumanMessage):
        try:
            sys_msg = SystemMessage(content="You are a polite customer support assistant for Edges Music Store. Respond friendly and concisely to the user's greeting, gratitude, or general chat.")
            llm = get_fast_llm()
            res = llm.invoke([sys_msg] + messages[-5:])
            new_messages.append(res)
        except Exception as e:
            print(f"Error generating general response: {e}")
            new_messages.append(AIMessage(content="Hello! How can I help you today with our music catalog or your invoices?"))
    
    if not cid:
        return {"messages": new_messages} if new_messages else state
        
    messages_text = "\n".join([f"{type(m).__name__}: {m.content}" for m in messages[-5:] if isinstance(m, (HumanMessage, AIMessage))])
    
    try:
        llm = get_fast_llm()
        prompt = f"Extract any new music preferences (favorite artists, genres, etc.) from the conversation. Keep it concise. If none, reply 'None'.\n\n{messages_text}"
        pref = llm.invoke(prompt).content
        if "none" not in pref.lower() and len(pref) > 3:
            existing = LONG_TERM_MEMORY.get(cid, "")
            new_memory = f"{existing}\n{pref}".strip()
            LONG_TERM_MEMORY[cid] = new_memory
    except Exception as e:
        print(f"Error in memory extraction: {e}")

    return {"messages": new_messages} if new_messages else state

def build_graph():
    workflow = StateGraph(State)
    workflow.add_node("verify_info", verify_info)
    workflow.add_node("ask_human", ask_human)
    workflow.add_node("load_memory", load_memory)
    workflow.add_node("supervisor", supervisor)
    workflow.add_node("music_catalog", music_node)
    workflow.add_node("invoice_info", invoice_node)
    workflow.add_node("create_memory", create_memory)

    workflow.add_edge(START, "verify_info")
    workflow.add_conditional_edges("verify_info", route_after_verification, {"load_memory": "load_memory", "ask_human": "ask_human"})
    workflow.add_edge("ask_human", END)
    workflow.add_edge("load_memory", "supervisor")
    workflow.add_conditional_edges("supervisor", route_supervisor, {"music_catalog": "music_catalog", "invoice_info": "invoice_info", "create_memory": "create_memory"})
    workflow.add_edge("music_catalog", "supervisor")
    workflow.add_edge("invoice_info", "supervisor")
    workflow.add_edge("create_memory", END)

    return workflow
