from fastapi import FastAPI, Query, Path, Depends, HTTPException
import os 
from dotenv import load_dotenv
load_dotenv()

# step 1 - db url setup
DATABASE_URL = os.getenv("DATABASE_URL")

# step 2 - engine
from sqlalchemy import create_engine, text,Column, Integer, String
from sqlalchemy.exc import IntegrityError

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    version = conn.execute(text("SELECT version()")).scalar()
    print(f"Connected to {version.split(",")[0]}")

# step 3 - create SessionLocal and Base
from sqlalchemy.orm import sessionmaker, DeclarativeBase
SessionLocal = sessionmaker(bind=engine)

# db = SessionLocal()


class Base(DeclarativeBase):
    pass

# step 4 - create studentDB
class StudentDB(Base):
    __tablename__ = "student_records"
    id         = Column(String, primary_key=True)
    name       = Column(String(50), nullable=False)    
    age        = Column(Integer, nullable=False) 
    marks      = Column(Integer, nullable=False) 
    email = Column(String(255), unique=True, nullable=True)
    course     = Column(String(50), nullable=False) 

Base.metadata.create_all(bind = engine)
print("Table Ready...")

# step 5 - Pydantic schemas for input(StudentCreate, StudentUpdate)
from pydantic import EmailStr, BaseModel, Field, field_validator, computed_field, ConfigDict

class StudentCreate(BaseModel):
    id : str = Field(..., examples=["S001"])
    name : str = Field(..., min_length=2, max_length=50)
    age: int = Field(..., gt = 0, le = 100)
    email : EmailStr
    course : str = Field(..., max_length = 50)
    marks : int = Field(..., ge = 0, le = 100)

    @field_validator("name")
    @classmethod
    def check_name(cls, name):
        if not name.replace (" ", "").isalpha():
            raise ValueError("Name must contain only letters and spaces")

        return name.title()

class StudentUpdate(BaseModel):
    name : str | None = Field(None, min_length = 2, max_length = 50)
    age : int | None = Field(None, gt = 0, lt= 100)
    course : str | None = Field(None, max_length=50)
    marks : int | None = Field(None, ge = 0, le = 100)
    email : EmailStr | None = None

    @field_validator("name")
    @classmethod
    def check_name(cls, name):
        if not name.replace (" ", "").isalpha():
            raise ValueError("Name must contain only letters and spaces")
    
        return name.title()

# step 6 - Pydantic schemas for output(StudentResponse, StudentPage, message)

class StudentResponse(StudentCreate):
    # from_attributes = True lets pydantic read student.marks (an object) not only
    model_config = ConfigDict(from_attributes=True)
    # (marks = 80)
    @computed_field
    @property

    def grade(self) -> str:
        if self.marks >= 90:
            return "A+"
        elif self.marks >= 80:
            return "A"
        elif self.marks >= 70:
            return "B"
        elif self.marks >= 60:
            return "C"
        else:
            return "F"




# step 7 - get_db() - one session per request
# opens a session, gives it to endpoint, always closes it, replaces load_data/save_data

# opens a session, pauses at yield while endpoint does its work and 
# once the endpoint completed it's work the session will be closed
def get_db():
    db = SessionLocal()
    try:
        yield db
    # except:

    finally:
        db.close()

# step 8 - Create the FastAPI app
from sqlalchemy.orm import Session

app = FastAPI()

# GET one student
# Depends(get_db) means : before running this endpoint, run the get_db() function
@app.get('/student/{student_id}', response_model = StudentResponse, tags = ['GET ROUTE'])
def get_student(
    student_id : str = Path(..., description = "The id of the student"),
    db : Session = Depends(get_db)
):
    student = db.get(StudentDB, student_id) # select ... where id = "S001"
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student with Id {student_id} not found")

    return student

# step 10 - POST - create a student
@app.post('/create_student', response_model=StudentResponse, status_code=201, tags = ['POST ROUTE'])
def create_student(
    student : StudentCreate,
    db : Session = Depends(get_db)):

    if db.get(StudentDB, student.id):
        raise HTTPException(status_code=400, detail = f"Student with ID {student.id} already exists")
    new_student = StudentDB(**student.model_dump())

    db.add(new_student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Email {student.email} already used by another student")

    db.refresh(new_student)

    return new_student
# step 11 - PUT - update a student

@app.put('/UpdateStudent/{student_id}', tags = ["PUT ROUTE"])
def update_student(
    student_update : StudentUpdate,
    student_id : str = Path(..., description="The ID of the student", examples="S001"),
    db : Session = Depends(get_db)
):
    student = db.get(StudentDB, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail = f"Student with the ID {student_id} does not exist")

    changes = student_update.model_dump(exclude_unset=True) # only fields sent eg. course = python

    for key, value in changes.items():
        setattr(student, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Email {student.email} already used by another student")
    
    db.refresh(student)
    
    return student
# step 12 - DELETE - remove a student
@app.delete('/DeleteStudent/{student_id}', tags = ["DELETE ROUTE"])
def Delete_Student(student_id : str = Path(..., description="The id of the student"),
                  db : Session = Depends(get_db)):
    student = db.get(StudentDB, student_id)
    if student is None:
        raise HTTPException(
            status_code= 404,
            detail = f"Student with ID {student_id} not found"
        )

    db.delete(student)
    db.commit()
    return {"message": f"{student_id} deleted successfully"}


# step 13 - GET all students(filter + sort + paginate)
from sqlalchemy import func
SORT_FIELDS = ["marks", "age", "name"]
SORT_ORDER = ["asc", "desc"]

@app.get('/students', tags = ['GET ROUTE'])
def get_all(
        course: str | None = Query(None, description = "show only students in this course", examples = ["Python"]),
        sort_by : str | None = Query(None, description = "Sort by marks, age or name"),
        order_by : str | None = Query("asc", description="asc or desc", examples=["desc"]),
        page : int = Query(1, ge = 1, description = "Which page you want (start from 1)"),
        limit : int = Query(2, ge = 1, le = 100, description = "How many students on one page (1 to 100)"),
        db : Session = Depends(get_db)
):
    if sort_by is not None and sort_by not in SORT_FIELDS:
        raise HTTPException(
            status_code = 400,
            detail = f"Invalid sort_by {sort_by}, Choose from {SORT_FIELDS}"
        )

    if order_by not in SORT_ORDER:
        raise HTTPException(
            status_code=400,
            description = f"Invalid order {order_by}, Choose from {SORT_ORDER}"
        )

    query = db.query(StudentDB)

    if course: # where -> select * from student_records where course == "python"
        query = query.filter(func.lower(StudentDB.course) == course.lower())

    total_students = query.count()

    if sort_by:
        column = getattr(StudentDB, sort_by)
        if order_by == "desc":
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())

    else:
        query = query.order_by(StudentDB.id)

    start = (page - 1) * limit
    student = query.offset(start).limit(limit).all()

    return {
        "page": page,
        "limit": limit,
        "total_student": total_students,
        "students": student
    }