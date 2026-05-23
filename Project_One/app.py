import streamlit as st
import hashlib
from PIL import Image
from database import SchoolDatabase, DatabaseError
from chatbot import Chatbot

# Configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'school_db'
}
ADMIN_PASSWORD_HASH = hashlib.sha256("admin".encode()).hexdigest()

st.set_page_config(page_title="Elhawey School Portal", layout="wide", page_icon="🏫")

st.title("🏫 Elhawey Chatbot")

# Initialize Classes
db = SchoolDatabase(DB_CONFIG)
try:
    db.setup_database()
except DatabaseError as e:
    st.error(f"Database Initialization Error: {e}")

bot = Chatbot(db)

# Session State Init
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False
if "logged_in_username" not in st.session_state:
    st.session_state.logged_in_username = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

def create_new_chat():
    st.session_state.messages = []
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
    st.rerun()

# --- Sidebar Navigation ---
st.sidebar.title("Settings")
if st.session_state.admin_authenticated or st.session_state.user_authenticated:
    st.sidebar.success(f"Logged in as: {st.session_state.logged_in_username or 'Admin'}")
    
    # Admin-specific navigation
    if st.session_state.admin_authenticated:
        if st.sidebar.button("📊 Admin Dashboard"):
            st.session_state.current_page = "admin_dashboard"
        if st.sidebar.button("💬 Chatbot"):
            st.session_state.current_page = "chatbot"
            
    if st.sidebar.button("Logout"):
        st.session_state.admin_authenticated = False
        st.session_state.user_authenticated = False
        st.session_state.logged_in_username = None
        st.session_state.current_page = "home"
        st.rerun()
else:
    if st.sidebar.button("User Login/Register"):
        st.session_state.current_page = "user_login_register"
    if st.sidebar.button("Admin Login"):
        st.session_state.current_page = "admin_login"

st.sidebar.markdown("---")

# --- Pages ---
if st.session_state.current_page == "home":
    st.write("Please select a role from the sidebar to proceed.")

elif st.session_state.current_page == "user_login_register":
    st.sidebar.subheader("User Login / Registration")
    with st.sidebar.form("user_login_form"):
        st.markdown("#### Login")
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                user = db.get_user_by_username(u)
                if user and hashlib.sha256(p.encode()).hexdigest() == user['password_hash']:
                    st.session_state.user_authenticated, st.session_state.logged_in_username = True, u
                    st.session_state.current_page = "chatbot"
                    st.rerun()
                else: st.sidebar.error("Invalid credentials.")
            except DatabaseError as e:
                st.error(e)

    with st.sidebar.form("user_registration_form"):
        st.markdown("#### Register")
        ru, rp, rcp = st.text_input("New Username"), st.text_input("New Password", type="password"), st.text_input("Confirm", type="password")
        re = st.text_input("Email")
        if st.form_submit_button("Register"):
            try:
                if ru and rp == rcp and not db.get_user_by_username(ru):
                    if db.add_user(ru, hashlib.sha256(rp.encode()).hexdigest(), re):
                        st.sidebar.success("Registered! Please log in.")
                else: st.sidebar.error("Check inputs or username exists.")
            except DatabaseError as e:
                st.error(e)

elif st.session_state.current_page == "admin_login":
    st.sidebar.subheader("Admin Login")
    ap = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if hashlib.sha256(ap.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            st.session_state.admin_authenticated, st.session_state.current_page = True, "admin_dashboard"
            st.rerun()

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
                    if success: st.sidebar.success("Saved!")
                except DatabaseError as e:
                    st.sidebar.error(e)

    st.subheader("Admin Dashboard")
    if "db_results" in st.session_state:
        edited = st.data_editor(st.session_state.db_results, key="editor", use_container_width=True, num_rows="dynamic", disabled=["student_id", "teacher_id"])
        
        c1, c2 = st.columns(2)
        if c1.button("💾 Sync Database", type="primary"):
            try:
                state, view = st.session_state["editor"], st.session_state["db_view"]
                # Process edits
                for idx, changes in state["edited_rows"].items():
                    row = {**st.session_state.db_results[idx], **changes}
                    if view == "students": db.update_student(row['student_id'], row['first_name'], row['last_name'], row['grade_level'], row['email'])
                    else: db.update_teacher(row['teacher_id'], row['first_name'], row['last_name'], row['subject'], row['email'])
                # Process additions
                for r in state["added_rows"]:
                    if view == "students": db.add_student(r.get('first_name',''), r.get('last_name',''), r.get('grade_level',1), r.get('email',''))
                    else: db.add_teacher(r.get('first_name',''), r.get('last_name',''), r.get('subject',''), r.get('email',''))
                # Process deletions
                for idx in state["deleted_rows"]:
                    rid = st.session_state.db_results[idx]['student_id' if view == "students" else 'teacher_id']
                    if view == "students": db.delete_student(rid)
                    else: db.delete_teacher(rid)
                
                st.session_state.db_results = db.fetch_students() if view == "students" else db.fetch_teachers()
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
        files = st.file_uploader("Attach files to your query", accept_multiple_files=True, key=st.session_state.get("uploader_key", 0))
        if st.button("🗑️ Clear Chat History", use_container_width=True): create_new_chat()

    summaries = bot.process_uploads(files) if files else []
    name = st.session_state.logged_in_username if st.session_state.user_authenticated else "Admin"
    bot.render_chat_interface(name, delay, summaries)

    if "messages" in st.session_state and st.session_state.messages:
        chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        st.sidebar.download_button("Download Chat", chat_text, file_name="chat.txt")