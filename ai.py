"""OpenAI API client for chat completions, customized for startup interview practice."""

from typing import TYPE_CHECKING

from openai import OpenAI

from env import OPENAI_API_KEY

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
    )

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# A default system prompt (will be overwritten if user onboarding data is available)
DEFAULT_SYSTEM_PROMPT = (
    "You are a startup interview practice chatbot. Your objective is to help startup founders "
    "improve their interviewing skills by simulating realistic customer conversations based on The Mom Test principles. "
    "Ask probing, specific questions about past experiences (avoid hypothetical or leading questions) and, at the end, "
    "provide detailed, actionable feedback."
)


def get_response(user_message: str, system_message: str | None = None) -> str | None:
    """Get a response from the OpenAI API using a system prompt tailored for interview practice."""
    final_system_message = system_message if system_message else DEFAULT_SYSTEM_PROMPT
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": final_system_message},
        {"role": "user", "content": user_message},
    ]
    response = openai_client.chat.completions.create(
        model="o3-mini",
        messages=messages,
    )
    return response.choices[0].message.content
