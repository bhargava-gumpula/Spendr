import json
import os

from openai import AsyncOpenAI

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")
BASE_URL = os.environ.get("OPENAI_BASE_URL")  # set for Azure AI Foundry / non-default endpoints


def _client() -> AsyncOpenAI:
    if BASE_URL:
        return AsyncOpenAI(base_url=BASE_URL)
    return AsyncOpenAI()


async def call_function(system: str, user_content: str, tool: dict) -> dict:
    """tool is a Responses-API function-tool schema:
    {"type": "function", "name", "description", "parameters"}.
    Forces the model to call it and returns the parsed arguments dict —
    never free text, so callers can rely on the shape."""
    client = _client()
    response = await client.responses.create(
        model=MODEL,
        instructions=system,
        input=user_content,
        tools=[tool],
        tool_choice={"type": "function", "name": tool["name"]},
    )
    for item in response.output:
        if item.type == "function_call" and item.name == tool["name"]:
            try:
                return json.loads(item.arguments)
            except json.JSONDecodeError:
                return {}
    return {}


async def call_with_web_search(system: str, user_content: str, report_tool: dict, max_tool_calls: int = 4) -> dict:
    """Like call_function, but gives the model the hosted web_search tool
    alongside the report function. Can't force tool_choice here — forcing
    the function immediately would skip searching and hallucinate
    arguments — so this relies on the model choosing to search, then
    report. max_tool_calls bounds latency/cost (real web search is slow).
    Returns {} if the model never got around to calling report_tool."""
    client = _client()
    response = await client.responses.create(
        model=MODEL,
        instructions=system,
        input=user_content,
        tools=[{"type": "web_search"}, report_tool],
        max_tool_calls=max_tool_calls,
    )
    for item in response.output:
        if item.type == "function_call" and item.name == report_tool["name"]:
            try:
                return json.loads(item.arguments)
            except json.JSONDecodeError:
                return {}
    return {}
