import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import typing
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token
import tkinter as tk
from PIL import Image, ImageTk
import imageio
import tempfile

class BasicOverlay(tk.Tk):
    """a basic jarvisBot window as an overlay"""
    def __init__(self):
        """initiate a basic jarvisBot window as an overlay"""
        super().__init__("jarvisBot", "jarvisBot") # initiate the window it self
        self.overrideredirect(True) # remove window in the app bar and remove the top bar from the window 
        self.wm_attributes("-topmost", 1) # force the window to stay on top

        # make any completely black pixels transparent or if it fails set alpha to 0.7
        try:
            self.attributes("-transparentcolor", "#000000")
            self.config(bg="#000000")
        except tk.TclError:
            self.attributes("-alpha", 0.7)
        self.createUI()

    def createUI(self):
        """create all of the UI elements for the overlay"""
        # just a example label
        label = tk.Label(self, text="hello world", fg="white", font=("Helvetica", 16), bg=self.transparentColor)
        label.pack(pady=20)
    
    def show(self, position: tuple[int, int] = None):
        """show the overlay and keep it running"""
        if position:
            # set a initial position
            self.geometry(f"+{position[0]}+{position[1]}")
        
        # run the functions to show the overlay and the elements inside it
        self.mainloop()

class TextOverlay(BasicOverlay):
    """a text label window as an overlay"""
    def __init__(self, text: str | list[str]):
        """initiate a text label window as an overlay"""
        super().__init__()
        self.text = text if isinstance(text, str) else "\n".join(text)

    def createUI(self):
        """create all of the UI elements for the overlay"""
        # just a example label
        label = tk.Label(self, text=self.text, fg="white", font=("TkDefaultFont", 16), bg=self.transparentColor)
        label.pack(pady=20)

class ImageOverlay(BasicOverlay):
    """an image display overlay"""
    def __init__(self, image: Image.Image, scale: int = 100):
        """initiate an image display overlay"""
        self.scale = scale
        super().__init__()
        self.resizable(False, False)
        data = np.array(image) # convert to a matrix

        # extract each channel
        red = data[..., 0]
        green = data[..., 1]
        blue = data[..., 2]
        
        # shift the blue channel of the image's pixels if ir's in the transparent zone
        data[(red == 0) & (green == 0) & (blue == 0)] = (0, 0, 1)

        self.image = Image.fromarray(data) # convert back into PIL
        
        # set the window size
        ratio = self.image.width/self.image.height
        self.geometry(f"{self.scale}x{int(ratio*self.scale)}")

    def createUI(self):
        # Convert the PIL image to a Tkinter-compatible PhotoImage object
        self.__tk_image__ = ImageTk.PhotoImage(self.image)

        # Create a Label widget to display the image
        self.__image_label__ = tk.Label(self, image=self.__tk_image__)
        self.__image_label__.pack()

        # Keep a reference to the image object
        self.__image_label__.image = self.__tk_image__

class VideoOverlay(BasicOverlay):
    def __init__(self, video: bytes | str, scale = 100):
        
        if isinstance(video, bytes):
            self.video = video
            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp4") as f:
                f.write(video)
                f.flush()
                f.close()
                self.reader = imageio.get_reader(f.name)
        else:
            self.reader = imageio.get_reader(video)

        self.fps = self.reader.get_meta_data()['fps']
        
        self.current_frame = 0
        self.playing = True
        self.scale = scale
        
        super().__init__()
        
        # set the window size
        self.start_frame = Image.fromarray(self.reader.get_data(0))
        ratio = self.start_frame.width/self.start_frame.height
        self.geometry(f"{self.scale}x{int(ratio*self.scale)}")

    def createUI(self):

        self.label = tk.Label(self)
        self.label.pack()

        # Buttons
        controls = tk.Frame(self)
        controls.pack()

        tk.Button(controls, text="Play/Pause", command=self.toggle_play).pack(side="left")
        tk.Button(controls, text="-5s", command=self.skip_backward).pack(side="left")
        tk.Button(controls, text="+5s", command=self.skip_forward).pack(side="left")

    def show_frame(self, index):
        frame = self.reader.get_data(index)
        # extract each channel
        red = frame[..., 0]
        green = frame[..., 1]
        blue = frame[..., 2]
        
        # shift the blue channel of the image's pixels if ir's in the transparent zone
        frame[(red == 0) & (green == 0) & (blue == 0)] = (0, 0, 1)

        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(img)

        self.label.imgtk = imgtk
        self.label.config(image=imgtk)

    def update(self):
        if playing:
            self.current_frame = (self.current_frame + 1) % self.reader.get_length()
            self.show_frame(self.current_frame)

        self.after(int(1000 / self.fps), self.update)

    # Controls
    def toggle_play(self):
        global playing
        playing = not playing

    def skip_forward(self):
        current_frame = min(current_frame + int(self.fps * 5), self.reader.get_length() - 1)  # +5 sec
        self.show_frame(current_frame)

    def skip_backward(self):
        current_frame = max(current_frame - int(self.fps * 5), 0)  # -5 sec
        self.show_frame(current_frame)

    def show(self, position = None):
        self.show_frame(self.current_frame)
        self.update()
        return super().show(position)

def createOverlay(overlayType: typing.Literal["img", "txt", "vid", "audio"], position: tuple[int, int] = None, *args, **kwargs):
    if overlayType == "img":
        overlay = ImageOverlay(*args, **kwargs)
    elif overlayType == "txt":
        overlay = TextOverlay(*args, **kwargs)
    elif overlayType == "vid":
        overlay = VideoOverlay(*args, **kwargs)
    
    overlay.show(position)
    return overlay

createOverlay("vid", None, "test.mp4")