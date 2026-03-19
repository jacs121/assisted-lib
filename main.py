import tkinter as tk
import requests
import uuid
import typing

BOT_URL = "https://clave-app.onrender.com/api/ischat"
api_headers = {"Content-Type": "application/json", "x-session-id": uuid.uuid4().hex}

MODELS = typing.Literal["grok-3-mini", "grok-4-fast-reasoning", "gpt-oss-120b"]

def promptSmart(message: str, model: MODELS = "grok-4-fast-reasoning", systemPrompt: str = "", history: list = []) -> tuple[str, bool]:
    """sends a prompt to the AI bot

    Args:
        message (str): the user's input message
        model (MODELS, optional): the AI bot model to use for this conversation. Defaults to "grok-4-fast-reasoning".
        systemPrompt (str, optional): a global prompts describing how to the AI how to act. Defaults to empty.
        history (list, optional): all previous messages send by the chat bot and the user from oldest to newest. Defaults to empty.

    Returns:
        str: the response from the API
        bool: if the API sent a message or an error
    """
    response = requests.post(BOT_URL, json={
        "message": "\n".join([systemPrompt, message, "here is what was already said, including who said it:"]+history),
        "model": model.lower().replace(" ", "-")
    }, headers=api_headers).json()
    return response.get("text", response.get("error", None)), response.get("text", None) is not None


class MainOverlay(tk.Tk):
    def __init__(self):
        """initiate the jarvisBot window as an overlay"""
        super().__init__("jarvisBot", "jarvisBot")
        self.overrideredirect(True)
        self.wm_attributes("-topmost", 1)

        try:
            self.attributes("-transparentcolor", "#85299C")
            self.config(bg="#85299C")
        except tk.TclError:
            self.attributes("-alpha", 0.7)

        self.mainloop()

    def createUI(self):
        """create all of the UI elements for the overlay"""
        label = tk.Label(self, text="hello world", fg="white", font=("Helvetica", 16), bg="#85299C")
        label.pack(pady=20)

if __name__ == "__main__":
    MainOverlay()