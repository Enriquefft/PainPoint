"""OpenAI API client for chat completions, customized for startup interview practice."""

from google import genai  # type: ignore
from google.genai import types  # type: ignore

from env import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)
for model in client.models.list():
    print(model)
