"""
student.py
----------
Unit II (OOP): classes, constructors, inheritance, polymorphism,
encapsulation and abstraction.
Unit III: regular expressions for input validation.
"""
import re

# ---------- Regular expressions (Unit III) ----------
EMAIL_PATTERN = r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$"
NAME_PATTERN = r"^[A-Za-z][A-Za-z .'-]{1,39}$"


def is_valid_email(email):
    """Return True if the email looks like name@domain.com"""
    return re.match(EMAIL_PATTERN, email) is not None


def is_valid_name(name):
    """Name: 2-40 characters, letters, spaces, dots, apostrophes, hyphens."""
    return re.match(NAME_PATTERN, name) is not None


# ---------- Classes (Unit II) ----------
class Person:
    """Base class. Name and email are 'private' (encapsulation):
    they are stored with an underscore and read through properties."""

    def __init__(self, name, email):  # constructor
        self._name = name.strip()
        self._email = email.strip().lower()

    @property
    def name(self):
        return self._name

    @property
    def email(self):
        return self._email

    def role(self):
        # Abstraction: every child class MUST provide its own role()
        raise NotImplementedError("Child class must define role()")

    def describe(self):
        return f"{self._name} ({self._email}) - {self.role()}"

    def to_dict(self):
        return {"name": self._name, "email": self._email}


class Student(Person):
    """A student who joins a study group (inheritance from Person)."""

    def role(self):  # polymorphism: same method name, different result
        return "Member"


class GroupCreator(Person):
    """The student who created the group (inheritance from Person)."""

    def role(self):  # polymorphism
        return "Creator"
