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
from sqlalchemy.orm import (
    DeclarativeBase,
    mapped_column,
    sessionmaker,
    Mapped,
    relationship,
)
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


class Base(DeclarativeBase):
    metadata = MetaData(schema=PROJECT_NAME)


class ActiveConversation(Base):
    __tablename__ = "active_conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    users: Mapped["User"] = relationship(back_populates="active_conversations")
    interview: Mapped[str] = mapped_column(String())
    feedback: Mapped[str] = mapped_column(String())


class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer, index=True, primary_key=True)
    phone_number = mapped_column(String(15), unique=True)
    name = mapped_column(String(50), nullable=False)
    target_user_persona: Mapped[str] = mapped_column(String(), nullable=False)
    active_conversation_id = mapped_column(ForeignKey(ActiveConversation.id))
    active_conversations: Mapped["ActiveConversation"] = relationship(
        back_populates="users"
    )
    previous_conversations: Mapped[list["PreviousConversation"]] = relationship()


class PreviousConversation(Base):
    __tablename__ = "previous_conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    interview = Column(Text)
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.now)


with engine.connect() as connection:
    connection.execute(CreateSchema(PROJECT_NAME, if_not_exists=True))
    connection.commit()

Base.metadata.create_all(engine)
