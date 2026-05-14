# =====================================================
# Name        : chatbot.py
# Copyright   : Edges For Training
# =====================================================

import streamlit as st
import time
import mysql.connector
import hashlib
from PIL import Image

# Database connection configuration for XAMPP
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'school_db'
}

# Admin password (for demonstration purposes, use a strong, hashed password in production)
ADMIN_PASSWORD_HASH = hashlib.sha256("admin".encode()).hexdigest()

st.set_page_config(page_title="Chatbot Demo", layout="wide")
st.title(" Elhawey Chatbot")

# Helper function to simulate streaming response
def response_generator(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.05)

class SchoolDatabase:
    """OOP implementation for school database operations."""
    def __init__(self, config):
        self.config = config

    def _get_connection(self):
        return mysql.connector.connect(**self.config)

    def fetch_students(self):
        """Read-access: Fetches student records."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT student_id, first_name, last_name, grade_level, email FROM students")
            return cursor.fetchall()
        except mysql.connector.Error as e:
            st.error(f"Read error: {e}")
            return None
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def fetch_teachers(self):
        """Read-access: Fetches teacher records."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT teacher_id, first_name, last_name, subject, email FROM teachers")
            return cursor.fetchall()
        except mysql.connector.Error as e:
            st.error(f"Read error: {e}")
            return None
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def update_student(self, student_id, fname, lname, grade, email):
        """Update an existing student record in the database."""
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
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def update_teacher(self, teacher_id, fname, lname, subject, email):
        """Update an existing teacher record in the database."""
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
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def delete_student(self, student_id):
        """Remove a student record from the database."""
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
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def delete_teacher(self, teacher_id):
        """Remove a teacher record from the database."""
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
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def add_student(self, fname, lname, grade, email):
        """Write-access: Adds a new student record."""
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
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    def add_teacher(self, fname, lname, subject, email):
        """Write-access: Adds a new teacher record."""
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
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

db = SchoolDatabase(db_config)

def create_new_chat():
    """Clears the message history, resets the file uploader, and restarts the app."""
    st.session_state.messages = []
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
    st.rerun()

# Sidebar controls
st.sidebar.title("Settings")

# Initialize admin authentication status
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# Role-Based Access Control (RBAC)
role = st.sidebar.selectbox("Identity Role", ["User", "Admin"])
st.sidebar.write(f"Access Level: **{role}**")

# Admin password input
if role == "Admin" and not st.session_state.admin_authenticated:
    password_input = st.sidebar.text_input("Admin Password", type="password")
    if st.sidebar.button("Login"):
        if hashlib.sha256(password_input.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            st.session_state.admin_authenticated = True
            st.sidebar.success("Logged in as Admin!")
        else:
            st.sidebar.error("Incorrect password.")
elif role == "Admin" and st.session_state.admin_authenticated:
    st.sidebar.success("Admin access granted.")
    if st.sidebar.button("Logout"):
        st.session_state.admin_authenticated = False

if st.sidebar.button("🎓 Fetch Student Records"):
    with st.spinner("Connecting to database..."):
        data = db.fetch_students()
        if data is not None:
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
if role == "Admin" and st.session_state.admin_authenticated:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Admin: Database Entry")
    
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

delay = st.sidebar.slider("Response delay (s)", 0.0, 5.0, 1.0)
uploaded_files = st.sidebar.file_uploader(
    "Upload files", type=["txt", "png", "jpg", "jpeg", "pdf", "py", "csv"],
    key=st.session_state.get("uploader_key", 0),
    accept_multiple_files=True
)

file_summaries = []
if uploaded_files:
    for uploaded_file in uploaded_files:
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

if st.sidebar.button("➕ New Chat"):
    create_new_chat()

# Display Database Results if they exist in session state
if "db_results" in st.session_state:
    st.data_editor(
        st.session_state.db_results,
        key="student_editor",
        use_container_width=True,
        num_rows="dynamic",
        disabled=["student_id", "teacher_id"] # Primary keys should not be edited
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save All Changes to Database", type="primary"):
            # Access the specific changes from session state
            state = st.session_state["student_editor"]
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
            if view == "students":
                st.session_state.db_results = db.fetch_students()
            else:
                st.session_state.db_results = db.fetch_teachers()
            st.rerun()
    with col2:
        if st.button("🗑️ Clear Table View"):
            del st.session_state.db_results
            st.rerun()

# Initialize message history
if "messages" not in st.session_state:
    st.session_state.messages = []
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I am a chatbot. Ask me anything."})

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
            else:
                response = f"You said: {user_input}. (Simulated response)" 

        # Use the typewriter effect
        st.write_stream(response_generator(response))
        st.session_state.messages.append({"role": "assistant", "content": response})

# Add download functionality
# Ensure the button is visible as long as there are messages (including greeting)
if "messages" in st.session_state and st.session_state.messages:
    chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages])
    st.sidebar.download_button(
        "Download chat", 
        chat_text,
        file_name="chat_history.txt",
        mime="text/plain"
    )
    