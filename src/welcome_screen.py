import tkinter as tk
from tkinter import ttk, filedialog
import os

class WelcomeScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Window setup
        self.title("Welcome to Chess Viewer")
        self.geometry("600x400")
        self.resizable(False, False)
        
        # Use consistent font
        default_font = ('Consolas', 10)
        title_font = ('Consolas', 24, 'bold')
        version_font = ('Consolas', 8)
        
        self.option_add('*Font', default_font)
        style = ttk.Style()
        style.configure('.', font=default_font)
        
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, 
                              text="Chess Viewer", 
                              font=title_font)
        title_label.pack(pady=20)
        
        # Welcome message
        welcome_text = "Welcome to Chess Viewer!\n\n" \
                      "This application allows you to:\n" \
                      "• View and analyze chess games\n" \
                      "• Load PGN files\n" \
                      "• Use chess engines for analysis\n" \
                      "• Save games to a database"
        
        msg_label = ttk.Label(main_frame, 
                             text=welcome_text,
                             justify="left")
        msg_label.pack(pady=20)
        
        # Version info
        version_label = ttk.Label(main_frame, 
                                text="Version 1.0",
                                font=version_font)
        version_label.pack(side=tk.BOTTOM, pady=10)
        
        # Store parent reference
        self.parent = parent
        
        # Make this window modal
        self.transient(parent)
        self.grab_set()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
    
    def start_play_mode(self):
        self.parent.start_play_mode(engine_path=self.engine_path, 
                                  engine_depth=int(self.depth_var.get()))
        self.destroy()
    
    def start_view_mode(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
        )
        if file_path:
            self.parent.start_view_mode(file_path, 
                                      engine_path=self.engine_path,
                                      engine_depth=int(self.depth_var.get()))
            self.destroy() 