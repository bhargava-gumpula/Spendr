import json
import os

from openai import AsyncOpenAI

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")


async def call_function(system: str, user_content: str, tool: dict) -> dict:
    """tool is an OpenAI function-tool schema:
    {"type": "function", "function": {"name", "description", "parameters"}}.
    Forces the model to call it and returns the parsed arguments dict —
    never free text, so callers can rely on the shape."""
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model=MODEL,
        tools=[tool],
        tool_choice={"type": "function", "function": {"name": tool["function"]["name"]}},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    )
    message = response.choices[0].message
    if message.tool_calls:
        try:
            return json.loads(message.tool_calls[0].function.arguments)
        except json.JSONDecodeError:
            return {}
    return {}
