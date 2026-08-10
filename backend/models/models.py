from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from backend.database.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    row_count = Column(Integer, default=0)
    col_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=False)

    owner = relationship("User", back_populates="datasets")
    metadata_records = relationship("DatasetMetadata", back_populates="dataset", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="dataset", cascade="all, delete-orphan")
    searches = relationship("SearchData", back_populates="dataset", cascade="all, delete-orphan")
    views = relationship("CourseView", back_populates="dataset", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="dataset", cascade="all, delete-orphan")

class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    columns_json = Column(Text, nullable=False) # Store column info as JSON string (types, null counts)
    duplicate_count = Column(Integer, default=0)
    missing_count = Column(Integer, default=0)

    dataset = relationship("Dataset", back_populates="metadata_records")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    name = Column(String, nullable=False)

    dataset = relationship("Dataset", back_populates="categories")

class SearchData(Base):
    __tablename__ = "search_data"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    user_id = Column(String, nullable=False)
    search_keyword = Column(String, nullable=False)
    course_id = Column(String, nullable=True)

    dataset = relationship("Dataset", back_populates="searches")

class CourseView(Base):
    __tablename__ = "course_views"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    user_id = Column(String, nullable=False)
    course_id = Column(String, nullable=False)
    course_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    search_keyword = Column(String, nullable=True)

    dataset = relationship("Dataset", back_populates="views")

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    user_id = Column(String, nullable=False)
    course_id = Column(String, nullable=False)
    course_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    search_keyword = Column(String, nullable=True)

    dataset = relationship("Dataset", back_populates="enrollments")
