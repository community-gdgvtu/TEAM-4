import csv
import random
from pathlib import Path
from faker import Faker

fake = Faker()
random.seed(42)

BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# CONFIGURATION
# ============================================================

NUM_STUDENTS = 500
NUM_PROJECTS = 1000
NUM_COMMITS = 5000
NUM_ASSESSMENTS = 1500

# ============================================================
# MASTER DATA
# ============================================================

institutions = [
    ["INS001", "S.G. Balekundri Institute of Technology", "India"],
    ["INS002", "RV College of Engineering", "India"],
    ["INS003", "PES University", "India"],
    ["INS004", "Indian Institute of Technology Bombay", "India"],
    ["INS005", "Indian Institute of Technology Delhi", "India"],
]

skills = [
    ["SK001", "Python", "Programming"],
    ["SK002", "Java", "Programming"],
    ["SK003", "JavaScript", "Programming"],
    ["SK004", "React", "Frontend"],
    ["SK005", "Node.js", "Backend"],
    ["SK006", "SQL", "Database"],
    ["SK007", "Machine Learning", "AI/ML"],
    ["SK008", "Data Science", "AI/ML"],
    ["SK009", "FastAPI", "Backend"],
    ["SK010", "Git", "Tools"],
    ["SK011", "Docker", "DevOps"],
    ["SK012", "C++", "Programming"],
    ["SK013", "HTML/CSS", "Frontend"],
    ["SK014", "MongoDB", "Database"],
    ["SK015", "Firebase", "Backend"],
]

skill_names = [x[1] for x in skills]

courses = [
    ["CRS001", "Python Programming", "Python"],
    ["CRS002", "Object Oriented Programming", "Java"],
    ["CRS003", "Web Development", "JavaScript"],
    ["CRS004", "Frontend Development", "React"],
    ["CRS005", "Backend Development", "Node.js"],
    ["CRS006", "Database Management Systems", "SQL"],
    ["CRS007", "Machine Learning", "Machine Learning"],
    ["CRS008", "Data Analytics", "Data Science"],
    ["CRS009", "API Development", "FastAPI"],
    ["CRS010", "Software Engineering", "Git"],
    ["CRS011", "Cloud Computing", "Docker"],
    ["CRS012", "Advanced Programming", "C++"],
    ["CRS013", "UI Development", "HTML/CSS"],
    ["CRS014", "NoSQL Databases", "MongoDB"],
    ["CRS015", "Cloud Application Development", "Firebase"],
]

languages = [
    "Python",
    "JavaScript",
    "Java",
    "C++",
    "TypeScript",
    "HTML",
    "CSS",
]

project_templates = [
    ("AI Resume Analyzer", ["Python", "FastAPI", "Machine Learning"]),
    ("E-Commerce Platform", ["JavaScript", "React", "Node.js", "SQL"]),
    ("Student Management System", ["Java", "SQL"]),
    ("Data Analytics Dashboard", ["Python", "Data Science", "SQL"]),
    ("Food Delivery Application", ["React", "Node.js", "MongoDB"]),
    ("Face Recognition System", ["Python", "Machine Learning"]),
    ("Hospital Management System", ["Java", "SQL"]),
    ("Smart Attendance System", ["Python", "Firebase"]),
    ("Portfolio Website", ["HTML/CSS", "JavaScript"]),
    ("Cloud File Manager", ["React", "Firebase"]),
    ("AI Chatbot", ["Python", "FastAPI", "Machine Learning"]),
    ("Expense Tracker", ["React", "Node.js", "MongoDB"]),
    ("Recommendation System", ["Python", "Machine Learning", "Data Science"]),
    ("Online Examination System", ["Java", "SQL"]),
    ("DevOps Deployment Platform", ["Docker", "Git", "Node.js"]),
]

job_templates = [
    ("JOB001", "Python Backend Developer",
     ["Python", "FastAPI", "SQL", "Git"]),
    ("JOB002", "Frontend Developer",
     ["JavaScript", "React", "HTML/CSS", "Git"]),
    ("JOB003", "Full Stack Developer",
     ["JavaScript", "React", "Node.js", "SQL", "Git"]),
    ("JOB004", "Machine Learning Engineer",
     ["Python", "Machine Learning", "Data Science"]),
    ("JOB005", "Data Analyst",
     ["Python", "SQL", "Data Science"]),
    ("JOB006", "Java Developer",
     ["Java", "SQL", "Git"]),
    ("JOB007", "Cloud Developer",
     ["Docker", "Firebase", "Git"]),
    ("JOB008", "AI Engineer",
     ["Python", "Machine Learning", "FastAPI"]),
]

# ============================================================
# HELPERS
# ============================================================

def write_csv(filename, headers, rows):
    path = BASE_DIR / filename

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Created {filename}: {len(rows)} records")


# ============================================================
# STUDENTS
# ============================================================

students = []

for i in range(1, NUM_STUDENTS + 1):

    student_id = f"STU{i:04d}"

    name = fake.name()

    institution = random.choice(institutions)

    department = random.choice([
        "Computer Science",
        "Information Science",
        "Artificial Intelligence",
        "Data Science",
        "Electronics"
    ])

    year = random.choice([2, 3, 4])

    students.append([
        student_id,
        name,
        institution[0],
        department,
        year,
        round(random.uniform(6.2, 9.8), 2),
        fake.email()
    ])

write_csv(
    "students.csv",
    [
        "student_id",
        "name",
        "institution_id",
        "department",
        "year",
        "cgpa",
        "email"
    ],
    students
)

