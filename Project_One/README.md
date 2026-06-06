# Elhawey School Portal & Chatbot Demo

A comprehensive Streamlit application that integrates an interactive chatbot with a MySQL-backed School Management System. This project demonstrates advanced Python concepts including Object-Oriented Programming (OOP) and real-time database synchronization.

## 🛠️ Used Tools & Libraries

- **[Streamlit](https://streamlit.io/):** Used for building the web-based interactive user interface.
- **[MySQL Connector](https://dev.mysql.com/doc/connector-python/en/):** Handles all communications between the Python script and the MySQL database.
- **[Pillow (PIL)](https://python-pillow.org/):** Used for image processing and rendering uploaded images in the sidebar.
- **[Hashlib](https://docs.python.org/3/library/hashlib.html):** Provides secure SHA-256 hashing for Admin authentication.
- **[JSON](https://docs.python.org/3/library/json.html):** Manages local user registration and session persistence in `users.json`.
- **[ABC (Abstract Base Classes)](https://docs.python.org/3/library/abc.html):** Used to enforce OOP design patterns (Abstraction and Polymorphism).

## 🚀 Key Features

### 1. Interactive Chatbot
- **Typewriter Effect:** Uses Python generators to simulate a "typing" response from the AI.
- **File Awareness:** The chatbot can acknowledge and summarize files uploaded by the user.
- **Database Querying:** Processes natural language requests to list, count, or find specific student and teacher records in real-time.
- **History Export:** Users can download their current chat session as a `.txt` file.

### 2. School Database Management
- **OOP Implementation:**
    - **Abstraction:** `DatabaseManager` defines the template for database connectivity.
    - **Encapsulation:** Database configurations are kept private.
    - **Inheritance:** `SchoolDatabase` inherits and implements management logic.
- **CRUD Operations:** Full Create, Read, Update, and Delete capabilities for Students and Teachers.
- **Live Data Editor:** Uses `st.data_editor` to allow batch updates and deletions directly in a spreadsheet-like UI.

### 3. Security & RBAC
- **User Authentication:** Includes a self-service registration and login system for standard users.
- **Role-Based Access Control:** Restricts database management, batch editing, and administrative tools to authenticated Admins.

## 📖 How to Use

### Prerequisites
1. Install a local MySQL server (e.g., **XAMPP** or **WAMP**).
2. Create a database named `school_db`.
3. Create the necessary tables:
   ```sql
   CREATE TABLE students (
       student_id INT AUTO_INCREMENT PRIMARY KEY,
       first_name VARCHAR(50),
       last_name VARCHAR(50),
       grade_level INT,
       email VARCHAR(100)
   );

   CREATE TABLE teachers (
       teacher_id INT AUTO_INCREMENT PRIMARY KEY,
       first_name VARCHAR(50),
       last_name VARCHAR(50),
       subject VARCHAR(50),
       email VARCHAR(100)
   );
   ```
4. Run the app: `streamlit run Project_One.py`
5. Default Admin Password: `admin`

## 🧪 How to Test the Chatbot

1. **Register a User:** Click the "User Login/Register" button in the sidebar and create a new account.
2. **Log In:** Use your new credentials to log in. You will be automatically redirected to the Chatbot page.
3. **Ask Database Queries:** Interact with the chatbot by typing queries such as:
    - *"List all students"*
    - *"How many teachers are registered in the system?"*
    - *"Find student Alice Johnson"* (Note: Ensure the record exists in your MySQL database).
    - `Find student Alice Johnson`
    - *"Who is the Math teacher?"* or *"Search for a Science teacher"*
4. **Verify Admin Sync:** Log in as Admin (password: `admin`), modify a record in the dashboard, then log back in as a user and ask the chatbot for that record to verify real-time synchronization.