# =====================================================
# Name        : Project_One.py.py
# Copyright   : Abdelbaset Abdelaal
# =====================================================

import streamlit as st
import time
import json
import mysql.connector
from abc import ABC, abstractmethod
import hashlib
from PIL import Image

# Database connection configuration for XAMPP
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'school_db'
}

# Secure Admin password hash (SHA-256)
# In a real app, these credentials should be stored in a secure secrets manager or database.
ADMIN_PASSWORD_HASH = hashlib.sha256("admin".encode()).hexdigest()
USERS_FILE = "users.json"

st.set_page_config(page_title="Elhawey School Portal", layout="wide")
st.title(" Elhawey Chatbot")

# Helper function to simulate streaming response
def response_generator(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.05)

class DatabaseManager(ABC):
    """Abstract Base Class demonstrating Abstraction."""
    def __init__(self, config):
        # Encapsulation: Private attribute to hide configuration details
        self.__config = config

    @property
    def _config(self):
        return self.__config

    @abstractmethod
    def _get_connection(self):
        """Abstract method to be implemented by subclasses (Polymorphism)."""
        pass

class SchoolDatabase(DatabaseManager):
    """Implementation demonstrating Inheritance."""
    def _get_connection(self):
        return mysql.connector.connect(**self._config)

    def fetch_students(self):
        """Read-access: Fetches student records."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT student_id, first_name, last_name, grade_level, email FROM students")
            return cursor.fetchall()
        except mysql.connector.Error as e:
            st.error(f"Read error: {e}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def fetch_teachers(self):
        """Read-access: Fetches teacher records."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT teacher_id, first_name, last_name, subject, email FROM teachers")
            return cursor.fetchall()
        except mysql.connector.Error as e:
            st.error(f"Read error: {e}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def fetch_student_by_name(self, first_name, last_name=""):
        """Read-access: Fetches a specific student record by name."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT student_id, first_name, last_name, grade_level, email FROM students WHERE first_name = %s"
            params = [first_name]
            if last_name:
                query += " AND last_name = %s"
                params.append(last_name)
            cursor.execute(query, tuple(params))
            return cursor.fetchone() # Assuming unique names or just returning the first match
        except mysql.connector.Error as e:
            st.error(f"Read error: {e}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def update_student(self, student_id, fname, lname, grade, email):
        """Update an existing student record in the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "UPDATE students SET first_name=%s, last_name=%s, grade_level=%s, email=%s WHERE student_id=%s"
            cursor.execute(query, (fname, lname, grade, email, student_id))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            st.error(f"Update error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def update_teacher(self, teacher_id, fname, lname, subject, email):
        """Update an existing teacher record in the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "UPDATE teachers SET first_name=%s, last_name=%s, subject=%s, email=%s WHERE teacher_id=%s"
            cursor.execute(query, (fname, lname, subject, email, teacher_id))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            st.error(f"Update error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def delete_student(self, student_id):
        """Remove a student record from the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            st.error(f"Delete error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def delete_teacher(self, teacher_id):
        """Remove a teacher record from the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            st.error(f"Delete error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def add_student(self, fname, lname, grade, email):
        """Write-access: Adds a new student record."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO students (first_name, last_name, grade_level, email) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (fname, lname, grade, email))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            st.error(f"Write error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def add_teacher(self, fname, lname, subject, email):
        """Write-access: Adds a new teacher record."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO teachers (first_name, last_name, subject, email) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (fname, lname, subject, email))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            st.error(f"Write error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def add_user(self, username, password_hash, email):
        """Adds a new user record to users.json."""
        try:
            users = []
            try:
                with open(USERS_FILE, "r") as f:
                    users = json.load(f)
            except FileNotFoundError:
                pass
            
            users.append({
                "username": username,
                "password_hash": password_hash,
                "email": email
            })
            
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=4)
            return True
        except Exception as e:
            st.error(f"File write error: {e}")
            return False

    def get_user_by_username(self, username):
        """Retrieves user details by username from users.json."""
        try:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
                for user in users:
                    if user['username'] == username:
                        return user
            return None
        except (FileNotFoundError, json.JSONDecodeError):
            return None

db = SchoolDatabase(db_config)

def create_new_chat():
    """Clears the message history, resets the file uploader, and restarts the app."""
    st.session_state.messages = []
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
    st.rerun()

# Sidebar controls
st.sidebar.title("Settings")

# Initialize authentication and page state
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False
if "logged_in_username" not in st.session_state:
    st.session_state.logged_in_username = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "home" # home, user_login_register, admin_login, chatbot, admin_dashboard

# --- Navigation Buttons ---
if st.session_state.admin_authenticated or st.session_state.user_authenticated:
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

# --- Conditional Page Rendering ---
if st.session_state.current_page == "home":
    st.write("Please select a role to proceed.")
elif st.session_state.current_page == "user_login_register":
    st.sidebar.subheader("User Login / Registration")

    # User Login Form
    with st.sidebar.form("user_login_form"):
        st.markdown("#### Login")
        login_username = st.text_input("Username")
        login_password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = db.get_user_by_username(login_username)
            if user:
                if hashlib.sha256(login_password.encode()).hexdigest() == user['password_hash']:
                    st.session_state.user_authenticated = True
                    st.session_state.logged_in_username = login_username
                    st.session_state.current_page = "chatbot"
                    st.sidebar.success(f"Welcome, {login_username}!")
                    st.rerun()
                else:
                    st.sidebar.error("Incorrect password.")
            else:
                st.sidebar.error("Username not found.")

    st.sidebar.markdown("---")

    # User Registration Form
    with st.sidebar.form("user_registration_form"):
        st.markdown("#### Register")
        reg_username = st.text_input("New Username")
        reg_password = st.text_input("New Password", type="password")
        reg_confirm_password = st.text_input("Confirm Password", type="password")
        reg_email = st.text_input("Email (Optional)")
        if st.form_submit_button("Register"):
            if not reg_username or not reg_password or not reg_confirm_password:
                st.sidebar.error("Username, Password, and Confirm Password are required.")
            elif reg_password != reg_confirm_password:
                st.sidebar.error("Passwords do not match.")
            else:
                # Check if username already exists
                if db.get_user_by_username(reg_username):
                    st.sidebar.error("Username already exists. Please choose a different one.")
                else:
                    hashed_password = hashlib.sha256(reg_password.encode()).hexdigest()
                    if db.add_user(reg_username, hashed_password, reg_email):
                        st.sidebar.success("Registration successful! Please log in.")
                        # Optionally log in the user immediately
                        # st.session_state.user_authenticated = True
                        # st.session_state.logged_in_username = reg_username
                        # st.session_state.current_page = "chatbot"
                        st.rerun()
                    else:
                        st.sidebar.error("Failed to register user.")

elif st.session_state.current_page == "admin_login":
    st.sidebar.subheader("Admin Login")
    admin_password_input = st.sidebar.text_input("Admin Password", type="password")
    if st.sidebar.button("Login as Admin"):
        if hashlib.sha256(admin_password_input.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            st.session_state.admin_authenticated = True
            st.session_state.current_page = "admin_dashboard"
            st.sidebar.success("Logged in as Admin!")
            st.rerun()
        else:
            st.sidebar.error("Incorrect password.")

# --- Admin Dashboard (visible only if admin_authenticated) ---
if st.session_state.admin_authenticated and st.session_state.current_page == "admin_dashboard":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Admin Actions")

    # --- Database Query Buttons ---
    if st.sidebar.button("🎓 Fetch Student Records"):
        with st.spinner("Connecting to database..."):
            data = db.fetch_students()
            if data is not None:
                # Store results in session state to persist between reruns
                st.session_state.db_results = data
                st.session_state.db_view = "students"
                st.sidebar.success(f"Successfully fetched {len(data)} records.")

    if st.sidebar.button("👨‍🏫 Fetch Teacher Records"):
        with st.spinner("Connecting to database..."):
            data = db.fetch_teachers()
            if data is not None:
                st.session_state.db_results = data
                st.session_state.db_view = "teachers"
                st.sidebar.success(f"Successfully fetched {len(data)} records.")

    # Admin Write Operations (only if authenticated)
    st.sidebar.markdown("---")
    st.sidebar.subheader("Admin: Database Entry")
    
    # Form to add students - demonstrates standard CRUD 'Create'
    with st.sidebar.expander("➕ Add New Student"):
        with st.form("student_form", clear_on_submit=True):
            fn = st.text_input("First Name")
            ln = st.text_input("Last Name")
            gl = st.number_input("Grade Level", 1, 12, 1)
            em = st.text_input("Email")
            if st.form_submit_button("Save Student"):
                if fn and ln and em:
                    if db.add_student(fn, ln, gl, em):
                        st.sidebar.success("Student added successfully!")
                        # Refresh the table if it is currently displayed
                        if "db_results" in st.session_state:
                            st.session_state.db_results = db.fetch_students()
                else:
                    st.sidebar.error("All fields are required.")

    # Form to add teachers
    with st.sidebar.expander("➕ Add New Teacher"):
        with st.form("teacher_form", clear_on_submit=True):
            tfn = st.text_input("First Name")
            tln = st.text_input("Last Name")
            sub = st.text_input("Subject")
            tem = st.text_input("Email")
            if st.form_submit_button("Save Teacher"):
                if tfn and tln and tem:
                    if db.add_teacher(tfn, tln, sub, tem):
                        st.sidebar.success("Teacher added successfully!")
                else:
                    st.sidebar.error("All fields are required.")

# --- Sidebar Utilities (visible to all, but chatbot interaction depends on auth) ---
st.sidebar.markdown("---")
st.sidebar.subheader("Chatbot Settings")

delay = st.sidebar.slider("Response delay (s)", 0.0, 5.0, 1.0)
uploaded_files = st.sidebar.file_uploader(
    "Upload files", type=["txt", "png", "jpg", "jpeg", "pdf", "py", "csv"],
    key=st.session_state.get("uploader_key", 0),
    accept_multiple_files=True
)

# Process uploaded files to generate summaries for the chatbot
file_summaries = []
if uploaded_files:
    for uploaded_file in uploaded_files:
        # Handle different MIME types accordingly
        if uploaded_file.type == "text/plain":
            # Handle text files
            content = uploaded_file.read().decode("utf-8")
            file_summaries.append(f"Text file '{uploaded_file.name}' ({len(content)} chars)")
        elif uploaded_file.type in ["image/png", "image/jpeg"]:
            # Handle image files
            try:
                img = Image.open(uploaded_file)
                st.sidebar.image(img, caption=f"Uploaded: {uploaded_file.name}", use_container_width=True)
                file_summaries.append(f"Image '{uploaded_file.name}' ({img.format}, {img.size[0]}x{img.size[1]})")
            except Exception as e:
                st.sidebar.error(f"Error loading {uploaded_file.name}: {e}")
        else:
            file_summaries.append(f"File '{uploaded_file.name}' (Type: {uploaded_file.type})")

# Option to reset chat session
if st.sidebar.button("➕ New Chat"):
    create_new_chat()


# --- Main Content Area ---
if st.session_state.current_page == "admin_dashboard" and st.session_state.admin_authenticated:
    st.subheader("Admin Dashboard")
    if "db_results" in st.session_state:
        st.data_editor(
            st.session_state.db_results,
            key="data_editor", # Changed key to avoid conflict if multiple editors were present
            use_container_width=True,
            num_rows="dynamic",
            disabled=["student_id", "teacher_id"] # Primary keys should not be edited
        )

        col1, col2 = st.columns(2)
        with col1:
            # Synchronization logic for the data editor
            if st.button("💾 Save All Changes to Database", type="primary"):
                # Access the specific changes from session state
                state = st.session_state["data_editor"]
                view = st.session_state.get("db_view", "students")
                
                # 1. Handle Updates (Edits)
                for row_idx, row_changes in state["edited_rows"].items():
                    orig = st.session_state.db_results[row_idx]
                    u = {**orig, **row_changes}
                    if view == "students":
                        db.update_student(u['student_id'], u['first_name'], u['last_name'], u['grade_level'], u['email'])
                    else:
                        db.update_teacher(u['teacher_id'], u['first_name'], u['last_name'], u['subject'], u['email'])
                
                # 2. Handle Additions (New rows added in-table)
                for new_row in state["added_rows"]:
                    if view == "students":
                        db.add_student(
                            new_row.get('first_name', ''), 
                            new_row.get('last_name', ''), 
                            new_row.get('grade_level', 1), 
                            new_row.get('email', '')
                        )
                    else:
                        db.add_teacher(
                            new_row.get('first_name', ''),
                            new_row.get('last_name', ''),
                            new_row.get('subject', ''),
                            new_row.get('email', '')
                        )
                
                # 3. Handle Deletions
                for row_idx in state["deleted_rows"]:
                    if view == "students":
                        id_to_del = st.session_state.db_results[row_idx]['student_id']
                        db.delete_student(id_to_del)
                    else:
                        id_to_del = st.session_state.db_results[row_idx]['teacher_id']
                        db.delete_teacher(id_to_del)
                
                st.success("Database synced successfully!")
                # Refresh local session state with the latest DB version
                if view == "students":
                    st.session_state.db_results = db.fetch_students()
                else:
                    st.session_state.db_results = db.fetch_teachers()
                st.rerun()
                
        with col2:
            if st.button("🗑️ Clear Table View"):
                del st.session_state.db_results
                st.rerun()
    else:
        st.info("Use the sidebar buttons to fetch student or teacher records.")

elif st.session_state.current_page == "chatbot" and (st.session_state.user_authenticated or st.session_state.admin_authenticated):
    st.subheader(f"Chatbot ({st.session_state.logged_in_username if st.session_state.user_authenticated else 'Admin'})")
    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if not st.session_state.messages:
        st.session_state.messages.append({"role": "assistant", "content": "Welcome to the School Portal! How can I help you today?"})

    # Display existing chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Type your message...")
    if user_input:
        # Display user message immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            # Display a spinner while "thinking"
            with st.spinner("Assistant is typing..."):
                time.sleep(delay) # simulate delay
                if file_summaries:
                    summary_str = ", ".join(file_summaries)
                    response = f"I've received {len(uploaded_files)} file(s): {summary_str}. How can I help you analyze them?"
                elif "student" in user_input.lower():
                    # Check for specific student query
                    if any(keyword in user_input.lower() for keyword in ["find", "search for", "about"]):
                        name_keywords = ["find", "search for", "about", "student"]
                        potential_name_parts = []
                        user_input_lower = user_input.lower()
                        
                        # Extract words after keywords
                        split_input = user_input_lower.split()
                        start_index = -1
                        for keyword in name_keywords:
                            if keyword in split_input:
                                start_index = split_input.index(keyword) + 1
                                break
                        
                        if start_index != -1 and start_index < len(split_input):
                            potential_name = " ".join(split_input[start_index:]).replace("student", "").strip()
                            name_components = [n.capitalize() for n in potential_name.split(maxsplit=1)]
                            first_name = name_components[0] if name_components else ""
                            last_name = name_components[1] if len(name_components) > 1 else ""

                            if first_name:
                                student_data = db.fetch_student_by_name(first_name, last_name)
                                if student_data:
                                    response = f"I found student: {student_data['first_name']} {student_data['last_name']} (Grade {student_data['grade_level']}, Email: {student_data['email']})."
                                else:
                                    response = f"I couldn't find a student named {first_name} {last_name}."
                            else:
                                response = "Please specify the name of the student you are looking for."
                        else:
                            # Fallback to listing all students if no specific name is found after keywords
                            data = db.fetch_students()
                            if data is None:
                                response = "I'm sorry, I encountered an error while trying to fetch student records from the database."
                            elif data:
                                student_list = ", ".join([f"{s['first_name']} {s['last_name']} (Grade {s['grade_level']})" for s in data])
                                response = f"I found {len(data)} student(s) in the system: {student_list}."
                            else:
                                response = "I checked the database, but there are currently no students registered."
                    else:
                        # Original behavior: list all students
                        data = db.fetch_students()
                        if data is None:
                            response = "I'm sorry, I encountered an error while trying to fetch student records from the database."
                        elif data:
                            student_list = ", ".join([f"{s['first_name']} {s['last_name']} (Grade {s['grade_level']})" for s in data])
                            response = f"I found {len(data)} student(s) in the system: {student_list}."
                        else:
                            response = "I checked the database, but there are currently no students registered."
                else:
                    response = f"You said: {user_input}. (Simulated response)" 

            # Use the typewriter effect
            st.write_stream(response_generator(response))
            st.session_state.messages.append({"role": "assistant", "content": response})

    # --- Main UI: Chat Export ---
    # Ensure the button is visible as long as there are messages (including greeting)
    if "messages" in st.session_state and st.session_state.messages:
        chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages])
        st.sidebar.download_button(
            "Download chat", 
            chat_text,
            file_name="chat_history.txt",
            mime="text/plain"
        )
else:
    if not st.session_state.admin_authenticated and not st.session_state.user_authenticated:
        st.info("Please log in or register to access the chatbot or admin features.")