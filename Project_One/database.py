import mysql.connector
import json
from abc import ABC, abstractmethod

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class DatabaseManager(ABC):
    """Abstract Base Class for Database Management."""
    def __init__(self, config):
        self.__config = config

    @property
    def _config(self):
        return self.__config

    @abstractmethod
    def _get_connection(self):
        pass

class SchoolDatabase(DatabaseManager):
    """Implementation of database operations for the School Portal."""
    USERS_FILE = "users.json"

    def _get_connection(self):
        return mysql.connector.connect(**self._config)

    def fetch_students(self):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT student_id, first_name, last_name, grade_level, email FROM students")
            return cursor.fetchall()
        except mysql.connector.Error as e:
            raise DatabaseError(f"Failed to fetch students: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def fetch_teachers(self):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT teacher_id, first_name, last_name, subject, email FROM teachers")
            return cursor.fetchall()
        except mysql.connector.Error as e:
            raise DatabaseError(f"Failed to fetch teachers: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def fetch_teachers_by_subject(self, subject):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            query = "SELECT teacher_id, first_name, last_name, subject, email FROM teachers WHERE subject LIKE %s"
            cursor.execute(query, (f"%{subject}%",))
            return cursor.fetchall()
        except mysql.connector.Error as e:
            raise DatabaseError(f"Search for subject '{subject}' failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def fetch_student_by_name(self, first_name, last_name=""):
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
            return cursor.fetchone()
        except mysql.connector.Error as e:
            raise DatabaseError(f"Student search failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def update_student(self, student_id, fname, lname, grade, email):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "UPDATE students SET first_name=%s, last_name=%s, grade_level=%s, email=%s WHERE student_id=%s"
            cursor.execute(query, (fname, lname, grade, email, student_id))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            raise DatabaseError(f"Update student failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def update_teacher(self, teacher_id, fname, lname, subject, email):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "UPDATE teachers SET first_name=%s, last_name=%s, subject=%s, email=%s WHERE teacher_id=%s"
            cursor.execute(query, (fname, lname, subject, email, teacher_id))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            raise DatabaseError(f"Update teacher failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def delete_student(self, student_id):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            raise DatabaseError(f"Delete student failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def delete_teacher(self, teacher_id):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            raise DatabaseError(f"Delete teacher failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def add_teacher(self, fname, lname, subject, email):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO teachers (first_name, last_name, subject, email) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (fname, lname, subject, email))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            raise DatabaseError(f"Add teacher failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def add_student(self, fname, lname, grade, email):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO students (first_name, last_name, grade_level, email) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (fname, lname, grade, email))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            raise DatabaseError(f"Add student failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def add_user(self, username, password_hash, email):
        try:
            users = []
            try:
                with open(self.USERS_FILE, "r") as f:
                    users = json.load(f)
            except FileNotFoundError:
                pass
            
            users.append({
                "username": username,
                "password_hash": password_hash,
                "email": email
            })
            
            with open(self.USERS_FILE, "w") as f:
                json.dump(users, f, indent=4)
            return True
        except Exception as e:
            raise DatabaseError(f"User registration file error: {e}")

    def get_user_by_username(self, username):
        try:
            with open(self.USERS_FILE, "r") as f:
                users = json.load(f)
                for user in users:
                    if user['username'] == username:
                        return user
            return None
        except (FileNotFoundError, json.JSONDecodeError):
            return None