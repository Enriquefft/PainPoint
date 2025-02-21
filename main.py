"""Main API module for the chatbot."""

# ruff: noqa: N803 (Twilio API requires Capitalized variable names)
# ruff: noqa: B008 (fastapi makes use of reusable default function calls)

import json
import logging
from collections.abc import Generator
import random

from fastapi import Depends, FastAPI, Form
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai import get_response
from models import SessionLocal, User, ActiveConversation, PreviousConversation
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
    Supports two modes:
      - Interview Mode: the AI acts as a client and stores the conversation.
      - End Conversation: on receiving "reset" or "start feedback", appropriate actions occur.
    """
    phone_number = From.removeprefix("whatsapp:")
    user = db.execute(select(User).where(User.phone_number == phone_number)).scalar()

    if not user:
        if "register" in Body.lower():
            await register_user(Body, phone_number, db)
            return ""
        send_message(
            From,
            "You are not registered. To register, please start your message with 'register' followed by your details in this format:\n\n"
            "'register, your name, your target user or client description.'\n\n"
            "Make sure to be as specific as possible when describing your target user or client.\n\n"
            "Example: 'register, John Doe, College students between 1st and 4th semester who struggle learning math.'",
        )
        return ""
    active_conv = db.execute(
        select(ActiveConversation).where(
            ActiveConversation.id == user.active_conversation_id
        )
    ).scalar()
    if not active_conv:
        # Create a new active conversation record with the initial exchange.
        conversation_record: dict[str, list[str]] = {"user": [], "bot": []}
        active_conv = ActiveConversation(
            users=user, interview=json.dumps(conversation_record), feedback=""
        )
        db.add(active_conv)
    if Body.strip().lower() == "remove":
        db.delete(active_conv)
        db.delete(user)
        db.commit()
        send_message(From, "User has been removed.")
        return "User has been removed."

    if Body.strip().lower() == "reset":
        previous_conv = PreviousConversation(
            user_id=user.id,
            interview=active_conv.interview,
            feedback=active_conv.feedback,
        )
        db.add(previous_conv)
        db.delete(active_conv)
        db.commit()
        send_message(From, "Conversation has been reset.")
        return "Conversation has been reset."

    if Body.strip().lower() == "start feedback":
        if not active_conv:
            send_message(From, "No active conversation found.")
            return "No active conversation found."

        feedback_prompt = (
            "You are now an interview feedback expert. Analyze the following interview transcript "
            "using principles from 'The Mom Test'. Provide detailed, actionable feedback—point out any "
            "overly generic or pitchy questions and suggest improvements based on asking about past experiences, "
            "deflecting compliments, and avoiding hypothetical future questions.\n\n"
            "Interview Transcript:\n" + active_conv.interview
        )
        feedback_response = get_response(Body, feedback_prompt)

        # Append feedback (assuming active_conv.feedback is a JSON string with structure {"user": [], "bot": []})
        try:
            feedback_record: dict[str, list[str]] = (
                json.loads(active_conv.feedback)
                if active_conv.feedback
                else {"user": [], "bot": []}
            )
        except json.JSONDecodeError:
            feedback_record = {"user": [], "bot": []}
        feedback_record["user"].append(Body)
        feedback_record["bot"].append(feedback_response)
        active_conv.feedback = json.dumps(feedback_record)
        db.commit()
        send_message(From, feedback_response)
        return feedback_response

    # ---------------- Dynamic Memory and Self-Reflection ----------------
    # Retrieve the last exchange from conversation history (if available)
    conversation_record = json.loads(active_conv.interview)
    if conversation_record["user"] and conversation_record["bot"]:
        last_user = conversation_record["user"][-1]
        last_bot = conversation_record["bot"][-1]
        last_exchange = f"Last exchange - User: {last_user} | Bot: {last_bot}"
    else:
        last_exchange = ""

    # Compute user's word count and add a random factor
    user_word_count = len(Body.split())
    random_factor = random.uniform(0.7, 1.3)
    target_word_count = user_word_count * random_factor

    if target_word_count < 15:
        length_instruction = "Respond concisely."
    elif target_word_count < 40:
        length_instruction = "Provide a moderately detailed answer."
    else:
        length_instruction = "Offer a comprehensive and detailed explanation."

    # Build system prompt with dynamic memory and self-reflection instructions.
    system_message = (
        "You are a unique and random peruvian whose personality is very loosely based on a generic description: {user.target_user_persona}, its nowhere strict, you need to create a persona that fits to some deegre (randomly between 30-80%) with that description"
        "However, you are a your responses may diverge from that description if new insights arise. "
        "Engage in a realistic, natural conversation with varied response lengths: generally short answers for simple questions, "
        "but elaborate when the user's input is complex. "
        f"{length_instruction} "
    )
    if last_exchange:
        system_message += f"Remember this recent exchange: {last_exchange}. "

    # Self-reflection instruction to ensure persona consistency
    system_message += (
        "Before finalizing your answer, take a brief moment to reflect on whether your response aligns with your invented random persona. "
        "If it deviates, adjust your response accordingly."
    )
    # -----------------------------------------------------------------------

    chat_response = get_response(Body, system_message)
    send_message(From, chat_response)

    # Append the new exchange to the conversation history.
    conversation_record["user"].append(Body)
    conversation_record["bot"].append(chat_response)
    active_conv.interview = json.dumps(conversation_record)
    db.commit()

    return chat_response


async def register_user(body: str, phone_number: str, db: Session) -> str:
    """Register a new user."""
    try:
        details = body.split(",")
        if len(details) < 3:
            error_msg = "Please provide all details in the format: register, Name, user description..."
            raise ValueError(error_msg)

        _, name, *user_description = details
        user_description = ", ".join(user_description)

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