# ============================================================
# INSTITUTIONS
# ============================================================

write_csv(
    "institutions.csv",
    ["institution_id", "institution_name", "country"],
    institutions
)

# ============================================================
# SKILLS
# ============================================================

write_csv(
    "skills.csv",
    ["skill_id", "skill_name", "category"],
    skills
)

# ============================================================
# COURSES
# ============================================================

write_csv(
    "courses.csv",
    ["course_id", "course_name", "primary_skill"],
    courses
)

# ============================================================
# STUDENT COURSES
# ============================================================

student_courses = []

for student in students:

    selected_courses = random.sample(
        courses,
        random.randint(5, 10)
    )

    for course in selected_courses:

        marks = random.randint(55, 98)

        if marks >= 85:
            grade = "A"
        elif marks >= 75:
            grade = "B+"
        elif marks >= 65:
            grade = "B"
        else:
            grade = "C"

        student_courses.append([
            student[0],
            course[0],
            marks,
            grade
        ])

write_csv(
    "student_courses.csv",
    [
        "student_id",
        "course_id",
        "marks",
        "grade"
    ],
    student_courses
)

# ============================================================
# GITHUB PROJECTS
# ============================================================

github_projects = []

for i in range(1, NUM_PROJECTS + 1):

    student = random.choice(students)

    project_name, technologies = random.choice(project_templates)

    github_projects.append([
        f"PRJ{i:05d}",
        student[0],
        project_name,
        random.choice([
            "academic",
            "personal",
            "hackathon",
            "internship"
        ]),
        random.randint(5, 150),
        random.randint(1, 20),
        random.choice(["beginner", "intermediate", "advanced"]),
        ", ".join(technologies),
        fake.sentence(nb_words=20)
    ])

write_csv(
    "github_projects.csv",
    [
        "project_id",
        "student_id",
        "project_name",
        "project_type",
        "stars",
        "contributors",
        "complexity",
        "technologies",
        "description"
    ],
    github_projects
)

# ============================================================
# GITHUB COMMITS
# ============================================================

github_commits = []

for i in range(1, NUM_COMMITS + 1):

    project = random.choice(github_projects)

    github_commits.append([
        f"COM{i:06d}",
        project[0],
        project[1],
        random.choice([
            "feature",
            "bugfix",
            "refactor",
            "documentation",
            "testing",
            "deployment"
        ]),
        random.randint(2, 150),
        random.randint(1, 500),
        fake.date_between(start_date="-2y", end_date="today")
    ])

write_csv(
    "github_commits.csv",
    [
        "commit_id",
        "project_id",
        "student_id",
        "commit_type",
        "files_changed",
        "lines_changed",
        "commit_date"
    ],
    github_commits
)

# ============================================================
# GITHUB LANGUAGES
# ============================================================

github_languages = []

for project in github_projects:

    technologies = project[7].split(", ")

    for technology in technologies:

        github_languages.append([
            project[0],
            project[1],
            technology,
            random.randint(10, 100)
        ])

write_csv(
    "github_languages.csv",
    [
        "project_id",
        "student_id",
        "language_or_technology",
        "usage_percentage"
    ],
    github_languages
)

# ============================================================
# ASSESSMENTS
# ============================================================

assessment_results = []

for i in range(1, NUM_ASSESSMENTS + 1):

    student = random.choice(students)
    skill = random.choice(skill_names)

    knowledge = random.randint(40, 100)
    problem_solving = random.randint(40, 100)
    coding = random.randint(40, 100)

    final_score = round(
        knowledge * 0.3 +
        problem_solving * 0.3 +
        coding * 0.4,
        2
    )

    if final_score >= 85:
        proficiency = "Advanced"
    elif final_score >= 70:
        proficiency = "Intermediate"
    elif final_score >= 50:
        proficiency = "Beginner"
    else:
        proficiency = "Not Verified"

    assessment_results.append([
        f"ASM{i:05d}",
        student[0],
        skill,
        knowledge,
        problem_solving,
        coding,
        final_score,
        proficiency,
        random.choice([
            "proctored",
            "practice"
        ])
    ])

write_csv(
    "assessment_results.csv",
    [
        "assessment_id",
        "student_id",
        "skill",
        "knowledge_score",
        "problem_solving_score",
        "coding_score",
        "final_score",
        "proficiency",
        "assessment_type"
    ],
    assessment_results
)

# ============================================================
# JOBS
# ============================================================

jobs = []

for job_id, title, required_skills in job_templates:

    jobs.append([
        job_id,
        title,
        ", ".join(required_skills),
        random.randint(400000, 1800000),
        random.choice([
            "India",
            "Germany",
            "Canada",
            "Japan",
            "UAE"
        ])
    ])

write_csv(
    "jobs.csv",
    [
        "job_id",
        "job_title",
        "required_skills",
        "salary",
        "country"
    ],
    jobs
)

# ============================================================
# SUMMARY
# ============================================================

print("\n===================================")
print("SkillPassport Dataset Generated")
print("===================================")
print(f"Students          : {len(students)}")
print(f"Institutions      : {len(institutions)}")
print(f"Courses           : {len(courses)}")
print(f"Student Courses   : {len(student_courses)}")
print(f"Projects          : {len(github_projects)}")
print(f"Commits           : {len(github_commits)}")
print(f"GitHub Languages  : {len(github_languages)}")
print(f"Assessments       : {len(assessment_results)}")
print(f"Jobs              : {len(jobs)}")
print("===================================")