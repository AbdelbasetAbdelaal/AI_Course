import streamlit as st
import time
from PIL import Image
import re
from database import DatabaseError

class Intent:
    """Base class for chatbot intents."""
    pattern = None
    def matches(self, query, has_files):
        if self.pattern:
            return bool(re.search(self.pattern, query, re.IGNORECASE))
        return False
    def resolve(self, query, db, is_admin, files):
        return ""

class WelcomeIntent(Intent):
    pattern = r"\b(hi|hello|hey|welcome|greetings)\b"
    def resolve(self, query, db, is_admin, files):
        return "Hello! I am the Elhawey School Assistant. How can I help you today?"

class StudentCountIntent(Intent):
    pattern = r"how many.*students?"
    def resolve(self, query, db, is_admin, files):
        students = db.fetch_students()
        return f"There are currently {len(students)} students enrolled in our system."

class TeacherCountIntent(Intent):
    pattern = r"how many.*teachers?"
    def resolve(self, query, db, is_admin, files):
        teachers = db.fetch_teachers()
        return f"There are currently {len(teachers)} teachers registered in our system."

class TeacherListIntent(Intent):
    pattern = r"(list|show|who are).*teachers?"
    def resolve(self, query, db, is_admin, files):
        teachers = db.fetch_teachers()
        if not teachers: return "There are no teachers listed in the system."
        return "Here is a list of our current teachers:\n" + "\n".join([f"- {t['first_name']} {t['last_name']} ({t['subject']})" for t in teachers])

class FileUploadIntent(Intent):
    pattern = r"(file|upload|analyze)"
    def matches(self, query, has_files):
        return has_files and super().matches(query, has_files)
    def resolve(self, query, db, is_admin, files):
        return f"I've acknowledged the {len(files)} file(s) you uploaded: " + ", ".join(files) + ". How would you like me to process them?"

class StudentListIntent(Intent):
    pattern = r"(list|show|who are).*students?"
    def resolve(self, query, db, is_admin, files):
        students = db.fetch_students()
        if not students: return "There are no students listed in the system."
        return "Here is a list of our current students:\n" + "\n".join([f"- {s['first_name']} {s['last_name']} (Grade: {s['grade_level']})" for s in students])

class SearchStudentByNameIntent(Intent):
    pattern = r"(find|search|who is|tell me about).*student"
    def resolve(self, query, db, is_admin, files):
        words = query.split()
        ignore = {"search", "find", "for", "a", "an", "the", "student", "students", "who", "is", "about"}
        name_parts = [w.capitalize() for w in words if w not in ignore]
        
        if not name_parts: return "Which student are you looking for?"
        
        fname = name_parts[0]
        lname = name_parts[1] if len(name_parts) > 1 else ""
        student = db.fetch_student_by_name(fname, lname)
        
        if student:
            return f"I found student **{student['first_name']} {student['last_name']}**: Grade {student['grade_level']}, Email: {student['email']}."
        return f"I couldn't find a student named '{' '.join(name_parts)}'."

class SearchTeacherBySubjectIntent(Intent):
    pattern = r"(find|search|who|who's).*teacher"
    def resolve(self, query, db, is_admin, files):
        # Extract subject by filtering out common stop words and command keywords
        words = query.split()
        ignore = {"search", "find", "for", "a", "an", "the", "teacher", "teachers", "who", "is", "any"}
        subject_parts = [w for w in words if w not in ignore]
        subject = " ".join(subject_parts)
        
        if not subject: return "What subject are you looking for?"
        teachers = db.fetch_teachers_by_subject(subject)
        if not teachers: return f"I couldn't find any teachers for '{subject}'."
        
        count_prefix = "The teacher is" if len(teachers) == 1 else f"I found the following {len(teachers)} teachers:"
        return f"{count_prefix}\n" + "\n".join([f"- {t['first_name']} {t['last_name']} (Subject: {t['subject']})" for t in teachers])

class Chatbot:
    """Handles chatbot logic and UI rendering."""
    def __init__(self, db_manager):
        self.db = db_manager
        self.intents = [
            WelcomeIntent(),
            StudentCountIntent(),
            TeacherCountIntent(),
            TeacherListIntent(), 
            FileUploadIntent(),
            StudentListIntent(),
            SearchStudentByNameIntent(),
            SearchTeacherBySubjectIntent()
        ]

    def response_generator(self, text):
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.05)

    def process_uploads(self, uploaded_files):
        summaries = []
        for uploaded_file in uploaded_files:
            if uploaded_file.type == "text/plain":
                content = uploaded_file.read().decode("utf-8")
                summaries.append(f"Text file '{uploaded_file.name}' ({len(content)} chars)")
            elif uploaded_file.type in ["image/png", "image/jpeg"]:
                try:
                    img = Image.open(uploaded_file)
                    st.sidebar.image(img, caption=f"Uploaded: {uploaded_file.name}", use_container_width=True)
                    summaries.append(f"Image '{uploaded_file.name}' ({img.format}, {img.size[0]}x{img.size[1]})")
                except Exception as e:
                    st.sidebar.error(f"Error loading {uploaded_file.name}: {e}")
            else:
                summaries.append(f"File '{uploaded_file.name}' (Type: {uploaded_file.type})")
        return summaries

    def handle_query(self, user_input, file_summaries, delay, user_name):
        query = user_input.lower()
        is_admin = (user_name == "Admin")

        try:
            for intent in self.intents:
                if intent.matches(query, bool(file_summaries)):
                    return intent.resolve(query, self.db, is_admin, file_summaries)
        except DatabaseError as e:
            return f"I'm sorry, I'm having trouble accessing the school database right now. Details: {e}"

        return "I'm sorry, I don't know how to handle that request."

    def render_chat_interface(self, user_name, delay, file_summaries):
        st.subheader(f"Chatbot ({user_name})")
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if not st.session_state.messages:
            st.session_state.messages.append({"role": "assistant", "content": "Welcome to the School Portal! How can I help you today?"})

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Type your message...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            
            with st.chat_message("assistant"):
                with st.spinner("Assistant is typing..."):
                    time.sleep(delay)
                    response = self.handle_query(user_input, file_summaries, delay, user_name)

                st.write_stream(self.response_generator(response))
                st.session_state.messages.append({"role": "assistant", "content": response})