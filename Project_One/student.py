from dataclasses import dataclass, asdict

@dataclass
class Student:
    """Data class representing a Student record."""
    student_id: int
    first_name: str
    last_name: str
    grade_level: int
    email: str

    @property
    def full_name(self) -> str:
        """Returns the combined first and last name."""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> dict:
        """Converts the instance to a dictionary."""
        return asdict(self)


@dataclass
class Teacher:
    """Data class representing a Teacher record."""
    teacher_id: int
    first_name: str
    last_name: str
    subject: str
    email: str

    @property
    def full_name(self) -> str:
        """Returns the combined first and last name."""
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> dict:
        """Converts the instance to a dictionary."""
        return asdict(self)