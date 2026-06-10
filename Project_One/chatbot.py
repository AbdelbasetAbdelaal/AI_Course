import streamlit as st
import time
from PIL import Image
from database import DatabaseError
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

class Chatbot:
    """Orchestrator for the Chat UI using LangChain Agents and Tools."""
    def __init__(self, db_manager, api_key=None):
        self.db = db_manager
        self.api_key = api_key
        self.agent_executor = None

        if self.api_key:
            self._setup_agent()

    def _setup_agent(self):
        @tool
        def get_student_count() -> str:
            """Useful to get the total number of students in the school."""
            try:
                students = self.db.fetch_students()
                return f"There are currently {len(students)} students enrolled in our system."
            except DatabaseError as e:
                return f"Database error: {e}"

        @tool
        def get_teacher_count() -> str:
            """Useful to get the total number of teachers in the school."""
            try:
                teachers = self.db.fetch_teachers()
                return f"There are currently {len(teachers)} teachers registered in our system."
            except DatabaseError as e:
                return f"Database error: {e}"

        @tool
        def get_system_status(is_admin: bool) -> str:
            """Useful to get an overview of system health and total records. Require to know if the user is_admin."""
            if not is_admin:
                return "I'm sorry, only administrators can view the full system status."
            try:
                s_count = len(self.db.fetch_students())
                t_count = len(self.db.fetch_teachers())
                return f"**System Overview:**\n- Total Students: {s_count}\n- Total Teachers: {t_count}\n- Database Connection: Active"
            except DatabaseError as e:
                return f"Database error: {e}"

        @tool
        def list_teachers() -> str:
            """Useful to list all teachers in the school."""
            try:
                teachers = self.db.fetch_teachers()
                if not teachers: return "There are no teachers listed in the system."
                return "Here is a list of our current teachers:\n" + "\n".join([f"- {t['first_name']} {t['last_name']} ({t['subject']})" for t in teachers])
            except DatabaseError as e:
                return f"Database error: {e}"

        @tool
        def list_students() -> str:
            """Useful to list all students in the school."""
            try:
                students = self.db.fetch_students()
                if not students: return "There are no students listed in the system."
                return "Here is a list of our current students:\n" + "\n".join([f"- {s['first_name']} {s['last_name']} (Grade: {s['grade_level']})" for s in students])
            except DatabaseError as e:
                return f"Database error: {e}"

        @tool
        def find_students_by_grade(grade: int) -> str:
            """Useful to find students in a specific grade level."""
            try:
                students = [s for s in self.db.fetch_students() if s['grade_level'] == grade]
                if not students: return f"I couldn't find any students enrolled in grade {grade}."
                return f"Found {len(students)} students in grade {grade}:\n" + "\n".join([f"- {s['first_name']} {s['last_name']}" for s in students])
            except DatabaseError as e:
                return f"Database error: {e}"

        @tool
        def find_student_by_name(first_name: str, last_name: str = "") -> str:
            """Useful to find a specific student by their first and optionally last name."""
            try:
                student = self.db.fetch_student_by_name(first_name, last_name)
                if student:
                    return f"I found student **{student['first_name']} {student['last_name']}**: Grade {student['grade_level']}, Email: {student['email']}."
                return f"I couldn't find a student named '{first_name} {last_name}'."
            except DatabaseError as e:
                return f"Database error: {e}"

        @tool
        def find_teacher_by_subject(subject: str) -> str:
            """Useful to find teachers who teach a specific subject."""
            try:
                teachers = self.db.fetch_teachers_by_subject(subject)
                if not teachers: return f"I couldn't find any teachers for '{subject}'."
                count_prefix = "The teacher is" if len(teachers) == 1 else f"I found the following {len(teachers)} teachers:"
                return f"{count_prefix}\n" + "\n".join([f"- {t['first_name']} {t['last_name']} (Subject: {t['subject']})" for t in teachers])
            except DatabaseError as e:
                return f"Database error: {e}"

        tools = [
            get_student_count,
            get_teacher_count,
            get_system_status,
            list_teachers,
            list_students,
            find_students_by_grade,
            find_student_by_name,
            find_teacher_by_subject
        ]

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.7
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Elhawey School Assistant. Your role is to help students, parents, and staff. Be professional, polite, and encouraging. Use tools to fetch information from the database when needed. If the user greets you, greet them back. The user interacting with you is '{user_name}' and their admin status is '{is_admin}'."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

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
        query = user_input
        is_admin = str(user_name == "Admin")
        if file_summaries:
            query = f"I've uploaded files: {', '.join(file_summaries)}. " + query
             
        if self.agent_executor:
            chat_history = []
            if history:
                 for msg in history[:-1]:
                     role_class = HumanMessage if msg["role"] == "user" else AIMessage
                     chat_history.append(role_class(content=msg["content"]))

            try:
                response = self.agent_executor.invoke({
                    "input": query,
                    "chat_history": chat_history,
                    "user_name": user_name,
                    "is_admin": is_admin
                })
                
                output = response["output"]
                
                # Extract text if LangChain returns structured content blocks
                if isinstance(output, list):
                    extracted = []
                    for item in output:
                        if isinstance(item, dict) and "text" in item:
                            extracted.append(item["text"])
                        else:
                            extracted.append(str(item))
                    return " ".join(extracted)
                elif isinstance(output, dict) and "text" in output:
                    return output["text"]
                    
                return str(output)
            except Exception as e:
                return f"I encountered an AI error: {str(e)}"
        else:
            return "AI features are currently unavailable since no API key was provided."

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