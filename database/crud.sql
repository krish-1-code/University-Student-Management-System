USE universitydatabase;

-- ========================================
-- CRUD FEATURE 1: CREATE - REGISTER A NEW STUDENT
-- ========================================

INSERT INTO students
(StudentFirstName, StudentLastName,
 DateOfBirth, EnrollmentDate,
 Email, DepartmentID)
VALUES
('John', 'Williams', '2006-05-20',
 '2026-08-20', 'john.williams@example.com', 1);

-- ========================================
-- CRUD FEATURE 2: RETRIEVE - FIND STUDENT BY EMAIL
-- ========================================

SELECT *
FROM students
WHERE Email = 'john.williams@example.com';


-- ========================================
-- CRUD FEATURE 3: UPDATE - CHANGE STUDENT'S BY DEPARTMENT
-- ========================================

UPDATE students
SET DepartmentID = 2
WHERE Email = 'john.williams@example.com';

-- ========================================
-- CRUD FEATURE 4: DELETE - REMOVE A STUDENT'S ENROLLMENT
-- ========================================

DELETE FROM enrollments
WHERE EnrollmentID = 10;
