import streamlit as st
import time
from PIL import Image
import re
from database import DatabaseError
from langchain_handler import LangChainAssistant

class Intent:
    """Base class for chatbot intents."""
    pattern = None
    def matches(self, query, has_files):
        if self.pattern:
            return bool(re.search(self.pattern, query, re.IGNORECASE))
        return False
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        return ""

class WelcomeIntent(Intent):
    pattern = r"\b(hi|hello|hey|welcome|greetings)\b"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        return "Hello! I am the Elhawey School Assistant. How can I help you today?"

class HelpIntent(Intent):
    pattern = r"\b(help|commands|what can you do|how to use)\b"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        cmds = [
            "Search: 'Find student John Doe' or 'Who teaches Science?'",
            "Lists: 'Show all teachers' or 'List students in grade 10'",
            "Stats: 'How many students?' or 'System status' (Admin only)",
            "Files: Upload a file and ask me to 'analyze files'."
        ]
        return "I can help you manage school records! Try these:\n" + "\n".join([f"- {c}" for c in cmds])

class StudentCountIntent(Intent):
    """Queries the database for total student numbers."""
    pattern = r"how many.*students?"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        students = db.fetch_students()
        return f"There are currently {len(students)} students enrolled in our system."

class TeacherCountIntent(Intent):
    pattern = r"how many.*teachers?"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        teachers = db.fetch_teachers()
        return f"There are currently {len(teachers)} teachers registered in our system."

class SystemStatusIntent(Intent):
    """Provides an overview of system health (restricted to admins)."""
    pattern = r"\b(status|system|stats|overview)\b"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        if not is_admin: return "I'm sorry, only administrators can view the full system status."
        s_count = len(db.fetch_students())
        t_count = len(db.fetch_teachers())
        return f"**System Overview:**\n- Total Students: {s_count}\n- Total Teachers: {t_count}\n- Database Connection: Active"

class TeacherListIntent(Intent):
    pattern = r"(list|show|who are).*teachers?"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        teachers = db.fetch_teachers()
        if not teachers: return "There are no teachers listed in the system."
        return "Here is a list of our current teachers:\n" + "\n".join([f"- {t['first_name']} {t['last_name']} ({t['subject']})" for t in teachers])

class FileUploadIntent(Intent):
    """Triggers when a user mentions files while having active uploads."""
    pattern = r"(file|upload|analyze)"
    def matches(self, query, has_files):
        return has_files and super().matches(query, has_files)
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        return f"I've acknowledged the {len(files)} file(s) you uploaded: " + ", ".join(files) + ". How would you like me to process them?"

class StudentListIntent(Intent):
    pattern = r"(list|show|who are).*students?"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        students = db.fetch_students()
        if not students: return "There are no students listed in the system."
        return "Here is a list of our current students:\n" + "\n".join([f"- {s['first_name']} {s['last_name']} (Grade: {s['grade_level']})" for s in students])

class StudentGradeIntent(Intent):
    pattern = r"(students|who).*grade\s+(\d+)"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        match = re.search(r"grade\s+(\d+)", query)
        if not match: return "Please specify the grade number."
        
        target_grade = int(match.group(1))
        students = [s for s in db.fetch_students() if s['grade_level'] == target_grade]
        
        if not students: return f"I couldn't find any students enrolled in grade {target_grade}."
        return f"Found {len(students)} students in grade {target_grade}:\n" + "\n".join([f"- {s['first_name']} {s['last_name']}" for s in students])

class SearchStudentByNameIntent(Intent):
    """Uses AI to extract names from a sentence and then queries the database."""
    pattern = r"(find|search|who is|tell me about).*student"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        if not assistant: return "AI features are disabled. Please use a more specific command like 'Find student John Doe'."
        
        params = assistant.extract_entities(query)
        fname, lname = params.first_name, params.last_name
        
        if not fname: return "Which student are you looking for?"
        
        student = db.fetch_student_by_name(fname, lname)
        if student:
            return f"I found student **{student['first_name']} {student['last_name']}**: Grade {student['grade_level']}, Email: {student['email']}."
        return f"I couldn't find a student named '{fname} {lname or ''}'."

class SearchTeacherBySubjectIntent(Intent):
    pattern = r"(find|search|who|teaches|teacher for).*(teacher|subject|class)"
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        if not assistant: return "AI features are disabled. Try 'Show all teachers'."
        
        params = assistant.extract_entities(query)
        subject = params.subject

        if not subject: return "What subject are you looking for?"
        teachers = db.fetch_teachers_by_subject(subject)
        if not teachers: return f"I couldn't find any teachers for '{subject}'."
        
        count_prefix = "The teacher is" if len(teachers) == 1 else f"I found the following {len(teachers)} teachers:"
        return f"{count_prefix}\n" + "\n".join([f"- {t['first_name']} {t['last_name']} (Subject: {t['subject']})" for t in teachers])

class FallbackIntent(Intent):
    def matches(self, query, has_files): return True
    def resolve(self, query, db, is_admin, files, history=None, assistant=None):
        if assistant:
            try:
                return assistant.ask(query, history)
            except Exception as e:
                return f"I encountered an AI error: {str(e)}"
        return "AI features are currently unavailable. Try asking for 'help' to see local commands!"

class Chatbot:
    """Orchestrator for the Chat UI and the Intent processing engine."""
    def __init__(self, db_manager, api_key=None):
        self.db = db_manager
        self.api_key = api_key
        self.assistant = LangChainAssistant(api_key) if api_key else None
        self.intents = [
            WelcomeIntent(),
            HelpIntent(),
            StudentCountIntent(),
            TeacherCountIntent(),
            SystemStatusIntent(),
            TeacherListIntent(), 
            FileUploadIntent(),
            StudentListIntent(),
            StudentGradeIntent(),
            SearchStudentByNameIntent(),
            SearchTeacherBySubjectIntent(),
            FallbackIntent() # Must be last
        ]

    def response_generator(self, text):
        """Creates a typewriter effect for chatbot responses."""
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.05)

    def process_uploads(self, uploaded_files):
        """Parses uploaded file metadata and displays images in the sidebar."""
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

    def handle_query(self, user_input, file_summaries, delay, user_name, history=None):
        """Iterates through intents to find the first one that matches the user's input."""
        query = user_input.lower()
        is_admin = (user_name == "Admin")

        try:
            for intent in self.intents:
                if intent.matches(query, bool(file_summaries)):
                    return intent.resolve(query, self.db, is_admin, file_summaries, history=history, assistant=self.assistant)
        except DatabaseError as e:
            return f"I'm sorry, I'm having trouble accessing the school database right now. Details: {e}"

    def render_chat_interface(self, user_name, delay, file_summaries):
        """Handles the Streamlit chat UI components and message state."""
        st.subheader(f"Chatbot ({user_name})")
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if not st.session_state.messages:
            st.session_state.messages.append({"role": "assistant", "content": "Welcome to the School Portal! How can I help you today?"})

        # Display historical messages
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
                    response = self.handle_query(user_input, file_summaries, delay, user_name, history=st.session_state.messages)

                st.write_stream(self.response_generator(response))
                st.session_state.messages.append({"role": "assistant", "content": response})