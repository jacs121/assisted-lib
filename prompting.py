import requests
import uuid
import typing

BOT_URL = "https://clave-app.onrender.com/api/ischat"
api_headers = {"Content-Type": "application/json", "x-session-id": uuid.uuid4().hex}

SMART_MODELS = typing.Literal["grok-3-mini", "grok-4-fast-reasoning", "gpt-oss-120b"]
MODELS = typing.Literal["gpt-4o", "gpt-3.5"]

def promptSmart(message: str, model: SMART_MODELS = "grok-4-fast-reasoning", systemPrompt: str = "") -> tuple[str, bool]:
    """sends a prompt to the AI bot

    Args:
        message (str): the user's input message
        model (SMART_MODELS, optional): the AI bot model to use for this conversation. Defaults to "grok-4-fast-reasoning".
        systemPrompt (str, optional): a global prompts describing how should the AI act. Defaults to empty.

    Returns:
        str: the response from the API
        bool: if the API sent a message or an error
    """
    
    # post data to API
    response = requests.post(BOT_URL, json={
        "message": systemPrompt+"\n"+message,
        "model": model.lower().replace(" ", "-")
    }, headers=api_headers).json() # retrieve the response as dict
    
    # return the given data without the dict
    return response.get("text", response.get("error", None)), response.get("text", None) is not None

def prompt(message: str, model: MODELS = "gpt-4o", systemPrompt: str = "") -> tuple[str, bool]:
    """sends a prompt to the AI bot

    Args:
        message (str): the user's input message
        model (MODELS, optional): the AI bot model to use for this conversation. Defaults to "gpt-4o".
        systemPrompt (str, optional): a global prompts describing how should the AI act. Defaults to empty.

    Returns:
        str: the response from the API
        bool: if the API sent a message or an error
    """
    # post data to API
    response = requests.post(BOT_URL, json={
        "message": message,
        "model": model.lower().replace(" ", "-"),
        "systemPrompt": systemPrompt
    }, headers=api_headers).json() # retrieve the response as dict
    
    # return the given data without the dict
    return response.get("text", response.get("error", None)), response.get("text", None) is not None
