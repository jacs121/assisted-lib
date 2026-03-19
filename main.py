import wave
import os
import prompting
import overlays
import query
from gtts import gTTS
import tempfile
import shlex

from PySide6 import QtWidgets
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioOutput

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, 750, 500)
        
        self.audio = None
        self.buffer = None

        self.currentSender = "user"
        self.history = []
        
        # create instructions for the AI, with information about system commands 
        self.systemPrompt = ""

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
    
    def raw_to_file(self, text):
    
        """Generate a WAV file from SAM and return its path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        try:
            gtts = gTTS(text)
            gtts.save(tmp_path)
            return tmp_path
        except Exception as e:
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
                wav_file = self.raw_to_file(chunk)
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

    def chunk_text(self, text: str, size=100):
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
            self.currentSender = "genia"
            self.display_messages.setText(self.get_messages(self.currentSender)+"\nthinking...")

            self.worker = prompting.Worker(self, message, systemPrompt=self.systemPrompt)
            self.worker.finished.connect(self.receivedMessage)
            self.worker.start()

    def receivedMessage(self, text: str):
        try:
            if text:
                for msg in text.splitlines():
                    if msg.startswith("/"):
                        command = msg[1:].split(" ")[0]
                        args = shlex.split(msg[1:])
                    else:
                        # add message to chat
                        self.add_message(text, self.currentSender)
                        # play text-to-speech of the message
                        self.play_combined_chunks(text)
            else:
                self.history[-1] = {"user": "ERROR", "msg": text}

        except Exception as e:
            self.history[-1] = {"user": "ERROR", "msg":"voice model failure, please read the response instead"}
        
        self.currentSender = "user"
        self.sendButton.setDisabled(False)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    app.exec()
