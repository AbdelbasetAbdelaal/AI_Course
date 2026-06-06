# Import necessary libraries for UI, security, environment, and data handling
import streamlit as st
import hashlib
import os
from PIL import Image
import pandas as pd
from database import SchoolDatabase, DatabaseError
from chatbot import Chatbot

# Configure the main Streamlit page settings
st.set_page_config(page_title="Elhawey School Portal", layout="wide", page_icon="🏫")

# --- Proxy Configuration (Useful for corporate environments or restricted networks) ---
# Set these to your proxy address. 
# Format: "http://user:password@host:port" or just "http://host:port"
USE_PROXY = False  # Set to True to enable
PROXY_URL = "http://your-proxy-address:8080"
if USE_PROXY:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

# Configuration: Safely retrieve MySQL credentials from Streamlit's secrets management
db_config = st.secrets.get("mysql")
if not db_config:
    st.error("MySQL database configuration not found in Streamlit secrets. Please ensure it's configured under the [mysql] section.")
    st.stop() # Halt execution if database config is missing


# Helper function to hash passwords using SHA-256 for security
def get_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

# Load admin password from secrets or default to 'admin' (hashed)
ADMIN_PASSWORD_HASH = st.secrets.get("ADMIN_PASSWORD_HASH", get_hash("admin"))

st.title("🏫 Elhawey School Portal")

# Initialize the Database connection
db = SchoolDatabase(db_config)
try:
    db.setup_database() # Create tables if they don't exist
except DatabaseError as e:
    st.error(f"Database Initialization Error: {e}")

# Initialize the AI Chatbot with the Gemini API Key
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.sidebar.warning("⚠️ Google API Key not found. AI-powered fallback responses will be disabled.")
bot = Chatbot(db, api_key=api_key) # Pass the retrieved API key to the Chatbot

# Session State Init
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False
if "logged_in_username" not in st.session_state:
    st.session_state.logged_in_username = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# Function to reset the chatbot conversation state
def create_new_chat():
    st.session_state.messages = []
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1

# --- Sidebar Navigation ---
st.sidebar.title("Settings")
if st.session_state.admin_authenticated or st.session_state.user_authenticated:
    display_name = st.session_state.logged_in_username or 'Admin'
    st.sidebar.success(f"Logged in as: {display_name}")

    # Admin-specific navigation
    if st.session_state.admin_authenticated:
        if st.sidebar.button("📊 Admin Dashboard"):
            st.session_state.current_page = "admin_dashboard"
        if st.sidebar.button("💬 Chatbot"):
            st.session_state.current_page = "chatbot"
            
    # Home Link
    if st.sidebar.button("🏠 Home"):
        st.session_state.current_page = "home"

    # Shared Logout logic
    if st.sidebar.button("Logout"):
        st.session_state.admin_authenticated = False
        st.session_state.user_authenticated = False
        st.session_state.logged_in_username = None
        st.session_state.current_page = "home"
        st.rerun()
else:
    # Show login options if not authenticated
    if st.sidebar.button("User Login/Register"):
        st.session_state.current_page = "user_login_register"
    if st.sidebar.button("Admin Login"):
        st.session_state.current_page = "admin_login"

st.sidebar.markdown("---")

