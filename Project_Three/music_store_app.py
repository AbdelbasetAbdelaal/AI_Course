import streamlit as st
import os
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from agents import build_graph, verify_customer

st.set_page_config(page_title="Music Store Customer Support", page_icon="🎵", layout="wide")

st.title("🎵 Edges Music Store")
st.markdown("### Welcome to your customer support experience.")

# Sidebar setup
with st.sidebar:
    st.markdown("### 🔑 API Key Handling")
    provider = st.selectbox("LLM Provider", ["Groq"])
    groq_api_key = st.text_input("Enter Groq API Key", type="password")
    
    if groq_api_key:
        os.environ["GROQ_API_KEY"] = groq_api_key
        
    models_list = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    if groq_api_key:
        try:
            import requests
            resp = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {groq_api_key}"})
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                fetched_models = [m["id"] for m in data if "tool" not in m["id"].lower()] # Filter out preview tool models to avoid UI clutter
                if fetched_models:
                    models_list = sorted(fetched_models)
        except Exception:
            pass
            
    model_name = st.selectbox("Model Name", models_list, help="Select a currently supported Groq model")
    
    if model_name:
        os.environ["GROQ_MODEL_NAME"] = model_name
        
    st.divider()
    
    st.markdown("### 🆔 Session Management")
    session_id = st.text_input("Session ID", value="default-rag-session")
    
    st.divider()
    
    st.markdown("### 🔐 Store Authentication")
    credential_input = st.text_input("Customer Email / Phone / ID", placeholder="e.g. +55 (12) 3923-5555")
    login_btn = st.button("Login Securely")
    
    st.divider()
    
    st.markdown("### 📊 System Status")
    try:
        from database import execute_query
        cust_count = execute_query("SELECT COUNT(*) as cnt FROM Customer")
        st.success(f"Database Online: {cust_count[0]['cnt']} Customers loaded.")
    except Exception as e:
        st.error(f"Database Error: {e}")

# Initialize graph and checkpointer in session state
if "checkpointer" not in st.session_state:
    st.session_state.checkpointer = MemorySaver()
# Always recompile the graph on rerun to ensure updates to agents.py are loaded instantly
st.session_state.graph = build_graph().compile(checkpointer=st.session_state.checkpointer)

config = {"configurable": {"thread_id": session_id}}

# Handle Login
if login_btn:
    if not credential_input:
        st.sidebar.error("Please enter a credential.")
    else:
        # Verify credential
        cid = verify_customer("email", credential_input) or \
              verify_customer("phone", credential_input) or \
              verify_customer("id", credential_input)
        
        if cid:
            st.sidebar.success(f"Authenticated as Customer ID: {cid}")
            # Inject into graph state directly
            st.session_state.graph.update_state(config, {"customer_id": cid})
        else:
            st.sidebar.error("Customer not found. Please try again.")

# Check current auth status from graph state
current_state = st.session_state.graph.get_state(config)
is_authenticated = False
if current_state and current_state.values.get("customer_id"):
    is_authenticated = True
    st.sidebar.success(f"Logged in as Customer ID: {current_state.values.get('customer_id')}")

if not is_authenticated:
    st.info("👋 Please enter your API key and login via the sidebar to start chatting.")
else:
    # Load state for the current session ID
    if current_state and current_state.values.get("messages"):
        st.session_state.chat_history = current_state.values["messages"]
    else:
        st.session_state.chat_history = []

    # Display chat messages from history
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage) and message.content:
            if "I need to verify your account" not in message.content: # Hide old fallback message if state exists
                with st.chat_message("assistant"):
                    st.markdown(message.content)

    # Accept user input
    if prompt := st.chat_input("Ask about your invoices, music recommendations, etc..."):
        if not groq_api_key:
            st.error("Please enter your Groq API Key in the sidebar.")
        else:
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.spinner("Analyzing request..."):
                inputs = {"messages": [HumanMessage(content=prompt)]}
                try:
                    # Stream the graph to completion
                    for event in st.session_state.graph.stream(inputs, config, stream_mode="values"):
                        pass
                        
                    # Retrieve the updated state and display the new assistant messages immediately
                    current_state = st.session_state.graph.get_state(config)
                    if current_state and current_state.values.get("messages"):
                        old_len = len(st.session_state.chat_history)
                        new_messages = current_state.values["messages"]
                        st.session_state.chat_history = new_messages
                        
                        for msg in new_messages[old_len:]:
                            if isinstance(msg, AIMessage) and msg.content:
                                if "I need to verify your account" not in msg.content:
                                    with st.chat_message("assistant"):
                                        st.markdown(msg.content)
                except Exception as e:
                    st.error(f"An error occurred: {e}")
