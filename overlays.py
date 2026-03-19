import tkinter as tk
from PIL import Image, ImageTk
import numpy as np

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
        self.createUI()
        self.mainloop()

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

    def updateImage(self, image: Image.Image):
        data = np.array(image) # convert to a matrix

        # extract each channel
        red = data[..., 0]
        green = data[..., 1]
        blue = data[..., 2]
        
        # shift the blue channel of the image's pixels if ir's in the transparent zone
        data[(red == 0) & (green == 0) & (blue == 0)] = (0, 0, 1)

        self.image = Image.fromarray(data) # convert back into PIL
        
        # update the image and window size
        self.__tk_image__.paste(self.image)
        ratio = self.image.width/self.image.height
        self.geometry(f"{self.scale}x{int(ratio*self.scale)}")
