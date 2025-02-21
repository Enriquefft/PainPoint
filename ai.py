"""OpenAI API client for chat completions, customized for startup interview practice."""

from google import genai  # type: ignore
from google.genai import types  # type: ignore

from env import GEMINI_API_KEY
from textwrap import shorten

client = genai.Client(api_key=GEMINI_API_KEY)


def get_response(user_message: str, system_message: str | None = None) -> str:
    """Get a response from the OpenAI API using a system prompt tailored for interview practice."""
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=types.Part.from_text(text=user_message),
        config=types.GenerateContentConfig(
            system_instruction=system_message,
            temperature=0.8,
            max_output_tokens=350,
        ),
    )

    if response.text is None:
        return ""

    return shorten(response.text, width=1599, placeholder="...")
