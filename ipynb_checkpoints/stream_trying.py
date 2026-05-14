# =====================================================
# Name        : chatbot.py
# Copyright   : Edges For Training
# =====================================================

import streamlit as st, time
from PIL import Image

st.set_page_config(page_title="Chatbot Demo", layout="wide")
st.title(" Elhawey Chatbot")

# Helper function to simulate streaming response
def response_generator(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.05)

def create_new_chat():
    """Clears the message history, resets the file uploader, and restarts the app."""
    st.session_state.messages = []
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
    st.rerun()

# Sidebar controls
st.sidebar.title("Settings")
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
    