import tkinter as tk
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token

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

class CodeOverlay(BasicOverlay):
    def __init__(self, code: str | list):
        super().__init__()
        self.code = code if isinstance(code, str) else "\n".join(code)
    
    def createUI(self):
        self.text_widget = tk.Text(self)
        self.text_widget.pack(expand=1, fill="both")
        self.text_widget.insert(0.0, self.code)
        self.highlight_syntax()

    def highlight_syntax(self):

        # Define tags
        colors = {
            Token.Keyword: "blue",
            Token.String: "green",
            Token.Comment: "gray",
            Token.Name.Function: "purple",
        }

        for t, color in colors.items():
            self.text_widget.tag_configure(str(t), foreground=color)

        def highlight_code(event=None, language="python"):
            content = self.text_widget.get("1.0", "end-1c")
            for tag in self.text_widget.tag_names():
                self.text_widget.tag_remove(tag, "1.0", "end")

            lexer = get_lexer_by_name(language)
            for token, value in lex(content, lexer):
                start_index = self.text_widget.index("insert linestart")
                end_index = len(value)+float(start_index)
                print(str(token), start_index, end_index, self.text_widget.get(start_index, end_index)[:-1])
                self.text_widget.tag_add(str(token), start_index, end_index)

        self.text_widget.bind("<KeyRelease>", highlight_code)
        highlight_code()
