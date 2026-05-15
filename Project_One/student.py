class Student:
    """Data class representing a Student record."""
    def __init__(self, student_id, first_name, last_name, grade_level, email):
        self.student_id = student_id
        self.first_name = first_name
        self.last_name = last_name
        self.grade_level = grade_level
        self.email = email


class Teacher:
    """Data class representing a Teacher record."""
    def __init__(self, teacher_id, first_name, last_name, subject, email):
        self.teacher_id = teacher_id
        self.first_name = first_name
        self.last_name = last_name
        self.subject = subject
        self.email = email