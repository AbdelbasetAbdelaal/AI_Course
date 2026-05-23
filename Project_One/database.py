import mysql.connector
from mysql.connector import pooling
import logging
from abc import ABC
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class DatabaseManager(ABC):
    """Abstract Base Class for Database Management."""
    def __init__(self, config: Dict[str, Any]):
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
    def _config(self) -> Dict[str, Any]:
        return self.__config

    @contextmanager
    def _get_cursor(self, dictionary: bool = False):
        """Context manager to handle connection and cursor lifecycle."""
        conn = None
        cursor = None
        try:
            conn = self._pool.get_connection()
            cursor = conn.cursor(dictionary=dictionary)
            yield cursor
            conn.commit()
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Database error: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

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
        with self._get_cursor() as cursor:
            for table_name, ddl in tables.items():
                cursor.execute(ddl)

    def fetch_students(self) -> List[Dict[str, Any]]:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT student_id, first_name, last_name, grade_level, email FROM students")
            return cursor.fetchall()

    def get_grade_distribution(self) -> List[Dict[str, Any]]:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT grade_level, COUNT(*) as count FROM students GROUP BY grade_level ORDER BY grade_level")
            return cursor.fetchall()

    def fetch_teachers(self) -> List[Dict[str, Any]]:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT teacher_id, first_name, last_name, subject, email FROM teachers")
            return cursor.fetchall()

    def fetch_teachers_by_subject(self, subject: str) -> List[Dict[str, Any]]:
        with self._get_cursor(dictionary=True) as cursor:
            query = "SELECT teacher_id, first_name, last_name, subject, email FROM teachers WHERE subject LIKE %s"
            cursor.execute(query, (f"%{subject}%",))
            return cursor.fetchall()

    def fetch_student_by_name(self, first_name: str, last_name: str = "") -> Optional[Dict[str, Any]]:
        with self._get_cursor(dictionary=True) as cursor:
            query = "SELECT student_id, first_name, last_name, grade_level, email FROM students WHERE first_name = %s"
            params = [first_name]
            if last_name:
                query += " AND last_name = %s"
                params.append(last_name)
            cursor.execute(query, tuple(params))
            return cursor.fetchone()

    def update_student(self, student_id: int, fname: str, lname: str, grade: int, email: str) -> bool:
        with self._get_cursor() as cursor:
            query = "UPDATE students SET first_name=%s, last_name=%s, grade_level=%s, email=%s WHERE student_id=%s"
            cursor.execute(query, (fname, lname, grade, email, student_id))
            return True

    def update_teacher(self, teacher_id: int, fname: str, lname: str, subject: str, email: str) -> bool:
        with self._get_cursor() as cursor:
            query = "UPDATE teachers SET first_name=%s, last_name=%s, subject=%s, email=%s WHERE teacher_id=%s"
            cursor.execute(query, (fname, lname, subject, email, teacher_id))
            return True

    def delete_student(self, student_id: int) -> bool:
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            return True

    def delete_teacher(self, teacher_id: int) -> bool:
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
            return True

    def add_teacher(self, fname: str, lname: str, subject: str, email: str) -> bool:
        with self._get_cursor() as cursor:
            query = "INSERT INTO teachers (first_name, last_name, subject, email) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (fname, lname, subject, email))
            return True

    def add_student(self, fname: str, lname: str, grade: int, email: str) -> bool:
        with self._get_cursor() as cursor:
            query = "INSERT INTO students (first_name, last_name, grade_level, email) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (fname, lname, grade, email))
            return True

    def add_user(self, username: str, password_hash: str, email: str) -> bool:
        with self._get_cursor() as cursor:
            query = "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, password_hash, email))
            return True

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT username, password_hash, email FROM users WHERE username = %s", (username,))
            return cursor.fetchone()