import streamlit as st

st.title("📝 TODO APP WITH SESSION")

# Initialize the task list in session state if it doesn't exist
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

def add_task(newtask):
    if newtask and newtask not in st.session_state.tasks:
        st.session_state.tasks.append(newtask)
        st.success(f"Task '{newtask}' added!")
    elif not newtask:
        st.warning("Please enter a task name.")
    else:
        st.info("That task is already in your list.")

# UI for adding tasks
new_task_input = st.text_input("What needs to be done?", placeholder="Type your task here...")
if st.button("Add Task"):
    add_task(new_task_input)

# Display the tasks
st.subheader("Your Current Tasks")
if not st.session_state.tasks:
    st.write("No tasks yet. Start by adding one above!")
else:
    for idx, task in enumerate(st.session_state.tasks):
        st.write(f"{idx + 1}. {task}")

    
