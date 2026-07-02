import os
import streamlit as st
import yaml
from engines.base import Chatbot
from engines.simple_faq import SimpleFAQEngine
from engines.rag_engine import RagEngine
from rag.ingest import DocumentIngester
from rag.pipeline import create_conversational_rag_chain

# --- Page Config & Styling ---
st.set_page_config(
    page_title="Conversational PDF RAG Assistant",
    page_icon="🤖",
    layout="wide"
)

# Inject custom premium CSS styling for a clean, glassmorphic layout
st.markdown("""
<style>
    /* Google Fonts import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Title Gradient styling */
    .title-text {
        background: linear-gradient(135deg, #a78bfa 0%, #6366f1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.8rem;
        margin-bottom: 0.2rem;
    }
    
    /* Header subtitle styling */
    .subtitle-text {
        font-size: 1.1rem;
        color: #9ca3af;
        margin-bottom: 2rem;
    }
    
    /* Card design for source documents */
    .source-card {
        background-color: #1f2937;
        border-left: 4px solid #6366f1;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .source-meta {
        font-size: 0.85rem;
        color: #a78bfa;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    
    .source-content {
        font-size: 0.9rem;
        color: #e5e7eb;
        line-height: 1.4;
    }
    
    /* Styled labels */
    .highlight-label {
        font-weight: 600;
        color: #f3f4f6;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def load_config() -> dict:
    """
    Loads application configuration parameters from config.yaml.
    Resolves the config path relative to this script directory to support 
    any launch working directory.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

# --- State Management & Setup ---
config = load_config()
persist_dir = config["vector_store"]["persist_directory"]

# 1. Initialize document ingester in session state
if "ingester" not in st.session_state:
    st.session_state.ingester = DocumentIngester()

# 2. Try to automatically load existing vector store on startup
if "vector_store" not in st.session_state:
    # Resolve the absolute persistence directory to check if collection files exist
    if not os.path.isabs(persist_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        resolved_persist = os.path.abspath(os.path.join(script_dir, persist_dir))
    else:
        resolved_persist = persist_dir
        
    if os.path.exists(resolved_persist) and len(os.listdir(resolved_persist)) > 0:
        try:
            st.session_state.vector_store = st.session_state.ingester.get_vector_store()
        except Exception:
            st.session_state.vector_store = None
    else:
        st.session_state.vector_store = None

# --- Sidebar Configuration Panel ---
with st.sidebar:
    st.markdown('<div style="text-align: center; padding: 1rem 0;">'
                '<span style="font-size: 3rem;">📚</span>'
                '<h2 style="margin: 0; font-weight: 700; color: #f3f4f6;">RAG Controller</h2>'
                '</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # 1. API Configuration Widgets
    st.subheader("🔑 API Key Handling")
    provider = st.selectbox("LLM Provider", ["Groq", "Gemini", "OpenAI"], index=0)
    
    # Dynamic placeholder mapping
    key_placeholder = f"Enter {provider} API Key"
    api_key = st.text_input(key_placeholder, type="password", key=f"{provider.lower()}_api_key_input")
    
    # Custom model selection override input (loaded from config default values)
    default_model = config["llm"][provider.lower()]["model_name"]
    model_name = st.text_input("Model Name", value=default_model, help="Adjust if your API key requires a specific model version.")

    st.markdown("---")
    
    # 2. Session Context Config
    st.subheader("🆔 Session Management")
    session_id = st.text_input("Session ID", value="default-rag-session")
    
    st.markdown("---")
    
    # 3. Strategy Pattern Selector (Swaps engines at runtime)
    st.subheader("⚙️ Chat Engine Strategy")
    engine_type = st.radio(
        "Choose Chat Engine:",
        ["RAG Engine", "Simple FAQ Engine"],
        help="RAG Engine searches uploaded PDFs; Simple FAQ Engine answers standard pre-defined FAQs."
    )
    
    st.markdown("---")
    
    # 4. PDF Document Uploader
    st.subheader("📁 Upload PDFs")
    uploaded_files = st.file_uploader(
        "Upload one or more PDFs", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    col1, col2 = st.columns(2)
    # PDF Ingestion processing trigger button
    with col1:
        if st.button("🚀 Ingest PDFs", use_container_width=True):
            if not uploaded_files:
                st.warning("Please select at least one PDF file.")
            else:
                with st.spinner("Parsing and embedding documents..."):
                    try:
                        # Ingest documents, update state, and trigger reload
                        vector_store = st.session_state.ingester.ingest_uploaded_files(uploaded_files)
                        st.session_state.vector_store = vector_store
                        # Force RAG engine to rebuild next turn
                        if "rag_engine" in st.session_state:
                            del st.session_state.rag_engine
                        st.success(f"Successfully ingested {len(uploaded_files)} PDF(s)!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ingestion failed: {e}")
                        
    # Vector store database reset button
    with col2:
        if st.button("🗑️ Clear DB", use_container_width=True):
            st.session_state.ingester.clear_vector_store()
            st.session_state.vector_store = None
            if "rag_engine" in st.session_state:
                del st.session_state.rag_engine
            st.success("Vector store cleared!")
            st.rerun()

# --- Main Dashboard ---
st.markdown('<h1 class="title-text">Conversational RAG Assistant</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Ask questions about your uploaded documents with persistent context-aware chat history.</p>', unsafe_allow_html=True)

# Build and configure the chatbot client based on Strategy selection
chatbot = None
error_msg = None

# A. Wire legacy FAQ engine
if engine_type == "Simple FAQ Engine":
    if "simple_engine" not in st.session_state:
        st.session_state.simple_engine = SimpleFAQEngine()
    # Inject FAQ engine into chatbot façade
    chatbot = Chatbot(st.session_state.simple_engine)
    
# B. Wire RAG search engine
elif engine_type == "RAG Engine":
    if not api_key:
        error_msg = "Please provide an API Key in the sidebar to run the RAG Engine."
    elif st.session_state.vector_store is None:
        error_msg = "No documents found. Please upload and ingest PDFs in the sidebar."
    else:
        # Construct RAG chain if parameters have changed or engine is uninitialized
        if ("rag_engine" not in st.session_state or 
            st.session_state.get("active_provider") != provider or 
            st.session_state.get("active_model") != model_name or
            st.session_state.get("active_key") != api_key):
            
            with st.spinner("Initializing RAG orchestration pipeline..."):
                try:
                    rag_chain, history_store = create_conversational_rag_chain(
                        vector_store=st.session_state.vector_store,
                        provider=provider,
                        api_key=api_key,
                        model_name=model_name
                    )
                    st.session_state.rag_engine = RagEngine(rag_chain, history_store)
                    st.session_state.active_provider = provider
                    st.session_state.active_model = model_name
                    st.session_state.active_key = api_key
                except Exception as e:
                    error_msg = f"Failed to initialize RAG pipeline: {e}"
        
        # Inject RAG engine into chatbot façade
        if "rag_engine" in st.session_state:
            chatbot = Chatbot(st.session_state.rag_engine)

# Status Information Bar
status_col1, status_col2 = st.columns([3, 1])
with status_col1:
    st.markdown(f"**Active Session:** `{session_id}` | **Engine Strategy:** `{engine_type}`")
with status_col2:
    if st.session_state.vector_store is not None:
        st.markdown('<span style="color: #10b981; font-weight: 600;">● Vector Store Indexed</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color: #f59e0b; font-weight: 600;">○ Vector Store Empty</span>', unsafe_allow_html=True)

st.markdown("---")

# Render conversational interface or display active validation messages
if error_msg:
    st.info(error_msg)
else:
    # 1. Fetch and render conversation history from the active engine
    chat_history = chatbot.history(session_id)
    for role, message in chat_history:
        with st.chat_message(role):
            st.markdown(message)
            
    # 2. Render input block for new user queries
    if prompt := st.chat_input("Ask a question about the uploaded PDFs..."):
        # Draw user prompt immediately on screen
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Draw assistant answer and fetch results
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Request answer through Strategy pattern façade
                    answer = chatbot.ask(session_id, prompt)
                    st.markdown(answer)
                    
                    # If RAG engine is active, render citations/source details
                    if engine_type == "RAG Engine":
                        sources = st.session_state.rag_engine.get_last_sources(session_id)
                        if sources:
                            with st.expander("🔍 View Retrieved Sources"):
                                for i, src in enumerate(sources):
                                    st.markdown(f"""
                                    <div class="source-card">
                                        <div class="source-meta">Source {i+1}: {src['source']} (Page {src['page']})</div>
                                        <div class="source-content">"{src['content'][:400]}..."</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                    # Trigger reload on success so messages settle nicely in the transcript
                    st.rerun()
                except Exception as e:
                    # Display error on screen (Rerun is skipped so error remains visible)
                    st.error(f"Error generating answer: {e}")
