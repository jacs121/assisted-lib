import json
import wave
import os
import prompting
from gtts import gTTS
import tempfile
import shlex
import traceback
from PySide6 import QtWidgets
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioOutput
import importlib.util

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, 750, 500)
        
        self.audio = None
        self.buffer = None

        self.currentSender = "user"
        self.history = []
        self.internalStorage = {}
        
        # create instructions for the AI, with information about system commands 
        self.systemPrompt = """in this session I want you to be a computer assistant named Genia
        you will say each line as one programed command or one message
        programed commands are messaging you can send to run functions that can get results and it look like this "/command argument1 argument2... -> path::to::location::only" (nothing else)
        any messages under the your called "SYSTEM" or internal messages that the system sends you
        system commands include:
          * stored: sends you all the stored location in the storage under the SYSTEM user
        commands:""" # example
        self.commandInstructions = []
        
        self.commandLocations = {}
        
        for commandName in config["commands"].keys():
            commandConfig = config["commands"][commandName]

            if not hasattr(modules[commandConfig["module"]], commandConfig["func"]):
                print(f"command location `{commandConfig["module"]}.{commandConfig["func"]}()` doesn't exist")
                continue
            self.commandLocations[commandName] = f"{commandConfig["module"]}.{commandConfig["func"]}"
            self.commandInstructions.append(f"/{commandName}: {commandConfig["description"]}\n  {commandConfig["results"]}\n    arguments:"+"".join(f"\n        * argument {i} (type {arg["type"]}, default's to {arg["default"]}):" for i, arg in enumerate(commandConfig["args"])))

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        # Main vertical layout
        layout = QtWidgets.QVBoxLayout(central)

        # Scroll area for messages
        self.messageScroll = QtWidgets.QScrollArea()
        self.messageScroll.setWidgetResizable(True)

        # Container inside scroll
        self.chat_container = QtWidgets.QWidget()
        self.chat_layout = QtWidgets.QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()

        self.messageScroll.setWidget(self.chat_container)

        # Input layout (horizontal is better UX)
        inputLayout = QtWidgets.QHBoxLayout()

        self.messageInput = QtWidgets.QLineEdit()
        self.sendButton = QtWidgets.QPushButton("Send")

        inputLayout.addWidget(self.messageInput)
        inputLayout.addWidget(self.sendButton)

        # Optional status label
        self.display_messages = QtWidgets.QLabel("Ready")
        self.display_messages.setWordWrap(True)

        # Add everything to main layout
        layout.addWidget(self.messageScroll)
        layout.addLayout(inputLayout)
        layout.addWidget(self.display_messages)

        # Connect button
        self.sendButton.clicked.connect(self.send_message)

        self.show()
    
    def raw_to_file(self, text):
    
        """Generate a WAV file from SAM and return its path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
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
        format.setSampleFormat(QAudioFormat.SampleFormat.UInt16)

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
        self.display_messages.setText(self.get_messages())

    def get_messages(self):
        return "\n".join([f"[{msg['user']}] {msg['msg']}" for msg in self.history])

    def send_message(self):
        if self.messageInput.text().strip() == "":
            return
        if self.currentSender == "user":
            message = self.messageInput.text()
            self.messageInput.clear()
            self.sendButton.setDisabled(True)
            self.add_message(message, self.currentSender)
            self.currentSender = "genia"
            self.display_messages.setText(self.get_messages()+"\nthinking...")

            self.worker = prompting.Worker(self, message, systemPrompt=self.systemPrompt+"\n\n".join(self.commandInstructions)+"\nhistory:\n"+self.get_messages())
            self.worker.finished.connect(self.receivedMessage)
            self.worker.start()
            
    def get_storage(self, location: str):
        print("accessing storage location:", location[9:])
        if location[:9:] not in self.internalStorage.keys():
            self.worker = prompting.Worker(self, f"SYSTEM: no location named {location[9:]} in storage.", systemPrompt=self.systemPrompt+"\n\n".join(self.commandInstructions)+"\nhistory:\n"+self.get_messages())
            self.worker.finished.connect(self.receivedMessage)
            self.worker.start()
        return self.internalStorage[location[9:]]
    
    def set_storage(self, location: str, data):
        print("storing data in storage at:", location[9:])
        self.internalStorage[location[9:]] = data

    def receivedMessage(self, text: str, isMessage: bool):
        typeDict = {"string": str, "integer": int, "float": float, "storageLocation": self.get_storage}
        try:
            if isMessage:
                for msgIndex, msg in enumerate(text.splitlines()):
                    print("message received:", msg)
                    if msg.startswith("/"):
                        try:
                            if msg == "/stored":
                                self.worker = prompting.Worker(self, f"SYSTEM: {list(self.internalStorage.keys())}.", systemPrompt=self.systemPrompt+"\n\n".join(self.commandInstructions)+"\nhistory:\n"+self.get_messages())
                                self.worker.finished.connect(self.receivedMessage)
                                self.worker.start()
                            print("command detected.")
                            command = msg[1:].split(" ")[0]
                            print("command:", command)
                            segments = shlex.split(msg[1:])
                            del segments[0]
                            
                            if "->" in segments:
                                args = segments[:segments.index("->")]
                            else:
                                args = segments
                            
                            print("arguments:", ", ".join(args))
                            method = config["commands"].get(command, None)
                            if method is not None:
                                print("module:", method["module"])
                                print("available:", dir(modules[method["module"]]))
                                print("func:", method["func"])
                                
                                trueArgs = []
                                print("converting message arguments into type arguments")
                                for i, arg in enumerate(args):
                                    print(arg, "->", method["args"][i]["type"])
                                    trueArgs.append(typeDict[method["args"][i]["type"]](arg))
                                
                                print(f"running {method["module"]}.{method["func"]}{tuple(trueArgs)}"+(f" into {'::'.join(segments[segments.index('->')+1:])}" if "->" in segments else ""))
                                self.display_messages.setText(self.get_messages()+f"\nrunning command {msgIndex}...")
                                result = getattr(modules[method["module"]], method["func"])(*trueArgs)
                                print("command ran successfully")
                                if "->" in segments:
                                    self.set_storage(segments[segments.index("->")+1], result)
                                print()
                        except Exception as e:
                            self.add_message("command method failed, please look in the console for more info.", "ERROR")
                            print("COMMAND ERROR:", repr(e))
                            traceback.print_exc()
                    else:
                        # add message to chat
                        self.add_message(msg, self.currentSender)
                        # play text-to-speech of the message (not yet implemented)
                        # self.play_combined_chunks(msg)
            else:
                self.history[-1] = {"user": "ERROR", "msg": text}

        except Exception as e:
            self.history[-1] = {"user": "ERROR", "msg":"voice model failure, please read the response instead"}
        
        self.currentSender = "user"
        self.sendButton.setDisabled(False)

modules = {}

if __name__ == "__main__":
    config = json.load(open("./system_commands.json", "r"))

    for commandName, command in config["commands"].items():
        moduleName = command["module"]
        if moduleName in modules.keys():
            continue
        path = os.path.join("modules", moduleName + ".py")

        if not os.path.exists(path):
            print(f"Module file not found: {path}")
            continue

        spec = importlib.util.spec_from_file_location(moduleName, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules[moduleName] = module
        print("module loaded:", moduleName)

    app = QtWidgets.QApplication([])
    window = MainWindow()
    app.exec()