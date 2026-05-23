import mysql.connector
from mysql.connector import pooling
import logging
from abc import ABC, abstractmethod

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class DatabaseManager(ABC):
    """Abstract Base Class for Database Management."""
    def __init__(self, config):
        self.__config = config
        try:
            self._pool = pooling.MySQLConnectionPool(
                pool_name="school_pool",
                pool_size=5,
                **self.__config
            )
        except mysql.connector.Error as e:
            raise DatabaseError(f"Error creating connection pool: {e}")

    @property
    def _config(self):
        return self.__config

    def _get_connection(self):
        try:
            return self._pool.get_connection()
        except mysql.connector.Error as e:
            raise DatabaseError(f"Failed to get connection from pool: {e}")

class SchoolDatabase(DatabaseManager):
    """Implementation of database operations for the School Portal."""

    def setup_database(self):
        """Ensures all necessary tables exist."""
        tables = {
            "students": """
                CREATE TABLE IF NOT EXISTS students (
                    student_id INT AUTO_INCREMENT PRIMARY KEY,
                    first_name VARCHAR(50),
                    last_name VARCHAR(50),
                    grade_level INT,
                    email VARCHAR(100)
                )
            """,
            "teachers": """
                CREATE TABLE IF NOT EXISTS teachers (
                    teacher_id INT AUTO_INCREMENT PRIMARY KEY,
                    first_name VARCHAR(50),
                    last_name VARCHAR(50),
                    subject VARCHAR(50),
                    email VARCHAR(100)
                )
            """,
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE,
                    password_hash VARCHAR(64),
                    email VARCHAR(100)
                )
            """
        }
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            for table_name, ddl in tables.items():
                cursor.execute(ddl)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

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
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, password_hash, email))
            conn.commit()
            return True
        except mysql.connector.Error as e:
            raise DatabaseError(f"User registration failed: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_user_by_username(self, username):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, password_hash, email FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"Error fetching user: {e}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()