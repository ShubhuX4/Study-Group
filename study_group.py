"""
study_group.py
--------------
Core logic of the project:
  * custom exceptions                      (Unit IV)
  * StudyGroup class                       (Unit II)
  * input validation with regex            (Unit III)
  * reading/writing JSON files             (Unit IV)
  * search/filter with lambda and filter() (Unit I)
  * a generator function                   (Unit II)
"""
import os
import re
import json
from datetime import datetime

from student import Student, GroupCreator, is_valid_email, is_valid_name

# ---------- File locations ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
REGISTRATIONS_FILE = os.path.join(DATA_DIR, "registrations.json")

# ---------- Constants (tuples / lists) ----------
SUBJECTS = ("Python", "Mathematics", "Physics", "Chemistry", "Data Science",
            "Machine Learning", "Web Development", "Computer Networks",
            "Database Systems", "Electronics", "Other")
MODES = ("Online", "Offline")
TIMINGS = ("Morning", "Afternoon", "Evening", "Night")
DAY_TYPES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


# ---------- Custom exceptions (Unit IV) ----------
class ValidationError(Exception):
    """Raised when form data is missing or invalid."""

    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or {}


class GroupNotFoundError(Exception):
    """Raised when a group id does not exist."""


class GroupFullError(Exception):
    """Raised when a group has no seats left."""


class DuplicateRegistrationError(Exception):
    """Raised when the same email tries to join a group twice."""


class NotMemberError(Exception):
    """Raised when someone tries to leave a group they are not in."""


class CreatorCannotLeaveError(Exception):
    """Raised when the creator tries to leave (they must delete the group instead)."""


class NotCreatorError(Exception):
    """Raised when someone other than the creator tries to delete a group."""


# ---------- StudyGroup class (Unit II) ----------
class StudyGroup:
    def __init__(self, group_id, name, subject, description, topics, day_type,
                 study_time, mode, max_members, creator_name, creator_email,
                 members=None, created_at=None):
        self.id = group_id
        self.name = name
        self.subject = subject
        self.description = description
        self.topics = topics                # list of strings
        self.day_type = day_type            # one day: "Monday" ... "Sunday"
        self.time = study_time              # "HH:MM"
        self.mode = mode
        self.max_members = max_members
        self.creator_name = creator_name
        self.creator_email = creator_email
        self._members = members if members is not None else []   # private list
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- members (encapsulation: outside code uses these methods) ---
    def get_members(self):
        return list(self._members)

    def member_count(self):
        return len(self._members)

    def seats_left(self):
        return self.max_members - len(self._members)

    def is_full(self):
        return self.seats_left() <= 0

    def has_member(self, email):
        email = email.strip().lower()
        for member in self._members:
            if member["email"] == email:
                return True
        return False

    def update_details(self, clean):
        """Change the editable details (members and creator stay the same)."""
        self.name = clean["name"]
        self.subject = clean["subject"]
        self.description = clean["description"]
        self.topics = clean["topics"]
        self.day_type = clean["day_type"]
        self.time = clean["time"]
        self.mode = clean["mode"]
        self.max_members = clean["max_members"]

    def remove_member(self, email):
        """Remove the member with this email from the group."""
        email = email.strip().lower()
        self._members = [m for m in self._members if m["email"] != email]

    def add_member(self, student):
        """Add a Student/GroupCreator object. Raises custom exceptions."""
        if self.has_member(student.email):
            raise DuplicateRegistrationError("This email is already registered in this group.")
        if self.is_full():
            raise GroupFullError("Sorry, this group is already full.")
        self._members.append(student.to_dict())

    # --- derived information ---
    def timing(self):
        """Morning / Afternoon / Evening / Night from the hour."""
        hour = int(self.time.split(":")[0])
        if hour < 12:
            return "Morning"
        elif hour < 17:
            return "Afternoon"
        elif hour < 21:
            return "Evening"
        return "Night"

    def status(self):
        return "Full" if self.is_full() else "Open"

    # --- conversion to dictionaries (for JSON) ---
    def to_dict(self):
        """Only the data that is saved in groups.json"""
        return {
            "id": self.id, "name": self.name, "subject": self.subject,
            "description": self.description, "topics": self.topics,
            "day_type": self.day_type, "time": self.time, "mode": self.mode,
            "max_members": self.max_members,
            "creator_name": self.creator_name, "creator_email": self.creator_email,
            "members": self.get_members(), "created_at": self.created_at,
        }

    def to_api_dict(self):
        """Saved data + calculated fields, sent to the frontend."""
        data = self.to_dict()
        data["member_count"] = self.member_count()
        data["seats_left"] = self.seats_left()
        data["timing"] = self.timing()
        data["status"] = self.status()
        return data

    @classmethod
    def from_dict(cls, d):
        return cls(d["id"], d["name"], d["subject"], d["description"], d["topics"],
                   d["day_type"], d["time"], d["mode"], d["max_members"],
                   d["creator_name"], d["creator_email"],
                   d.get("members", []), d.get("created_at"))


