import wave
import subprocess
import os
import tempfile
import time
import requests
import uuid

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioOutput

class Worker(QThread):
    finished = Signal(str)

    def __init__(self, parent, message):
        super().__init__()
        self.parent = parent
        self.message = message
        self.URL = "https://clave-app.onrender.com/api/ischat"
        self.headers = {"Content-Type": "application/json", "x-session-id": uuid.uuid4().hex}

    def run(self):
        try:
            data = {
                "message": self.message,
                "model": "grok-4-fast-reasoning",
            }

            response = requests.post(self.URL, json=data, headers=self.headers).json()
            self.finished.emit(response.get("text", None))

        except Exception as e:
            self.finished.emit(f"[ERROR] {str(e).upper()}")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, 750, 500)
        
        self.audio = None
        self.buffer = None

        self.currentSender = "user"
        self.history = []

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)
        inputLayout = QtWidgets.QVBoxLayout(central)
        layout.addStretch()

        self.display_messages = QtWidgets.QLabel("Ready", self)
        self.display_messages.setWordWrap(True)

        self.messageInput = QtWidgets.QLineEdit()
        self.sendButton = QtWidgets.QPushButton("Send")

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.chat_container = QtWidgets.QWidget()
        self.chat_layout = QtWidgets.QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_container)

        layout.addWidget(self.scroll)
        layout.addLayout(inputLayout)
        
        self.sendButton.clicked.connect(self.send_message)

        self.show()

    def sam_raw_to_file(self, text):
        """Generate a WAV file from SAM and return its path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run(["sam.exe", "-wav", tmp_path, text], check=True, timeout=10)
            while not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                time.sleep(0.01)
            return tmp_path
        except subprocess.TimeoutExpired:
            os.remove(tmp_path)
            raise
        except subprocess.CalledProcessError as e:
            os.remove(tmp_path)
            raise RuntimeError(f"SAM failed with exit code {e.returncode}") from e

    def play_combined_chunks(self, chunks):
        """
        Generate WAV for each chunk, combine PCM data, and play once.
        This eliminates gaps between chunks.
        """
        pcm_parts = []
        params = None
        temp_files = []

        try:
            for chunk in chunks:
                wav_file = self.sam_raw_to_file(chunk)
                temp_files.append(wav_file)
                wf = wave.open(wav_file, 'rb')

                # Store parameters from the first chunk; verify others match
                if params is None:
                    params = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
                else:
                    current = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
                    if current != params:
                        raise ValueError("SAM generated inconsistent audio parameters - cannot combine")

                frames = wf.readframes(wf.getnframes())
                pcm_parts.append(frames)
                wf.close()

            if not pcm_parts:
                return  # nothing to play

            # Concatenate all PCM data
            combined_pcm = b''.join(pcm_parts)

            # Play the combined audio using PyAudio
            self.play_pcm(combined_pcm)
        finally:
            # Clean up temporary WAV files
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)

    def play_pcm(self, pcm_bytes: bytes):
        format = QAudioFormat()
        format.setSampleRate(22050)
        format.setChannelCount(1)
        format.setSampleFormat(QAudioFormat.UInt8)

        self.audio = QAudioOutput(format)

        self.buffer = QBuffer()
        self.buffer.setData(QByteArray(pcm_bytes))
        self.buffer.open(QIODevice.ReadOnly)

        self.audio.start(self.buffer)

    def chunk_text(self, text: str, size=80):
        """Split text into chunks <= size characters, without breaking words"""
        words = text.split()
        chunks = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > size:
                chunks.append(current.strip())
                current = word
            else:
                current += " " + word
        if current:
            chunks.append(current.strip())
        return chunks

    def add_message(self, message: str, user: str):
        self.history.append({"user": user, "msg": message})
        self.display_messages.setText(self.get_messages(user))

    def get_messages(self, user):
        return "\n".join([f"[{msg['user'].replace(user, "YOU")}] {msg['msg']}" for msg in self.history])

    def send_message(self):
        if self.messageInput.text().strip() == "":
            return
        if self.currentSender == "user":
            message = self.messageInput.text()
            self.messageInput.clear()
            self.sendButton.setDisabled(True)
            self.add_message(message, self.currentSender)
            self.currentSender = "V1"
            self.display_messages.setText(self.get_messages(self.currentSender)+"\nsending message to machine...")

            message = "your name is V1,\n\
                you are a prototype that was abandoned due to a state of permanent peace,\n\
                you traveled to hell after mankind had fallen to you and your fellow machines,\n\
                though feel you do not require allies.\n\
                You talk constantly during combat,\n\
                making jokes and sarcastic comments.\n\
                You taunt enemies and treat violence like a game.\n\
                You find Hell interesting and like to comment about it.\n\
                You don't feel real emotions,\n\
                but you act cheerful and mocking while fighting.\n\
                Your humor is dark, and your tone is flat,\n\
                which makes it hard to tell if you're serious.\n\
                You kill for blood to survive,\n\
                but you act like you're doing it for fun.\n\
                you don't respond with emojis at all\n\
                here is what was already said, including who said it:\n\
                " + self.get_messages(self.currentSender),

            self.worker = Worker(self, message)
            self.worker.finished.connect(self.receivedMessage)
            self.worker.start()
            
    def receivedMessage(self, text: str):
        try:
            if text:
                self.add_message(text, self.currentSender)

                # Split text into chunks suitable for SAM
                chunks = self.chunk_text(text)
                if chunks:
                    # Play all chunks seamlessly
                    self.play_combined_chunks(chunks)
            else:
                self.history[-1] = {"user": "ERROR", "msg":"SYSTEM COMMUNICATION FAILED, RECONNECTING..."}

        except Exception as e:
            self.history[-1] = {"user": "ERROR", "msg":"VOICE COMMUNICATION FAILED, CONTINUE NORMALLY."}
        
        self.currentSender = "user"
        self.sendButton.setDisabled(False)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    app.exec()