USE universitydatabase;

-- ========================================
-- FEATURE 1: STUDENT DIRECTORY
-- ========================================

-- Retrieve all students alphabetically

SELECT
    StudentID,
    StudentFirstName,
    StudentLastName,
    Email,
    EnrollmentDate
FROM students
ORDER BY StudentLastName ASC;

-- ========================================
-- FEATURE 2: STUDENT ENROLLMENT REPORT
-- ========================================

-- Retrieve students and their enrolled courses

SELECT
    s.StudentID,
    s.StudentFirstName,
    s.StudentLastName,
    c.CourseName,
    e.Semester,
    e.Grade
FROM students s
INNER JOIN enrollments e
    ON s.StudentID = e.StudentID
INNER JOIN courses c
    ON e.CourseID = c.CourseID
ORDER BY s.StudentID;

-- ========================================
-- FEATURE 3: CALCULATE AVERAGE STUDENT GRADES
-- ========================================

SELECT
    s.StudentID,
    s.StudentFirstName,
    s.StudentLastName,
    ROUND(AVG(e.Grade), 2) AS AverageGrade
FROM students s

LEFT JOIN enrollments e
    ON s.StudentID = e.StudentID

GROUP BY
    s.StudentID,
    s.StudentFirstName,
    s.StudentLastName

ORDER BY AverageGrade DESC;

-- ========================================
-- FEATURE 4: COURSE ENROLLMENT STATISTICS
-- ========================================

SELECT
    c.CourseID,
    c.CourseName,
    COUNT(e.EnrollmentID) AS TotalStudents
FROM courses c

LEFT JOIN enrollments e
    ON c.CourseID = e.CourseID

GROUP BY
    c.CourseID,
    c.CourseName

ORDER BY TotalStudents DESC;
