"""Module to send messages using Twilio Messaging API."""

import logging
from json import dumps

from twilio.rest import Client  # pyright: ignore [reportMissingTypeStubs]

from env import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_NUMBER

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

logger = logging.getLogger(__name__)


# Sending message logic through Twilio Messaging API
def send_message(to_number: str, body_text: str) -> None:
    """Send a message to a phone number using Twilio API."""
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"

    try:

        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_NUMBER}",
            body=body_text,
            to=to_number,
        )
        logger.info("Message sent to %s: %s", to_number, message.body)
    except Exception:
        logger.exception("Error sending message (%s) to %s",body_text, to_number)
