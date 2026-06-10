# Dataclasses provide a concise way to create classes that primarily store data
from dataclasses import dataclass, asdict

@dataclass
class Person:
    """Base class for common person attributes."""
    first_name: str
    last_name: str
    email: str

    @property
    def full_name(self) -> str:
        """Returns the combined first and last name."""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> dict:
        """Converts the instance to a dictionary."""
        return asdict(self)

@dataclass
class Student(Person):
    """Schema for a Student record matching the database structure."""
    student_id: int
    grade_level: int

@dataclass
class Teacher(Person):
    """Schema for a Teacher record matching the database structure."""
    teacher_id: int
    subject: str