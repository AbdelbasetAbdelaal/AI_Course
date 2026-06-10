# Standard libraries for MySQL connection and utility
import mysql.connector
from mysql.connector import pooling
import logging
from abc import ABC
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union

# Set up logging for tracking database errors
logger = logging.getLogger(__name__)

# Type Aliases for better readability
QueryResult = List[Dict[str, Any]]
RowResult = Optional[Dict[str, Any]]

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class DatabaseManager(ABC):
    """Abstract Base Class providing connection pooling and cursor lifecycle management."""
    def __init__(self, config: Dict[str, Any]):
        self.__config = config
        try:
            # Initialize a connection pool to reuse database connections efficiently
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
            conn = self._pool.get_connection() # Fetch a connection from the pool
            cursor = conn.cursor(dictionary=dictionary)
            yield cursor
            conn.commit()
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Database error: {e}")
        finally:
            # Ensure resources are released back to the pool even if an error occurs
            if cursor:
                cursor.close()
            if conn:
                conn.close()

class SchoolDatabase(DatabaseManager):
    """High-level implementation of school-specific database operations."""

    def setup_database(self):
        """Ensures all necessary tables exist."""
        tables = {
            "students": """
                CREATE TABLE IF NOT EXISTS students (
                    student_id INT AUTO_INCREMENT PRIMARY KEY,
                    first_name VARCHAR(50),
                    last_name VARCHAR(50),
                    grade_level INT,
                    email VARCHAR(100),
                    INDEX (first_name, last_name)
                )
            """,
            "teachers": """
                CREATE TABLE IF NOT EXISTS teachers (
                    teacher_id INT AUTO_INCREMENT PRIMARY KEY,
                    first_name VARCHAR(50),
                    last_name VARCHAR(50),
                    subject VARCHAR(50),
                    email VARCHAR(100),
                    INDEX (subject)
                )
            """,
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE,
                    password_hash VARCHAR(64),
                    email VARCHAR(100)
                )
            """,
            "attendance": """
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT,
                    attendance_date DATE,
                    status ENUM('Present', 'Absent', 'Late'),
                    FOREIGN KEY (student_id) REFERENCES students(student_id),
                    UNIQUE INDEX (student_id, attendance_date)
                )
            """
        }
        with self._get_cursor() as cursor:
            for table_name, ddl in tables.items():
                cursor.execute(ddl)

    def fetch_students(self) -> QueryResult:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT student_id, first_name, last_name, grade_level, email FROM students")
            return cursor.fetchall()

    def get_grade_distribution(self) -> QueryResult:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT grade_level, COUNT(*) as count FROM students GROUP BY grade_level ORDER BY grade_level")
            return cursor.fetchall()

    def fetch_teachers(self) -> QueryResult:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT teacher_id, first_name, last_name, subject, email FROM teachers")
            return cursor.fetchall()

    def fetch_teachers_by_subject(self, subject: str) -> QueryResult:
        with self._get_cursor(dictionary=True) as cursor:
            query = "SELECT teacher_id, first_name, last_name, subject, email FROM teachers WHERE subject LIKE %s"
            cursor.execute(query, (f"%{subject}%",))
            return cursor.fetchall()

    def fetch_student_by_name(self, first_name: str, last_name: str = "") -> QueryResult:
        with self._get_cursor(dictionary=True) as cursor:
            query = "SELECT student_id, first_name, last_name, grade_level, email FROM students WHERE first_name = %s"
            params = [first_name]
            if last_name:
                query += " AND last_name = %s"
                params.append(last_name)
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

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
            return cursor.rowcount > 0

    def delete_teacher(self, teacher_id: int) -> bool:
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
            return cursor.rowcount > 0

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

    def add_students_bulk(self, students: List[tuple]) -> bool:
        """Adds multiple student records in a single transaction for better performance."""
        with self._get_cursor() as cursor:
            query = "INSERT INTO students (first_name, last_name, grade_level, email) VALUES (%s, %s, %s, %s)"
            cursor.executemany(query, students)
            return True

    def add_user(self, username: str, password_hash: str, email: str) -> bool:
        with self._get_cursor() as cursor:
            query = "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, password_hash, email))
            return True

    def get_user_by_username(self, username: str) -> RowResult:
        with self._get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT username, password_hash, email FROM users WHERE username = %s", (username,))
            return cursor.fetchone()

    def record_attendance(self, student_id: int, date_str: str, status: str) -> bool:
        """Records or updates student attendance for a specific date (YYYY-MM-DD)."""
        with self._get_cursor() as cursor:
            query = """
                INSERT INTO attendance (student_id, attendance_date, status)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE status = VALUES(status)
            """
            cursor.execute(query, (student_id, date_str, status))
            return True

    def fetch_attendance_by_date(self, date_str: str) -> QueryResult:
        """Fetches attendance records for all students on a specific date."""
        with self._get_cursor(dictionary=True) as cursor:
            query = """
                SELECT a.attendance_id, s.student_id, s.first_name, s.last_name, a.status
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.attendance_date = %s
            """
            cursor.execute(query, (date_str,))
            return cursor.fetchall()

    def migrate_users(self) -> int:
        """Migrates users from users.json to the MySQL users table."""
        import json
        import os
        count = 0
        if not os.path.exists("users.json"):
            return count
            
        with open("users.json", "r") as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                return count

        for user in users:
            try:
                existing = self.get_user_by_username(user.get("username"))
                if not existing:
                    if self.add_user(user.get("username"), user.get("password_hash"), user.get("email", "")):
                        count += 1
            except DatabaseError:
                pass
        return count