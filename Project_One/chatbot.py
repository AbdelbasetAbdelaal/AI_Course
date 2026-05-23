import streamlit as st
import time
from PIL import Image

class Chatbot:
    """Handles chatbot logic and UI rendering."""
    def __init__(self, db_manager):
        self.db = db_manager

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
        query_lower = user_input.lower()
        is_admin = (user_name == "Admin")
        
        if file_summaries:
            summary_str = ", ".join(file_summaries)
            return f"I've received {len(file_summaries)} file(s): {summary_str}. How can I help you analyze them?"
        
        if any(word in query_lower for word in ["student", "teacher", "teach", "subject"]):
            # Predefined Query: Count Records
            if any(kw in query_lower for kw in ["how many", "count"]):
                target = "students" if "student" in query_lower else "teachers"
                data = self.db.fetch_students() if target == "students" else self.db.fetch_teachers()
                return f"There are currently {len(data)} {target} registered in the system." if data is not None else "Error counting records."
            
            # Predefined Query: List Records
            elif any(kw in query_lower for kw in ["list", "show"]):
                target = "students" if "student" in query_lower else "teachers"
                data = self.db.fetch_students() if target == "students" else self.db.fetch_teachers()
                if data:
                    if is_admin:
                        names = [f"{i['first_name']} {i['last_name']} ({i['email']})" for i in data]
                    else:
                        names = [f"{i['first_name']} {i['last_name']}" for i in data]
                    return f"Here is a list of all {target}: " + ", ".join(names)
                return f"I couldn't find any {target} in the database."
                
            # Find specific student
            elif any(kw in query_lower for kw in ["find", "search", "who is"]) and "student" in query_lower:
                search_term = query_lower
                for word in ["find", "search", "for", "about", "who", "is", "student", "the"]:
                    search_term = search_term.replace(word, "")
                
                name_parts = search_term.strip().split()
                if name_parts:
                    fname = name_parts[0].capitalize()
                    lname = name_parts[1].capitalize() if len(name_parts) > 1 else ""
                    student = self.db.fetch_student_by_name(fname, lname)
                    if student:
                        response = f"I found student **{student['first_name']} {student['last_name']}**: Grade {student['grade_level']}"
                        if is_admin:
                            response += f", Email: {student['email']}, ID: {student['student_id']}"
                        return response + "."
                return "I couldn't find that student. Who should I look up?"

            # Find specific teacher by subject
            elif any(kw in query_lower for kw in ["teach", "subject", "teacher"]) and \
                 any(kw in query_lower for kw in ["who", "find", "search", "what", "is"]):
                search_term = query_lower
                for word in ["find", "search", "for", "about", "who", "is", "teacher", "the", "teaches", "teach", "subject", "a", "an", "me", "what", "does", "?", ".", "!"]:
                    search_term = search_term.replace(word, "")
                
                subject = search_term.strip()
                if subject:
                    teachers = self.db.fetch_teachers_by_subject(subject)
                    if teachers:
                        if is_admin:
                            names = [f"{t['first_name']} {t['last_name']} ({t['email']})" for t in teachers]
                        else:
                            names = [f"{t['first_name']} {t['last_name']}" for t in teachers]
                        return f"I found the following teachers for **{subject.capitalize()}**: " + ", ".join(names) + "."
                    return f"I couldn't find any teachers for the subject '{subject}'."
                return "Which subject should I search for?"
        
        return f"You said: {user_input}. (Simulated response)"

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