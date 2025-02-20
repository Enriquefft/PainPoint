"""Main API module for the chatbot."""

# ruff: noqa: N803 (Twilio API requires Capitalized variable names)
# ruff: noqa: B008 (fastapi makes use of reusable default function calls)

import json
import logging
from collections.abc import Generator

from fastapi import Depends, FastAPI, Form
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai import get_response
from models import ConversationSession, SessionLocal, User
from wsp import send_message

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"msg": "up & running"}

# Dependency for DB connection
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/message")
async def reply(
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db),
) -> str:
    """
    Endpoint to handle user messages.

    The chatbot uses the founder's onboarding details to tailor its system prompt.
    """
    phone_number = From.removeprefix("whatsapp:")
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        if "register" in Body.lower():
            return await register_user(Body, phone_number, db)
        else:  # noqa: RET505
            send_message(
                From,
                "You are not registered. To register, please start your message with 'register' followed by your details in this format:\n\n"
                "'register, your name, your target user or client description.'\n\n"
                "Example: 'register, John Doe, College students between 1st and 4th semester who struggle learning math.'\n\n"
                "Please make sure your user description is well defined and correctly delimited (not everyone can be your user).",
            )
            return ""

    # Build a personalized system prompt using the onboarding data.
    system_message = (
        f"You are a startup interview practice chatbot for startup founders. "
        f"The founder's name is {user.name}."
        f"Their target customer is described as: {user.target_user_persona}. "
        "Start or continue simulating a realistic customer interview using The Mom Test principles: ask probing, concrete, and specific questions about past behaviors. "
        "At the end of the session, provide detailed, actionable feedback on errors and areas of improvement."
    )

    chat_response = get_response(Body, system_message)
    if chat_response is None:
        logger.error("Failed to get a response from the chat system")
        return ""

    conversation_data = {
        "user": Body,
        "bot": chat_response
    }
    session = ConversationSession(
        user_id=user.id,
        conversation_history=json.dumps(conversation_data)
    )
    db.add(session)
    db.commit()

    logger.info("Processed message from user %s", phone_number)
    return chat_response


async def register_user(body: str, phone_number: str, db: Session) -> str:
    """Register a new user."""
    try:
        details = body.split(",")
        if len(details) != 3:
            return "Please provide all details in the format: register, Name, user description"

        _, name, user_description = details

        user = User(
            name=name.strip(),
            phone_number=phone_number,
            target_user_persona=user_description.strip(),


        )
        db.add(user)
        db.commit()
        db.refresh(user)

    except SQLAlchemyError as e:
        db.rollback()
        error_message = f"Error registering user: {e}"
        logger.exception(error_message)
        return "Registration failed. Please try again."
    else:
        send_message(f"whatsapp:{phone_number}", "Registration successful.")
        return "Registration successful."
