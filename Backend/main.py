
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import date
from db import get_connection
import mysql.connector
import logging

app = FastAPI(
    title="University Student Management API",
    version="1.0.0",
    description="REST API for managing university student records."
)

logger = logging.getLogger(__name__)


# ==========================================
# PYDANTIC MODEL
# ==========================================

class StudentCreate(BaseModel):
    StudentFirstName: str = Field(min_length=1, max_length=100)
    StudentLastName: str = Field(min_length=1, max_length=100)
    DateOfBirth: date
    EnrollmentDate: date
    Email: EmailStr
    DepartmentID: int = Field(gt=0)


# ==========================================
# HOME ENDPOINT
# ==========================================

@app.get("/")
def home():
    return {
        "message": "University Management API is running"
    }


# ==========================================
# GET ALL STUDENTS
# ==========================================

@app.get("/students")
def get_students():

    try:
        connection = get_connection()
    except mysql.connector.Error:
        logger.exception("Database connection failed")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                StudentID,
                StudentFirstName,
                StudentLastName,
                Email,
                EnrollmentDate
            FROM students
            ORDER BY StudentID
        """

        cursor.execute(query)
        students = cursor.fetchall()

        return students

    except mysql.connector.Error:
        logger.exception("Failed to retrieve students")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve student records"
        )

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


# ==========================================
# CREATE NEW STUDENT
# ==========================================

@app.post("/students", status_code=201)
def create_student(student: StudentCreate):

    try:
        connection = get_connection()
    except mysql.connector.Error:
        logger.exception("Database connection failed")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    cursor = None

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO students
            (
                StudentFirstName,
                StudentLastName,
                DateOfBirth,
                EnrollmentDate,
                Email,
                DepartmentID
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            student.StudentFirstName,
            student.StudentLastName,
            student.DateOfBirth,
            student.EnrollmentDate,
            student.Email,
            student.DepartmentID
        )

        cursor.execute(query, values)
        new_student_id = cursor.lastrowid

        connection.commit()

        return {
            "message": "Student registered successfully",
            "StudentID": new_student_id
        }

    except mysql.connector.Error as error:
        connection.rollback()
        logger.exception("Failed to register student")

        if error.errno == 1062:
            raise HTTPException(
                status_code=409,
                detail="A student with this unique value already exists"
            )

        if error.errno == 1452:
            raise HTTPException(
                status_code=400,
                detail="DepartmentID does not reference an existing department"
            )

        raise HTTPException(
            status_code=500,
            detail="Unable to register student"
        )

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

# ==========================================
# GET STUDENT BY ID
# ==========================================

@app.get("/students/{student_id}")
def get_student(student_id: int):

    try:
        connection = get_connection()
    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT *
            FROM students
            WHERE StudentID = %s
        """

        cursor.execute(query, (student_id,))

        student = cursor.fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        return student

    except mysql.connector.Error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve student"
        )

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

# ==========================================
# UPDATE STUDENT BY ID
# ==========================================

@app.put("/students/{student_id}")
def update_student(student_id: int, student: StudentCreate):

    try:
        connection = get_connection()

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    cursor = None

    try:
        cursor = connection.cursor()

        # Check whether student exists
        cursor.execute(
            "SELECT StudentID FROM students WHERE StudentID = %s",
            (student_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        # Update the student's information
        query = """
            UPDATE students
            SET
                StudentFirstName = %s,
                StudentLastName = %s,
                DateOfBirth = %s,
                EnrollmentDate = %s,
                Email = %s,
                DepartmentID = %s
            WHERE StudentID = %s
        """

        values = (
            student.StudentFirstName,
            student.StudentLastName,
            student.DateOfBirth,
            student.EnrollmentDate,
            student.Email,
            student.DepartmentID,
            student_id
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "message": "Student updated successfully",
            "StudentID": student_id
        }

    except mysql.connector.Error as error:
        connection.rollback()

        if error.errno == 1062:
            raise HTTPException(
                status_code=409,
                detail="Email or another unique value already exists"
            )

        if error.errno == 1452:
            raise HTTPException(
                status_code=400,
                detail="Invalid DepartmentID"
            )

        raise HTTPException(
            status_code=500,
            detail="Unable to update student"
        )

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

# ==========================================
# DELETE STUDENT BY ID
# ==========================================

@app.delete("/students/{student_id}")
def delete_student(student_id: int):

    try:
        connection = get_connection()

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    cursor = None

    try:
        cursor = connection.cursor()

        # Check whether student exists
        cursor.execute(
            "SELECT StudentID FROM students WHERE StudentID = %s",
            (student_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )

        # Delete student
        cursor.execute(
            "DELETE FROM students WHERE StudentID = %s",
            (student_id,)
        )

        connection.commit()

        return {
            "message": "Student deleted successfully",
            "StudentID": student_id
        }

    except mysql.connector.Error as error:
        connection.rollback()

        if error.errno == 1451:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete student with existing enrollments"
            )

        raise HTTPException(
            status_code=500,
            detail="Unable to delete student"
        )

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()