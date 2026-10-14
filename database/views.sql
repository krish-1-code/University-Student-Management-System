-- ========================================
-- FEATURE : ADVANCED SQL: VIEWS
-- ========================================

-- A VIEW IS A STORED SQL QUERY THAT BEHAVES LIKE A VIRTUAL TABLE.

CREATE OR REPLACE VIEW StudentEnrollmentView AS

SELECT
    s.StudentID,
    CONCAT(
        s.StudentFirstName,
        ' ',
        s.StudentLastName
    ) AS StudentName,
    c.CourseName,
    e.Semester,
    e.Grade

FROM students s

JOIN enrollments e
    ON s.StudentID = e.StudentID

JOIN courses c
    ON e.CourseID = c.CourseID;


-- NOW WE CAN RETREIVE INFORMATION USING:

SELECT *
FROM StudentEnrollmentView;