# ---------- JSON file handling (Unit IV) ----------
def read_json(path):
    """Read a JSON list from a file. Returns [] if file is missing or broken."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("Warning: invalid JSON in", path)
        return []


def write_json(path, data):
    """Write a list/dict to a JSON file."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
    except OSError as error:
        raise OSError(f"Could not save file: {error}")
    finally:
        print("write_json finished for", os.path.basename(path))


def load_groups():
    """Return a list of StudyGroup objects from groups.json"""
    return [StudyGroup.from_dict(item) for item in read_json(GROUPS_FILE)]


def save_groups(groups):
    write_json(GROUPS_FILE, [g.to_dict() for g in groups])


def load_registrations():
    return read_json(REGISTRATIONS_FILE)


def save_registrations(registrations):
    write_json(REGISTRATIONS_FILE, registrations)


# ---------- Validation (Unit III) ----------
def validate_group_data(data):
    """Check every field of the create-group form.
    Returns a clean dictionary or raises ValidationError."""
    errors = {}
    clean = {}

    name = str(data.get("name", "")).strip()
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9 .,&'#+()-]{2,59}$", name):
        errors["name"] = "Group name must be 3-60 characters (letters, numbers, basic symbols)."
    clean["name"] = name

    subject = str(data.get("subject", "")).strip()
    if subject not in SUBJECTS:
        errors["subject"] = "Please choose a valid subject."
    clean["subject"] = subject

    description = str(data.get("description", "")).strip()
    if len(description) < 10 or len(description) > 300:
        errors["description"] = "Description must be 10-300 characters."
    clean["description"] = description

    # topics can come as "a, b, c" or as a list
    raw_topics = data.get("topics", "")
    if isinstance(raw_topics, list):
        raw_topics = ",".join(str(t) for t in raw_topics)
    topics = [t.strip() for t in str(raw_topics).split(",") if t.strip()]
    if len(topics) == 0:
        errors["topics"] = "Enter at least one topic (separate topics with commas)."
    clean["topics"] = topics[:8]

    day_type = str(data.get("day_type", "")).strip()
    if day_type not in DAY_TYPES:
        errors["day_type"] = "Please choose a valid study day."
    clean["day_type"] = day_type

    study_time = str(data.get("time", "")).strip()
    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", study_time):
        errors["time"] = "Enter a valid time (HH:MM)."
    clean["time"] = study_time

    mode = str(data.get("mode", "")).strip()
    if mode not in MODES:
        errors["mode"] = "Mode must be Online or Offline."
    clean["mode"] = mode

    try:
        max_members = int(data.get("max_members"))
        if max_members < 2 or max_members > 50:
            errors["max_members"] = "Maximum members must be between 2 and 50."
    except (TypeError, ValueError):
        errors["max_members"] = "Maximum members must be a number."
        max_members = 0
    clean["max_members"] = max_members

    creator_name = str(data.get("creator_name", "")).strip()
    if not is_valid_name(creator_name):
        errors["creator_name"] = "Enter a valid name (letters only, 2-40 characters)."
    clean["creator_name"] = creator_name

    creator_email = str(data.get("creator_email", "")).strip().lower()
    if not is_valid_email(creator_email):
        errors["creator_email"] = "Enter a valid email address."
    clean["creator_email"] = creator_email

    if errors:
        raise ValidationError("Please fix the highlighted fields.", errors)
    return clean


