"""Module for database models and session creation."""

import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    create_engine,
)
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.schema import CreateSchema

from env import PG_DATABASE, PG_HOST, PG_PASSWORD, PG_PORT, PG_USER, PROJECT_NAME

db_url = URL.create(
    drivername="postgresql",
    username=PG_USER,
    password=PG_PASSWORD,
    host=PG_HOST,
    database=PG_DATABASE,
    port=PG_PORT,
)

engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base(metadata=MetaData(schema=PROJECT_NAME))


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    name = Column(String)
    target_user_persona = Column(String)
    sessions = relationship("ConversationSession", back_populates="user")


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    conversation_history = Column(Text)  # JSON string storing conversation data
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now
    )
    user = relationship("User", back_populates="sessions")


with engine.connect() as connection:
    connection.execute(CreateSchema(PROJECT_NAME, if_not_exists=True))
    connection.commit()

Base.metadata.create_all(engine)
