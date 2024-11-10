import tkinter as tk
from tkinter import ttk, filedialog
import os

class WelcomeScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Window setup
        self.title("Welcome to Chess Viewer")
        self.geometry("600x500")
        self.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        # Configure the grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Title
        title_label = ttk.Label(main_frame, 
                              text="Chess Viewer", 
                              font=('Helvetica', 24, 'bold'))
        title_label.pack(pady=20)
        
        # Mode selection frame
        mode_frame = ttk.LabelFrame(main_frame, text="Select Mode", padding="20")
        mode_frame.pack(fill="x", pady=20)
        
        # Play mode button
        play_btn = ttk.Button(mode_frame, 
                            text="Play Chess",
                            command=self.start_play_mode,
                            width=30)
        play_btn.pack(pady=10)
        
        # View PGN button
        view_btn = ttk.Button(mode_frame, 
                            text="View PGN Game",
                            command=self.start_view_mode,
                            width=30)
        view_btn.pack(pady=10)
        
        # Engine options frame
        engine_frame = ttk.LabelFrame(main_frame, text="Engine Options", padding="20")
        engine_frame.pack(fill="x", pady=20)
        
        # Engine status
        self.engine_path = os.path.join('res', 'stockfish', 'stockfish-windows-x86-64-avx2.exe')
        engine_status = "Found" if os.path.exists(self.engine_path) else "Not Found"
        engine_color = "green" if os.path.exists(self.engine_path) else "red"
        
        status_label = ttk.Label(engine_frame, 
                               text=f"Stockfish Engine: {engine_status}",
                               foreground=engine_color)
        status_label.pack(pady=5)
        
        # Engine depth setting
        depth_frame = ttk.Frame(engine_frame)
        depth_frame.pack(pady=5)
        
        depth_label = ttk.Label(depth_frame, text="Analysis Depth:")
        depth_label.pack(side=tk.LEFT, padx=5)
        
        self.depth_var = tk.StringVar(value="20")
        depth_entry = ttk.Entry(depth_frame, 
                              textvariable=self.depth_var,
                              width=5)
        depth_entry.pack(side=tk.LEFT, padx=5)
        
        # Version info
        version_label = ttk.Label(main_frame, 
                                text="Version 1.0",
                                font=('Helvetica', 8))
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