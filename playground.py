"""
python will interact with PostgrSQL without any FastApi 
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, String, Integer, Column
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
load_dotenv()



# step 1 - get the db url
DATABASE_URL = os.getenv("DATABASE_URL")

# step 2 - engine = the road to database
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    version = conn.execute(text("SELECT version()")).scalar()
    print(f"Connected to {version.split(",")[0]}")

# .all() -> every row
# .first() -> only the first row
# .scalar() -> only the first value of first row

"""
we make our own Base once and every table inherits from it.
Like Pydantic : BaseModel gives validations
Base : gives table powers
"""

class Base(DeclarativeBase):
    pass

class StudentDB(Base):
    __tablename__ = "student_records"
    id = Column(String, primary_key = True)
    name = Column(String(50), nullable = False)
    age = Column(Integer, nullable = False)
    course = Column(String(50), nullable = False)
    marks = Column(Integer, nullable = False)
    email = Column(String, unique = True, nullable = False)

Base.metadata.create_all(bind = engine)
print("Table ready...")

SessionLocal = sessionmaker(bind = engine)

db = SessionLocal()

if db.get(StudentDB, "S001") is None:
    db.add(StudentDB(id = "S001",
                     name = "Chaitanya Kulkarni",
                     age = 25,
                     course = "Python",
                     marks = 80,
                     email = "kulkarni@gmail.com"))
    db.commit()

# Read it back
for i in db.query(StudentDB).all():
    print(i.id, i.name, i.age, i.marks, i.course, i.email)

# db is session and StudentDB is table and S001 is id ... db.commit() makes permanent changes to database beyond session
# update
Chaitanya = db.get(StudentDB, "S001")
Chaitanya.course = "Data Science"
db.commit()
print(Chaitanya.course)