# --- PAGE ROUTING LOGIC ---
if st.session_state.current_page == "home":
    st.subheader("Welcome to Elhawey School Portal")
    st.write("Select an option below to get started.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("User Access", use_container_width=True):
            st.session_state.current_page = "user_login_register"
            st.rerun()
    with col2:
        if st.button("Administrator Access", use_container_width=True):
            st.session_state.current_page = "admin_login"
            st.rerun()

elif st.session_state.current_page == "user_login_register":
    st.subheader("User Portal")
    tab1, tab2 = st.tabs(["Login", "Registration"])
    
    with tab1:
        with st.form("user_login_form"):
            st.markdown("#### Login")
            u, p = st.text_input("Username"), st.text_input("Password", type="password") # Hide password typing
            if st.form_submit_button("Login"):
                try:
                    user = db.get_user_by_username(u)
                    # Verify password hash against database
                    if user and get_hash(p) == user['password_hash']:
                        st.session_state.user_authenticated, st.session_state.logged_in_username = True, u
                        st.session_state.current_page = "chatbot" # Redirect to chat
                        st.rerun()
                    else: st.error("Invalid credentials.")
                except DatabaseError as e:
                    st.error(f"Login error: {e}")

    with tab2:
        with st.form("user_registration_form"):
            st.markdown("#### Register")
            ru, rp, rcp = st.text_input("New Username"), st.text_input("New Password", type="password"), st.text_input("Confirm Password", type="password")
            re = st.text_input("Email")
            if st.form_submit_button("Register"):
                # Validate input and add user to database
                try:
                    if ru and rp == rcp and not db.get_user_by_username(ru):
                        if db.add_user(ru, get_hash(rp), re):
                            st.success("Registered successfully! You can now log in.")
                    else: st.error("Passwords mismatch or username already exists.")
                except DatabaseError as e:
                    st.error(f"Registration error: {e}")

elif st.session_state.current_page == "admin_login":
    st.subheader("Administrator Login")
    ap = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if get_hash(ap) == ADMIN_PASSWORD_HASH:
            st.session_state.admin_authenticated, st.session_state.current_page = True, "admin_dashboard"
            st.rerun()
        else:
            st.error("Incorrect administrator password.")

# --- Admin Dashboard ---
if st.session_state.admin_authenticated and st.session_state.current_page == "admin_dashboard":
    st.sidebar.subheader("Admin Actions")
    if st.sidebar.button("🎓 Fetch Students"):
        try:
            st.session_state.db_results, st.session_state.db_view = db.fetch_students(), "students"
        except DatabaseError as e: st.error(e)
    if st.sidebar.button("👨‍🏫 Fetch Teachers"):
        try:
            st.session_state.db_results, st.session_state.db_view = db.fetch_teachers(), "teachers"
        except DatabaseError as e: st.error(e)

    st.sidebar.markdown("---")
    with st.sidebar.expander("➕ Add Record"):
        mode = st.radio("Type", ["Student", "Teacher"])
        with st.form("add_form", clear_on_submit=True):
            fn, ln, email = st.text_input("First Name"), st.text_input("Last Name"), st.text_input("Email")
            extra = st.number_input("Grade", 1, 12) if mode == "Student" else st.text_input("Subject")
            if st.form_submit_button("Save"):
                try:
                    success = db.add_student(fn, ln, extra, email) if mode == "Student" else db.add_teacher(fn, ln, extra, email)
                    if success: 
                        st.sidebar.success("Record Added Successfully!")
                        # Refresh view if current results match the added type
                        if "db_view" in st.session_state and st.session_state.db_view.lower().startswith(mode.lower()):
                            st.session_state.db_results = db.fetch_students() if mode == "Student" else db.fetch_teachers()
                except DatabaseError as e:
                    st.sidebar.error(e)

    st.subheader("Admin Dashboard")
    
    # --- Statistics Section ---
    with st.expander("📊 School Analytics", expanded=False):
        try:
            stats = db.get_grade_distribution()
            if stats:
                df_stats = pd.DataFrame(stats)
                col1, col2 = st.columns([1, 2])
                col1.metric("Total Students", df_stats['count'].sum())
                col2.bar_chart(df_stats.set_index('grade_level'))
            else:
                st.info("No student data available for analytics.")
        except DatabaseError as e:
            st.error(f"Could not load analytics: {e}")

    # --- Data Editor Section (CRUD Operations) ---
    if "db_results" in st.session_state:
        edited = st.data_editor(st.session_state.db_results, key="editor", use_container_width=True, num_rows="dynamic", disabled=["student_id", "teacher_id"])
        
        c1, c2 = st.columns(2)
        if c1.button("💾 Sync Database", type="primary"):
            try:
                state, view = st.session_state["editor"], st.session_state["db_view"]
                results = st.session_state.db_results
                
                # Process edits
                for idx, changes in state["edited_rows"].items():
                    row = {**results[idx], **changes}
                    if view == "students": 
                        db.update_student(row['student_id'], row['first_name'], row['last_name'], row['grade_level'], row['email'])
                    else: 
                        db.update_teacher(row['teacher_id'], row['first_name'], row['last_name'], row['subject'], row['email'])
                        
                # Process additions
                for r in state["added_rows"]:
                    if view == "students": 
                        db.add_student(r.get('first_name',''), r.get('last_name',''), r.get('grade_level',1), r.get('email',''))
                    else: 
                        db.add_teacher(r.get('first_name',''), r.get('last_name',''), r.get('subject',''), r.get('email',''))
                        
                # Process deletions
                for idx in state["deleted_rows"]:
                    rid = results[idx]['student_id' if view == "students" else 'teacher_id']
                    if view == "students": 
                        db.delete_student(rid)
                    else: 
                        db.delete_teacher(rid)
                
                st.session_state.db_results = db.fetch_students() if view == "students" else db.fetch_teachers()
                st.success("Changes synced with the database.")
                st.rerun()
            except DatabaseError as e:
                st.error(f"Sync failed: {e}")
        if c2.button("🗑️ Clear View"):
            del st.session_state.db_results
            st.rerun()

# --- Chatbot Page ---
if st.session_state.current_page == "chatbot":
    with st.sidebar:
        st.subheader("Chat Configuration")
        delay = st.slider("Response Speed", 0.0, 3.0, 0.5)
        # Allow users to upload images/text for the bot to analyze
        files = st.file_uploader("Attach files to your query", accept_multiple_files=True, key=st.session_state.get("uploader_key", 0))
        if st.button("🗑️ Clear Chat History", use_container_width=True): create_new_chat()

    summaries = bot.process_uploads(files) if files else []
    name = st.session_state.logged_in_username if st.session_state.user_authenticated else "Admin"
    bot.render_chat_interface(name, delay, summaries) # Display the chat UI

    if "messages" in st.session_state and st.session_state.messages:
        chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        st.sidebar.download_button("Download Chat", chat_text, file_name="chat.txt")