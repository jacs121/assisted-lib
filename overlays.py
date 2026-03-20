import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import typing
import tkinter as tk
import os
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
        pass
    
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
        self.text = text if isinstance(text, str) else "\n".join(text)
        super().__init__()

    def createUI(self):
        """create all of the UI elements for the overlay"""
        # just a example label
        label = tk.Label(self, text=self.text, fg="white", font=("TkDefaultFont", 16), bg="#000000")
        label.pack(pady=20)

class ImageOverlay(BasicOverlay):
    """an image display overlay"""
    def __init__(self, image: Image.Image | str, scale: int = 100):
        """initiate an image display overlay"""
        self.scale = scale
        if isinstance(image, str):
            image = Image.open(image)
        
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
        super().__init__()
        self.resizable(False, False)
        self.geometry(f"{int(ratio*self.scale)}x{self.scale}")

    def createUI(self):
        # Convert the PIL image to a Tkinter-compatible PhotoImage object
        self.__tk_image__ = ImageTk.PhotoImage(self.image)

        # Create a Label widget to display the image
        self.__image_label__ = tk.Label(self, image=self.__tk_image__)
        self.__image_label__.pack()

        # Keep a reference to the image object
        self.__image_label__.image = self.__tk_image__

class VideoOverlay(BasicOverlay):
    def __init__(self, video: bytes | str, scale=100):

        self._temp_path = None

        if isinstance(video, bytes):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp.write(video)
            tmp.close()

            self._temp_path = tmp.name
            self.reader = imageio.get_reader(tmp.name, format="ffmpeg")
        else:
            self.reader = imageio.get_reader(video, format="ffmpeg")

        meta = self.reader.get_meta_data()
        self.duration = meta.get('duration', None)
        self.fps = meta.get('fps', None)
        self.total_frames = int(self.fps * self.duration) if self.duration else None

        self.current_frame = 0
        self.playing = False
        self.scale = scale

        super().__init__()

        # window sizing
        self.start_frame = Image.fromarray(self.reader.get_data(0))
        self.ratio = self.start_frame.width / self.start_frame.height
        self.geometry(f"{int(self.ratio * self.scale)}x{self.scale}")

    def createUI(self):
        self.container = tk.Frame(self, bg="#000000")
        self.container.pack(fill="both", expand=True)

        self.label = tk.Label(self.container, bg="#000000")
        self.label.pack(side="top", fill="both", expand=True)

        controls = tk.Frame(self.container, bg="#000000")
        controls.pack(side="bottom", fill="x")
        controls.place(relx=0.5, rely=0.95, anchor="s")

        tk.Button(controls, text="Play/Pause", command=self.toggle_play).pack(side="left")
        tk.Button(controls, text="-5s", command=self.skip_backward).pack(side="left")
        tk.Button(controls, text="+5s", command=self.skip_forward).pack(side="left")

    def show_frame(self, index):
        try:
            frame = self.reader.get_data(index)
        except Exception:
            return  # prevents crash on bad index
        
        img = Image.fromarray(frame).resize(
            (int(self.ratio * self.scale), self.scale),
            Image.Resampling.LANCZOS
        )
        frame = np.array(img) # convert to a matrix

        # transparency logic
        red = frame[..., 0]
        green = frame[..., 1]
        blue = frame[..., 2]
        frame[(red == 0) & (green == 0) & (blue == 0)] = (0, 0, 1)

        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(img)

        self.label.imgtk = imgtk
        self.label.config(image=imgtk)

    def update(self):
        if self.playing:
            self.current_frame += 1

            if self.total_frames:
                self.current_frame %= self.total_frames

            self.show_frame(self.current_frame)

        self.after(int(100 / self.fps), self.update)

    # Controls
    def toggle_play(self):
        self.playing = not self.playing

    def skip_forward(self):
        self.current_frame += int(self.fps * 5)

        if self.total_frames:
            self.current_frame = min(self.current_frame, self.total_frames - 1)

        self.show_frame(self.current_frame)

    def skip_backward(self):
        self.current_frame = max(0, self.current_frame - int(self.fps * 5))
        self.show_frame(self.current_frame)

    def show(self, position=None):
        self.show_frame(self.current_frame)
        self.update()
        return super().show(position)

    def __del__(self):
        if self._temp_path and os.path.exists(self._temp_path):
            os.remove(self._temp_path)

def createOverlay(overlayType: typing.Literal["img", "txt", "vid", "audio"], position: tuple[int, int] = None, *args, **kwargs):
    if overlayType == "img":
        overlay = ImageOverlay(*args, **kwargs)
    elif overlayType == "txt":
        overlay = TextOverlay(*args, **kwargs)
    elif overlayType == "vid":
        overlay = VideoOverlay(*args, **kwargs)
    
    overlay.show(position)
    return overlay