def validate_student_data(data):
    """Check name + email for joining a group."""
    errors = {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    if not is_valid_name(name):
        errors["name"] = "Enter a valid name (letters only, 2-40 characters)."
    if not is_valid_email(email):
        errors["email"] = "Enter a valid email address."
    if errors:
        raise ValidationError("Please fix the highlighted fields.", errors)
    return name, email


# ---------- Main operations ----------
def find_group(groups, group_id):
    """Return the group with this id or raise GroupNotFoundError."""
    for group in groups:
        if group.id == group_id:
            return group
    raise GroupNotFoundError(f"Group {group_id} does not exist.")


def make_registration(registrations, group, person):
    """Build one registration record (dictionary)."""
    next_id = max([r["id"] for r in registrations], default=0) + 1
    return {
        "id": next_id, "group_id": group.id, "group_name": group.name,
        "name": person.name, "email": person.email, "role": person.role(),
        "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def create_group(data):
    """Validate, create and save a new group. Creator becomes first member."""
    clean = validate_group_data(data)
    groups = load_groups()
    registrations = load_registrations()

    new_id = max([g.id for g in groups], default=0) + 1
    group = StudyGroup(new_id, clean["name"], clean["subject"], clean["description"],
                       clean["topics"], clean["day_type"], clean["time"], clean["mode"],
                       clean["max_members"], clean["creator_name"], clean["creator_email"])

    creator = GroupCreator(clean["creator_name"], clean["creator_email"])
    group.add_member(creator)
    registrations.append(make_registration(registrations, group, creator))

    groups.append(group)
    save_groups(groups)
    save_registrations(registrations)
    return group


def join_group(group_id, data):
    """Register a student in an existing group."""
    name, email = validate_student_data(data)
    groups = load_groups()
    registrations = load_registrations()

    group = find_group(groups, group_id)       # may raise GroupNotFoundError
    student = Student(name, email)
    group.add_member(student)                  # may raise Duplicate / Full errors
    registrations.append(make_registration(registrations, group, student))

    save_groups(groups)
    save_registrations(registrations)
    return group


def search_groups(groups, search="", subject="", mode="", timing=""):
    """Filter groups using lambda functions and filter() (Unit I)."""
    search = search.strip().lower()
    result = groups
    if subject:
        result = list(filter(lambda g: g.subject == subject, result))
    if mode:
        result = list(filter(lambda g: g.mode == mode, result))
    if timing:
        result = list(filter(lambda g: g.timing() == timing, result))
    if search:
        result = list(filter(
            lambda g: search in g.name.lower() or search in g.subject.lower()
            or any(search in topic.lower() for topic in g.topics), result))
    return result


def update_group(group_id, data):
    """Edit a group. Only the creator (matching email) is allowed.
    Members and the creator's details are not changed."""
    email = str(data.get("email", "")).strip().lower()
    groups = load_groups()
    group = find_group(groups, group_id)                  # may raise GroupNotFoundError
    if group.creator_email != email:
        raise NotCreatorError("Only the creator of this group can edit it.")

    # reuse the same validation as "create", keeping the creator's details
    merged = dict(data)
    merged["creator_name"] = group.creator_name
    merged["creator_email"] = group.creator_email
    clean = validate_group_data(merged)

    if clean["max_members"] < group.member_count():
        raise ValidationError("Please fix the highlighted fields.", {
            "max_members": f"Cannot be less than the current members ({group.member_count()})."})

    group.update_details(clean)
    registrations = load_registrations()
    for record in registrations:                          # keep group name in sync
        if record["group_id"] == group_id:
            record["group_name"] = group.name
    save_groups(groups)
    save_registrations(registrations)
    return group


def leave_group(group_id, data):
    """A member leaves a group. The creator cannot leave (they delete instead)."""
    name, email = validate_student_data({"name": data.get("name", "Student"), "email": data.get("email", "")})
    groups = load_groups()
    group = find_group(groups, group_id)                  # may raise GroupNotFoundError
    if group.creator_email == email:
        raise CreatorCannotLeaveError("You created this group, so you cannot leave it. Delete it instead.")
    if not group.has_member(email):
        raise NotMemberError("You are not a member of this group.")

    group.remove_member(email)
    registrations = [r for r in load_registrations()
                     if not (r["group_id"] == group_id and r["email"] == email)]
    save_groups(groups)
    save_registrations(registrations)
    return group


def delete_group(group_id, email):
    """Delete a group. Only the creator (matching email) is allowed.
    Also removes that group's registrations."""
    email = str(email).strip().lower()
    groups = load_groups()
    group = find_group(groups, group_id)               # may raise GroupNotFoundError
    if group.creator_email != email:
        raise NotCreatorError("Only the creator of this group can delete it.")

    groups = [g for g in groups if g.id != group_id]
    registrations = [r for r in load_registrations() if r["group_id"] != group_id]
    save_groups(groups)
    save_registrations(registrations)
    return group


def get_my_groups(email):
    """All groups where this email is the creator or a member."""
    email = email.strip().lower()
    mine = []
    for group in load_groups():
        if group.has_member(email):
            item = group.to_api_dict()
            item["my_role"] = "Creator" if group.creator_email == email else "Member"
            mine.append(item)
    return mine


def open_groups(groups):
    """Generator (Unit II): gives groups one by one, only those with free seats."""
    for group in groups:
        if not group.is_full():
            yield group
