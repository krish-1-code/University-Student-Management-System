"""CRUD API for database/Schema.sql. Run: uvicorn main:app --reload."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import logging
from typing import Annotated

import mysql.connector
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, ConfigDict, EmailStr, Field

if __package__:
    from .db import get_connection
else:
    from db import get_connection

app = FastAPI(
    title="University Student Management API",
    version="1.0.0",
    description="REST API for students, courses, departments, professors, and enrollments.",
)
logger = logging.getLogger(__name__)
RecordID = Annotated[int, Path(gt=0)]


# Fields use database column names and limits. PUT replaces all editable fields;
# omitted optional fields become NULL. Student requirements remain unchanged.
class RecordCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class StudentCreate(RecordCreate):
    StudentFirstName: str = Field(min_length=1, max_length=100)
    StudentLastName: str = Field(min_length=1, max_length=100)
    DateOfBirth: date
    EnrollmentDate: date
    Email: EmailStr = Field(max_length=100)
    DepartmentID: int = Field(gt=0)


class CourseCreate(RecordCreate):
    CourseName: str = Field(min_length=1, max_length=100)
    Credits: int = Field(ge=1, le=6)
    DepartmentID: int | None = Field(default=None, gt=0)
    ProfessorID: int | None = Field(default=None, gt=0)


class DepartmentCreate(RecordCreate):
    DepartmentName: str = Field(min_length=1, max_length=100)


class ProfessorCreate(RecordCreate):
    FirstName: str = Field(min_length=1, max_length=50)
    LastName: str = Field(min_length=1, max_length=50)
    Email: EmailStr = Field(max_length=100)
    DepartmentID: int | None = Field(default=None, gt=0)


class EnrollmentCreate(RecordCreate):
    StudentID: int = Field(gt=0)
    CourseID: int = Field(gt=0)
    Semester: str = Field(min_length=1, max_length=20)
    Grade: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2,
    )


# Identifiers come only from fixed metadata and validated model fields.
RESOURCES = {
    "students": ("students", "StudentID", "Student"),
    "courses": ("courses", "CourseID", "Course"),
    "departments": ("department", "DepartmentID", "Department"),
    "professors": ("professors", "ProfessorID", "Professor"),
    "enrollments": ("enrollments", "EnrollmentID", "Enrollment"),
}
REFERENCE_ERRORS = {
    "students": "DepartmentID does not reference an existing department",
    "courses": "DepartmentID or ProfessorID does not reference an existing record",
    "professors": "DepartmentID does not reference an existing department",
    "enrollments": "StudentID or CourseID does not reference an existing record",
}
DELETE_ERRORS = {
    "students": "Cannot delete student with existing enrollments",
    "courses": "Cannot delete course with existing enrollments",
    "departments": "Cannot delete department with existing students, courses, or professors",
    "professors": "Cannot delete professor with existing courses",
}


@contextmanager
def database(resource: str, *, write: bool = False):
    """Manage connections, transactions, and safe database error responses."""
    try:
        connection = get_connection()
    except mysql.connector.Error as error:
        logger.exception("Database connection failed")
        raise HTTPException(503, "Database connection unavailable") from error

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True, buffered=True)
        yield cursor
        if write:
            connection.commit()
    except Exception as error:
        if write:
            try:
                connection.rollback()
            except mysql.connector.Error:
                logger.exception("Database rollback failed")

        if not isinstance(error, mysql.connector.Error):
            raise

        logger.exception("Database operation failed for %s", resource)
        if error.errno == 1062:
            detail = (
                "Student is already enrolled in this course for this semester"
                if resource == "enrollments"
                else f"{RESOURCES[resource][2]} with this unique value already exists"
            )
            raise HTTPException(409, detail) from error
        if error.errno == 1452:
            raise HTTPException(400, REFERENCE_ERRORS.get(resource, "Invalid reference")) from error
        if error.errno == 1451:
            raise HTTPException(
                409, DELETE_ERRORS.get(resource, "Record is referenced by other records"),
            ) from error
        if error.errno in (1048, 1264, 1406, 3819):
            raise HTTPException(400, "Values violate a database constraint") from error
        raise HTTPException(500, "Unable to complete database operation") from error
    finally:
        # A cursor cleanup failure must not skip closing the connection or
        # hide the original response.
        try:
            if cursor is not None:
                cursor.close()
        except mysql.connector.Error:
            logger.exception("Failed to close database cursor")
        finally:
            try:
                connection.close()
            except mysql.connector.Error:
                logger.exception("Failed to close database connection")


def list_records(resource: str):
    table, key, _ = RESOURCES[resource]
    # Preserve the existing student-directory response.
    columns = (
        "StudentID, StudentFirstName, StudentLastName, Email, EnrollmentDate"
        if resource == "students" else "*"
    )
    with database(resource) as cursor:
        cursor.execute(f"SELECT {columns} FROM {table} ORDER BY {key}")
        return cursor.fetchall()


def read_record(resource: str, record_id: int):
    table, key, label = RESOURCES[resource]
    with database(resource) as cursor:
        cursor.execute(f"SELECT * FROM {table} WHERE {key} = %s", (record_id,))
        record = cursor.fetchone()
        if record is None:
            raise HTTPException(404, f"{label} not found")
        return record


def insert_record(resource: str, record: RecordCreate):
    table, key, label = RESOURCES[resource]
    values = record.model_dump()
    columns = ", ".join(values)
    placeholders = ", ".join("%s" for _ in values)
    with database(resource, write=True) as cursor:
        cursor.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(values.values()),
        )
        record_id = cursor.lastrowid
    message = (
        "Student registered successfully" if resource == "students"
        else f"{label} created successfully"
    )
    return {"message": message, key: record_id}


def replace_record(resource: str, record_id: int, record: RecordCreate):
    table, key, label = RESOURCES[resource]
    values = record.model_dump()
    assignments = ", ".join(f"{column} = %s" for column in values)
    with database(resource, write=True) as cursor:
        # MySQL may report zero changed rows for an identical update. Check
        # existence separately and lock the record for the transaction.
        cursor.execute(
            f"SELECT {key} FROM {table} WHERE {key} = %s FOR UPDATE", (record_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(404, f"{label} not found")
        cursor.execute(
            f"UPDATE {table} SET {assignments} WHERE {key} = %s",
            (*values.values(), record_id),
        )
    return {"message": f"{label} updated successfully", key: record_id}


def remove_record(resource: str, record_id: int):
    table, key, label = RESOURCES[resource]
    with database(resource, write=True) as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE {key} = %s", (record_id,))
        if cursor.rowcount == 0:
            raise HTTPException(404, f"{label} not found")
    return {"message": f"{label} deleted successfully", key: record_id}


@app.get("/")
def home():
    return {"message": "University Management API is running"}


# Students
@app.get("/students", tags=["Students"])
def get_students():
    return list_records("students")


@app.post("/students", status_code=201, tags=["Students"])
def create_student(student: StudentCreate):
    return insert_record("students", student)


@app.get("/students/{student_id}", tags=["Students"])
def get_student(student_id: RecordID):
    return read_record("students", student_id)


@app.put("/students/{student_id}", tags=["Students"])
def update_student(student_id: RecordID, student: StudentCreate):
    return replace_record("students", student_id, student)


@app.delete("/students/{student_id}", tags=["Students"])
def delete_student(student_id: RecordID):
    return remove_record("students", student_id)


# Courses
@app.get("/courses", tags=["Courses"])
def get_courses():
    return list_records("courses")


@app.post("/courses", status_code=201, tags=["Courses"])
def create_course(course: CourseCreate):
    return insert_record("courses", course)


@app.get("/courses/{course_id}", tags=["Courses"])
def get_course(course_id: RecordID):
    return read_record("courses", course_id)


@app.put("/courses/{course_id}", tags=["Courses"])
def update_course(course_id: RecordID, course: CourseCreate):
    return replace_record("courses", course_id, course)


@app.delete("/courses/{course_id}", tags=["Courses"])
def delete_course(course_id: RecordID):
    return remove_record("courses", course_id)


# Departments
# The API uses /departments; the SQL table is department (singular).
@app.get("/departments", tags=["Departments"])
def get_departments():
    return list_records("departments")


@app.post("/departments", status_code=201, tags=["Departments"])
def create_department(department: DepartmentCreate):
    return insert_record("departments", department)


@app.get("/departments/{department_id}", tags=["Departments"])
def get_department(department_id: RecordID):
    return read_record("departments", department_id)


@app.put("/departments/{department_id}", tags=["Departments"])
def update_department(department_id: RecordID, department: DepartmentCreate):
    return replace_record("departments", department_id, department)


@app.delete("/departments/{department_id}", tags=["Departments"])
def delete_department(department_id: RecordID):
    return remove_record("departments", department_id)


# Professors
@app.get("/professors", tags=["Professors"])
def get_professors():
    return list_records("professors")


@app.post("/professors", status_code=201, tags=["Professors"])
def create_professor(professor: ProfessorCreate):
    return insert_record("professors", professor)


@app.get("/professors/{professor_id}", tags=["Professors"])
def get_professor(professor_id: RecordID):
    return read_record("professors", professor_id)


@app.put("/professors/{professor_id}", tags=["Professors"])
def update_professor(professor_id: RecordID, professor: ProfessorCreate):
    return replace_record("professors", professor_id, professor)


@app.delete("/professors/{professor_id}", tags=["Professors"])
def delete_professor(professor_id: RecordID):
    return remove_record("professors", professor_id)


# Enrollments
@app.get("/enrollments", tags=["Enrollments"])
def get_enrollments():
    return list_records("enrollments")


@app.post("/enrollments", status_code=201, tags=["Enrollments"])
def create_enrollment(enrollment: EnrollmentCreate):
    return insert_record("enrollments", enrollment)


@app.get("/enrollments/{enrollment_id}", tags=["Enrollments"])
def get_enrollment(enrollment_id: RecordID):
    return read_record("enrollments", enrollment_id)


@app.put("/enrollments/{enrollment_id}", tags=["Enrollments"])
def update_enrollment(enrollment_id: RecordID, enrollment: EnrollmentCreate):
    return replace_record("enrollments", enrollment_id, enrollment)


@app.delete("/enrollments/{enrollment_id}", tags=["Enrollments"])
def delete_enrollment(enrollment_id: RecordID):
    return remove_record("enrollments", enrollment_id)
