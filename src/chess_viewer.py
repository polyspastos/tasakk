from .welcome_screen import WelcomeScreen
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import chess
import chess.pgn
import io
import os
from .chess_database import ChessDatabase
from .pgn_parser import PGNParser
from .chess_utils import format_game_display, parse_elo
import xml.etree.ElementTree as ET
from wand.image import Image as WandImage
import numpy as np
from scipy import ndimage
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chess_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChessViewer(tk.Frame):
    def __init__(self, root):
        print("Initializing ChessViewer...")
        super().__init__(root)
        self.root = root
        
        # Position window at 1/3 from left, 1/5 from top of screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = screen_width // 3
        y = screen_height // 8
        root.geometry(f"+{x}+{y}")  # Position window without changing its size
        
        # Set default font for all widgets
        default_font = ('Consolas', 10)
        self.option_add('*Font', default_font)
        
        # Configure specific fonts for ttk widgets
        style = ttk.Style()
        style.configure('.', font=default_font)
        
        # Configure specific widget classes to use Consolas
        style.configure('TLabel', font=default_font)
        style.configure('TButton', font=default_font)
        style.configure('TEntry', font=default_font)
        style.configure('Treeview', font=default_font)
        style.configure('TLabelframe.Label', font=default_font)
        
        # Theme colors with consistent dark mode
        self.themes = {
            'light': {
                'bg': '#f0f0f0',
                'fg': '#000000',
                'light_squares': '#F0D9B5',
                'dark_squares': '#B58863',
                'text_bg': 'white',
                'text_fg': 'black',
                'button_bg': '#e0e0e0',
                'button_fg': 'black',
                'listbox_bg': 'white',
                'listbox_fg': 'black',
                'frame_bg': '#f0f0f0',
                'menu_bg': '#f0f0f0',
                'menu_fg': 'black',
                'analysis_bg': 'white',
                'analysis_fg': 'black'
            },
            'dark': {
                'bg': '#1e1e1e',            # Darker background
                'fg': '#ffffff',
                'light_squares': '#769656',
                'dark_squares': '#4a7039',
                'text_bg': '#2d2d2d',       # Dark text areas
                'text_fg': '#ffffff',
                'button_bg': '#383838',     # Dark buttons
                'button_fg': '#ffffff',
                'listbox_bg': '#2d2d2d',    # Dark listbox
                'listbox_fg': '#ffffff',
                'frame_bg': '#1e1e1e',      # Dark frames
                'menu_bg': '#383838',       # Dark menus
                'menu_fg': '#ffffff',
                'analysis_bg': '#2d2d2d',
                'analysis_fg': '#ffffff'
            }
        }
        
        # Start in dark mode
        self.current_theme = 'dark'
        self.apply_theme()
        
        # Pack the frame
        self.pack(fill=tk.BOTH, expand=True)
        
        # Initialize components
        self.db = None
        self.parser = PGNParser()
        
        # Initialize variables
        self.current_game = None
        self.current_move_index = 0
        self.games_list = []
        self.piece_images = {}
        self.square_size = 45
        self.light_squares = '#F0D9B5'
        self.dark_squares = '#B58863'
        self.board = chess.Board()
        self.position = self.get_initial_position()
        
        # Initialize engine-related variables
        self.engine = None
        self.engine_path = None
        self.engine_depth = 20
        self.analyzing = False
        self.num_lines = 1  # Number of lines to show
        self.max_lines = 5  # Maximum number of lines
        self.eval_var = tk.StringVar(value="")
        self.analysis_lines = []  # Store multiple analysis lines
        
        # Initialize board offsets
        self.board_x_offset = 0  # Will be updated in resize_board
        self.board_y_offset = 0  # Will be updated in resize_board
        
        print("Creating menu...")
        self.create_menu()
        
        print("Setting up GUI...")
        self.setup_gui()
        
        print("Creating pieces...")
        self.create_default_pieces()
        
        print("Drawing board...")
        self.draw_board()
        
        # Open most recent PGN file
        self.open_most_recent_pgn()
        
        # Show welcome screen
        # self.after(100, lambda: WelcomeScreen(self))
        
        # Bind events...
        print("ChessViewer initialization complete")
        
        # Remove any existing bindings for arrow keys
        for key in ['<Left>', '<Right>', '<Up>', '<Down>']:
            self.root.unbind_all(key)
        
        # Add our specific bindings with high priority
        self.root.bind_all('<Left>', lambda e: self.prev_ply(e), add="+")
        self.root.bind_all('<Right>', lambda e: self.next_ply(e), add="+")
        self.root.bind_all('<Up>', lambda e: self.first_move() or "break", add="+")
        self.root.bind_all('<Down>', lambda e: self.last_move() or "break", add="+")
        
        # Add game navigation hotkeys
        self.root.bind_all('n', lambda e: self.next_game() or "break", add="+")
        self.root.bind_all('N', lambda e: self.next_game() or "break", add="+")
        self.root.bind_all('p', lambda e: self.prev_game() or "break", add="+")
        self.root.bind_all('P', lambda e: self.prev_game() or "break", add="+")
        
        # Try to find and load Stockfish by default
        self.find_default_engine()
        
        # Bind cleanup to window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_initial_position(self):
        """Return the initial chess position as a 2D array."""
        position = [
            ['bR', 'bN', 'bB', 'bQ', 'bK', 'bB', 'bN', 'bR'],
            ['bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP'],
            ['wR', 'wN', 'wB', 'wQ', 'wK', 'wB', 'wN', 'wR']
        ]
        return position

    def create_menu(self):
        """Create the menu bar."""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open PGN", command=self.open_pgn)
        file_menu.add_command(label="Open Database", command=self.open_database)
        file_menu.add_command(label="Save to Database", command=self.save_to_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Flip Board", command=self.flip_board)
        view_menu.add_command(label="Toggle Dark Mode", command=self.toggle_theme)
        
        # Engines menu
        self.engines_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Engines", menu=self.engines_menu)
        self.engines_menu.add_command(label="Select Engine...", command=self.select_engine)
        self.engines_menu.add_command(label="Set Analysis Depth...", command=self.set_engine_depth)
        self.engines_menu.add_separator()
        
        # Create a variable to track the selected engine
        self.selected_engine = tk.StringVar()
        
        # Immediately populate the engines menu
        self.update_engines_menu()

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.apply_theme()

    def apply_theme(self):
        """Apply the current theme to all widgets."""
        theme = self.themes[self.current_theme]
        
        # Configure root window and main frame
        self.root.configure(bg=theme['bg'])
        self.configure(bg=theme['bg'])
        
        # Configure all frames
        for widget in self.winfo_children():
            if isinstance(widget, (ttk.Frame, tk.Frame, ttk.LabelFrame)):
                widget.configure(bg=theme['frame_bg'])
                # Configure children of frames
                for child in widget.winfo_children():
                    if isinstance(child, (tk.Text, tk.Entry)):
                        child.configure(
                            bg=theme['text_bg'],
                            fg=theme['text_fg'],
                            insertbackground=theme['text_fg'],
                            selectbackground=theme['button_bg'],
                            selectforeground=theme['button_fg']
                        )
                    elif isinstance(child, tk.Listbox):
                        child.configure(
                            bg=theme['listbox_bg'],
                            fg=theme['listbox_fg'],
                            selectbackground=theme['button_bg'],
                            selectforeground=theme['button_fg']
                        )
                    elif isinstance(child, (ttk.Button, tk.Button)):
                        if isinstance(child, tk.Button):
                            child.configure(
                                bg=theme['button_bg'],
                                fg=theme['button_fg'],
                                activebackground=theme['button_bg'],
                                activeforeground=theme['button_fg']
                            )
                    elif isinstance(child, (ttk.Label, tk.Label)):
                        child.configure(
                            bg=theme['frame_bg'],
                            fg=theme['fg']
                        )
        
        # Configure specific widgets
        if hasattr(self, 'info_text'):
            self.info_text.configure(
                bg=theme['text_bg'],
                fg=theme['text_fg'],
                insertbackground=theme['text_fg'],
                selectbackground=theme['button_bg'],
                selectforeground=theme['button_fg']
            )
        
        if hasattr(self, 'moves_text'):
            self.moves_text.configure(
                bg=theme['text_bg'],
                fg=theme['text_fg'],
                insertbackground=theme['text_fg'],
                selectbackground=theme['button_bg'],
                selectforeground=theme['button_fg']
            )
        
        if hasattr(self, 'game_listbox'):
            self.game_listbox.configure(
                bg=theme['listbox_bg'],
                fg=theme['listbox_fg'],
                selectbackground=theme['button_bg'],
                selectforeground=theme['button_fg']
            )
        
        # Configure menu if it exists
        if hasattr(self, 'menubar'):
            self._configure_menu(self.menubar, theme)
        
        # Update board colors
        self.light_squares = theme['light_squares']
        self.dark_squares = theme['dark_squares']
        
        # Redraw the board if it exists
        if hasattr(self, 'canvas'):
            self.canvas.configure(bg=theme['bg'])
            self.update_pieces()
        
        # Configure analysis text specifically
        if hasattr(self, 'analysis_text'):
            self.analysis_text.configure(
                bg=theme['analysis_bg'],
                fg=theme['analysis_fg'],
                insertbackground=theme['analysis_fg'],
                selectbackground=theme['button_bg'],
                selectforeground=theme['button_fg']
            )

    def _configure_menu(self, menu, theme):
        """Configure menu colors recursively."""
        menu.configure(
            bg=theme['menu_bg'],
            fg=theme['menu_fg'],
            activebackground=theme['button_bg'],
            activeforeground=theme['button_fg']
        )
        
        # Configure all submenus
        for item in menu.winfo_children():
            if isinstance(item, tk.Menu):
                self._configure_menu(item, theme)

    def setup_gui(self):
        """Set up the main GUI layout."""
        # Main horizontal paned window
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for games list
        self.left_frame = ttk.Frame(self.main_paned, width=350)
        self.left_frame.pack_propagate(False)
        self.main_paned.add(self.left_frame, weight=1)
        
        # Games list
        self.games_frame = ttk.LabelFrame(self.left_frame, text="games")
        self.games_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Game listbox with scrollbar
        games_scroll = ttk.Scrollbar(self.games_frame)
        games_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.game_listbox = tk.Listbox(
            self.games_frame,
            yscrollcommand=games_scroll.set,
            bg=self.themes[self.current_theme]['listbox_bg'],
            fg=self.themes[self.current_theme]['listbox_fg'],
            selectmode=tk.SINGLE
        )
        self.game_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        games_scroll.config(command=self.game_listbox.yview)
        
        # Center panel for board and controls
        self.center_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.center_frame, weight=3)
        
        # Board container frame
        self.board_container = ttk.Frame(self.center_frame)
        self.board_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Make board container resizable
        self.board_container.grid_rowconfigure(0, weight=1)
        self.board_container.grid_columnconfigure(0, weight=1)
        
        # Create canvas for the chess board
        self.canvas = tk.Canvas(
            self.board_container,
            bg=self.themes[self.current_theme]['bg'],
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Controls frame below the board
        self.controls_frame = ttk.Frame(self.center_frame)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation buttons
        ttk.Button(self.controls_frame, text="Prev Game", command=self.prev_game).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls_frame, text="<<", command=self.first_move).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls_frame, text="<", command=self.prev_move).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls_frame, text=">", command=self.next_move).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls_frame, text=">>", command=self.last_move).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls_frame, text="Next Game", command=self.next_game).pack(side=tk.LEFT, padx=2)
        
        # Right panel
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=2)
        
        # Set up right panel contents
        self.setup_right_panel()
        
        # Bind resize events
        self.canvas.bind('<Configure>', self.resize_board)
        self.game_listbox.bind('<<ListboxSelect>>', self.on_select_game)

    def create_default_pieces(self):
        print("Starting create_default_pieces...")
        try:
            from wand.image import Image as WandImage
            import io
            import numpy as np
            from scipy import ndimage
            
            # Calculate the size we want for each piece (90% of square size)
            piece_size = int(self.square_size * 0.9)
            
            # Piece positions in the sprite (x, y)
            piece_positions = {
                'wK': (0, 0),    'wQ': (45, 0),   'wB': (90, 0),
                'wN': (135, 0),  'wR': (180, 0),  'wP': (225, 0),
                'bK': (0, 45),   'bQ': (45, 45),  'bB': (90, 45),
                'bN': (135, 45), 'bR': (180, 45), 'bP': (225, 45)
            }
            
            # Load the sprite sheet
            with WandImage(filename='res/chess_pieces_sprite.svg') as sprite:
                # Process each piece
                for piece_key, (x, y) in piece_positions.items():
                    # print(f"Creating piece {piece_key}...")
                    # logger.info(f"Creating piece {piece_key}...")
                    
                    # Clone the sprite to avoid modifying the original
                    with sprite.clone() as piece:
                        # Crop to the piece location
                        piece.crop(x, y, x + 45, y + 45)
                        
                        # Resize to desired size
                        piece.resize(piece_size, piece_size)
                        
                        # Convert to PNG
                        piece.format = 'png'
                        png_data = piece.make_blob()
                    
                    # Create PIL Image from PNG data
                    img = Image.open(io.BytesIO(png_data))
                    img = img.convert('RGBA')
                    
                    # Convert to numpy array for easier processing
                    data = np.array(img)
                    
                    # Find the piece shape (same threshold for both colors)
                    piece_shape = ~((data[:,:,0] > 250) & (data[:,:,1] > 250) & (data[:,:,2] > 250))
                    
                    # Fill the piece interior
                    filled_shape = ndimage.binary_fill_holes(piece_shape)
                    
                    # Create stronger outer border (two iterations)
                    dilated = ndimage.binary_dilation(filled_shape, iterations=2)
                    outer_border = dilated & ~filled_shape
                    
                    if piece_key.endswith('P'):
                        # For pawns, only keep the outer border
                        if piece_key.startswith('b'):
                            # Black pawns should be solid black
                            black_areas = filled_shape
                            white_areas = np.zeros_like(filled_shape, dtype=bool)
                        else:
                            # White pawns
                            black_areas = outer_border
                            white_areas = filled_shape & ~outer_border
                    else:
                        # For other pieces, process internal lines
                        # Use same threshold for both colors
                        dark_lines = (data[:,:,0] < 64) & (data[:,:,1] < 64) & (data[:,:,2] < 64)
                        light_lines = (data[:,:,0] > 210) & (data[:,:,1] > 210) & (data[:,:,2] > 210)  # Slightly lower threshold
                        
                        eroded_shape = ndimage.binary_erosion(filled_shape, iterations=4)
                        
                        # Process lines with slightly stronger dilation
                        if piece_key.startswith('b'):
                            light_lines = ndimage.binary_dilation(light_lines, iterations=1,
                                                                structure=np.array([[1,1,1],
                                                                                  [1,1,1],
                                                                                  [1,1,1]]))
                        dark_lines = ndimage.binary_dilation(dark_lines, iterations=1,
                                                           structure=np.array([[0,1,0],
                                                                             [1,1,1],
                                                                             [0,1,0]]))
                        
                        interior_dark_lines = dark_lines & eroded_shape
                        interior_light_lines = light_lines & eroded_shape
                        
                        if piece_key.startswith('b'):
                            black_areas = filled_shape & ~interior_light_lines
                            white_areas = interior_light_lines
                        else:
                            black_areas = outer_border | interior_dark_lines
                            white_areas = filled_shape & ~black_areas
                    
                    # Set colors
                    data[black_areas,0:3] = 0    # Pure black
                    data[white_areas,0:3] = 255  # Pure white
                    
                    # Use the dilated shape as the mask
                    mask = dilated
                    data[:,:,3] = np.where(mask, 255, 0)
                    
                    # Create PIL Image from numpy array
                    img = Image.fromarray(data)
                    
                    # Create a new image with the square size dimensions
                    final_img = Image.new('RGBA', (self.square_size, self.square_size), (0, 0, 0, 0))
                    
                    # Calculate position to paste (center the piece)
                    paste_x = (self.square_size - piece_size) // 2
                    paste_y = (self.square_size - piece_size) // 2
                    
                    # Paste the piece onto the center of the square
                    final_img.paste(img, (paste_x, paste_y))
                    
                    # Create PhotoImage
                    self.piece_images[piece_key] = ImageTk.PhotoImage(final_img)
                    
                    # print(f"Created piece {piece_key}")
                    # logger.info(f"Created piece {piece_key}")
                
        except Exception as e:
            print(f"Error creating pieces: {e}")
            import traceback
            traceback.print_exc()
        
        print("Finished create_default_pieces")

    def draw_board(self):
        """Draw the chess board."""
        # Clear existing squares
        self.canvas.delete("square")
        
        # Draw new squares
        for row in range(8):
            for col in range(8):
                x1 = self.board_x_offset + (col * self.square_size)
                y1 = self.board_y_offset + (row * self.square_size)
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                
                # Determine square color
                color = self.light_squares if (row + col) % 2 == 0 else self.dark_squares
                
                # Create square
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="",
                    tags="square"
                )

    def start_play_mode(self, engine_path, engine_depth):
        """Initialize play mode."""
        print(f"Starting play mode with engine depth {engine_depth}")
        # TODO: Implement play mode setup
        pass

    def start_view_mode(self, pgn_path, engine_path, engine_depth):
        """Initialize view mode with a PGN file."""
        print(f"Starting view mode with file {pgn_path}")
        self.engine_path = engine_path
        self.engine_depth = engine_depth
        self.open_pgn(pgn_path)

    def open_pgn(self, file_path=None):
        """Open and load a PGN file."""
        # If no file path provided, show file dialog
        if file_path is None:
            file_path = filedialog.askopenfilename(
                filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
            )
        
        if not file_path:
            return

        try:
            # Make sure GUI elements exist before using them
            if not hasattr(self, 'game_listbox') or not hasattr(self, 'info_text'):
                raise Exception("GUI elements not initialized")
                
            self.games_list = self.parser.parse_file(file_path)
            if not self.games_list:
                raise Exception("No valid games found in file")
                
            self.game_listbox.delete(0, tk.END)
            
            for game in self.games_list:
                game_str = self.format_game_display(game)
                self.game_listbox.insert(tk.END, game_str)
            
            if self.parser.errors:
                messagebox.showwarning(
                    "Parser Warnings",
                    f"Some games could not be parsed:\n\n" + "\n".join(self.parser.errors[:5])
                )
            
            # Select and load the first game if available
            if self.games_list:
                self.game_listbox.selection_set(0)
                self.current_game = self.games_list[0]
                self.current_move_index = 0
                self.update_game_info()
                self.update_pieces()
            
            self.game_listbox.bind('<<ListboxSelect>>', self.on_select_game)
                
        except Exception as e:
            logger.error(f"Error loading PGN file: {e}")
            messagebox.showerror("Error", f"Error loading PGN file: {str(e)}")

    def format_game_display(self, game):
        """Format a game for display in the listbox."""
        try:
            white = game.get('White', game.get('white', 'Unknown'))
            black = game.get('Black', game.get('black', 'Unknown'))
            result = game.get('Result', game.get('result', '*'))
            event = game.get('Event', game.get('event', ''))
            date = game.get('Date', game.get('date', ''))
            
            display = f"{white} - {black} ({result})"
            if event:
                display += f" | {event}"
            if date:
                display += f" {date}"
                
            return display
        except Exception as e:
            logger.error(f"Error formatting game display: {e}")
            return "Error formatting game"

    def open_database(self):
        db_path = filedialog.askopenfilename(
            filetypes=[("SQLite databases", "*.db"), ("All files", "*.*")]
        )
        if not db_path:
            return
            
        try:
            self.db = ChessDatabase(db_path)
            if not self.db.connect():
                raise Exception("Could not connect to database")
                
            # Load games from database
            games = self.db.get_games(limit=100)  # Load first 100 games
            self.games_list = []
            self.game_listbox.delete(0, tk.END)
            
            for game in games:
                game_str = self.format_game_display(game)
                self.game_listbox.insert(tk.END, game_str)
                self.games_list.append(game)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error opening database: {str(e)}")

    def save_to_database(self):
        if not self.db:
            db_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("SQLite databases", "*.db"), ("All files", "*.*")]
            )
            if not db_path:
                return
                
            self.db = ChessDatabase(db_path)
            if not self.db.connect():
                messagebox.showerror("Error", "Could not create database")
                return

        selection = self.game_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select games to save")
            return

        try:
            for index in selection:
                game = self.games_list[index]
                if not self.db.add_game(game):
                    raise Exception(f"Failed to save game {index + 1}")
                    
            messagebox.showinfo("Success", f"Saved {len(selection)} games to database")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving to database: {str(e)}")

    def search_games(self):
        if not self.db:
            messagebox.showinfo("Info", "Please open a database first")
            return
            
        search_term = self.search_var.get().strip()
        if not search_term:
            return
            
        try:
            games = self.db.search_games(search_term)
            self.games_list = []
            self.game_listbox.delete(0, tk.END)
            
            for game in games:
                game_str = self.format_game_display(game)
                self.game_listbox.insert(tk.END, game_str)
                self.games_list.append(game)
                
        except Exception as e:
            messagebox.showerror("Error", f"Search error: {str(e)}")

    def flip_board(self):
        # TODO: Implement board flipping
        pass

    def on_resize_window(self, event):
        """Handle window resize without resetting position."""
        # Only respond if it's a window resize, not a widget configure event
        if event.widget == self.root:
            # Adjust canvas size if needed
            if hasattr(self, 'canvas'):
                self.canvas.configure(width=event.width, height=event.height)
                self.draw_board()  # Only redraw the board, don't reset position
                self.update_pieces()  # Keep the current position

    # Navigation methods
    def first_move(self):
        if self.current_game:
            self.current_move_index = 0
            self.update_pieces()

    def last_move(self, event=None):
        """Go to the last move in the current game."""
        if not self.current_game:
            return
            
        try:
            if isinstance(self.current_game, dict):
                pgn_str = self.current_game.get('pgn', '')
                if pgn_str:
                    game = chess.pgn.read_game(io.StringIO(pgn_str))
                    if game:
                        moves = list(game.mainline_moves())
                        self.current_move_index = len(moves)
            else:
                moves = list(self.current_game.mainline_moves())
                self.current_move_index = len(moves)
                
            self.update_pieces()
            
        except Exception as e:
            logger.error(f"Error going to last move: {e}")

    def next_move(self, event=None):
        """Go to the next move in the current game."""
        if not self.current_game:
            return
        
        try:
            # Get moves list
            if isinstance(self.current_game, dict):
                pgn_str = self.current_game.get('pgn', '')
                if not pgn_str:
                    logger.warning("No moves found in game")
                    return
                    
                # Create a StringIO object with the PGN text
                pgn_io = io.StringIO(pgn_str)
                game = chess.pgn.read_game(pgn_io)
                
                if game:
                    moves = list(game.mainline_moves())
                else:
                    logger.warning("Could not parse moves for navigation")
                    return
            else:
                moves = list(self.current_game.mainline_moves())
            
            # Check if we can move forward
            if self.current_move_index < len(moves):
                self.current_move_index += 1
                self.update_pieces()
                self.update_moves_display()
            
        except Exception as e:
            logger.error(f"Error applying moves: {e}")

    def prev_move(self):
        if self.current_game and self.current_move_index > 0:
            self.current_move_index -= 1
            self.update_pieces()

    def on_select_game(self, event):
        selection = self.game_listbox.curselection()
        if selection:
            self.current_game = self.games_list[selection[0]]
            self.current_move_index = 0
            self.update_game_info()
            self.update_pieces()

    def resize_board(self, event):
        """Handle board resize while maintaining square aspect ratio."""
        if event.widget == self.canvas:
            # Get the container size
            width = self.board_container.winfo_width()
            height = self.board_container.winfo_height()
            
            # Calculate the maximum possible board size that fits while maintaining aspect ratio
            board_size = min(width - 20, height - 20)  # Subtract padding
            
            # Calculate new square size
            self.square_size = max(30, board_size // 8)  # Minimum square size of 30 pixels
            
            # Recalculate board size to ensure it's exactly 8 squares
            board_size = self.square_size * 8
            
            # Center the board in the canvas
            x_offset = (width - board_size) // 2
            y_offset = (height - board_size) // 2
            
            # Store offsets for piece placement
            self.board_x_offset = x_offset
            self.board_y_offset = y_offset
            
            # Recreate piece images at new size
            self.create_default_pieces()
            
            # Redraw everything
            self.draw_board()
            self.update_pieces()

    def update_pieces(self):
        """Update piece positions on the board."""
        try:
            # Clear existing pieces
            self.canvas.delete("piece")
            
            # Get current position from moves
            board = chess.Board()
            if self.current_game:
                if isinstance(self.current_game, dict):
                    pgn_str = self.current_game.get('pgn', '')
                    if pgn_str:
                        game = chess.pgn.read_game(io.StringIO(pgn_str))
                        if game:
                            moves = list(game.mainline_moves())
                            for move in moves[:self.current_move_index]:
                                board.push(move)
                else:
                    moves = list(self.current_game.mainline_moves())
                    for move in moves[:self.current_move_index]:
                        board.push(move)
            
            # Convert board position to our format
            position = [['.'] * 8 for _ in range(8)]
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece:
                    rank = chess.square_rank(square)
                    file = chess.square_file(square)
                    color = 'w' if piece.color else 'b'
                    piece_type = piece.symbol().upper()
                    position[7-rank][file] = color + piece_type
            
            # Draw pieces in their current positions
            for row in range(8):
                for col in range(8):
                    piece = position[row][col]
                    if piece != '.':
                        x = self.board_x_offset + (col * self.square_size) + (self.square_size // 2)
                        y = self.board_y_offset + (row * self.square_size) + (self.square_size // 2)
                        if piece in self.piece_images:
                            self.canvas.create_image(
                                x, y,
                                image=self.piece_images[piece],
                                tags="piece"
                            )
            
            # Update moves display
            self.update_moves_display()
            
        except Exception as e:
            logger.error(f"Error updating pieces: {e}")

    def update_moves_display(self):
        """Update the moves text display with clickable moves."""
        try:
            if hasattr(self, 'moves_text'):
                if self.current_game:
                    self.moves_text.delete('1.0', tk.END)
                    
                    # Configure tag for clickable moves
                    self.moves_text.tag_configure("clickable", 
                        foreground="lightblue",
                        underline=True)
                    
                    # Get moves
                    if isinstance(self.current_game, dict):
                        game = chess.pgn.read_game(io.StringIO(self.current_game.get('pgn', '')))
                        if game:
                            moves = list(game.mainline_moves())
                    else:
                        moves = list(self.current_game.mainline_moves())
                    
                    board = chess.Board()
                    
                    # Store move positions for click handling
                    self.move_positions = {}  # Clear previous positions
                    
                    for i, move in enumerate(moves):
                        # Add move number
                        if i % 2 == 0:
                            move_num = f"{i//2 + 1}. "
                            self.moves_text.insert(tk.END, move_num)
                        
                        # Add move (without space in clickable region)
                        move_san = board.san(move)
                        start_index = self.moves_text.index("end-1c")
                        self.moves_text.insert(tk.END, move_san, "clickable")
                        end_index = self.moves_text.index("end-1c")
                        # Add space after the clickable region
                        self.moves_text.insert(tk.END, " ")
                        
                        # Store the move position and index
                        self.move_positions[f"{start_index}:{end_index}"] = i
                        
                        board.push(move)
                    
                    # Bind click event
                    self.moves_text.tag_bind("clickable", "<Button-1>", self.on_move_click)
                    self.moves_text.config(cursor="hand2")
                    
        except Exception as e:
            logger.error(f"Error updating moves display: {e}")

    def on_move_click(self, event):
        """Handle click on a move in the moves display."""
        try:
            # Get click position
            click_index = self.moves_text.index(f"@{event.x},{event.y}")
            
            # Find which move was clicked
            for pos, move_index in self.move_positions.items():
                start, end = pos.split(":")
                if self.moves_text.compare(start, "<=", click_index) and \
                   self.moves_text.compare(click_index, "<=", end):
                    # Update position to this move
                    self.current_move_index = move_index + 1  # Add 1 because move_index is 0-based
                    self.update_pieces()
                    break
                    
        except Exception as e:
            logger.error(f"Error handling move click: {e}")

    def update_game_info(self):
        """Update the game information display."""
        if not self.current_game:
            self.info_text.delete('1.0', tk.END)
            return
        
        try:
            info = []
            # Handle both dictionary and chess.pgn.Game objects
            if isinstance(self.current_game, dict):
                game = self.current_game
                info.extend([
                    f"Event: {game.get('Event', game.get('event', 'Unknown'))}",
                    f"Site: {game.get('Site', game.get('site', 'Unknown'))}",
                    f"Date: {game.get('Date', game.get('date', '?'))}",
                    f"Round: {game.get('Round', game.get('round', '?'))}",
                    f"White: {game.get('White', game.get('white', '?'))}",
                    f"Black: {game.get('Black', game.get('black', '?'))}",
                    f"Result: {game.get('Result', game.get('result', '*'))}"
                ])
            else:
                headers = self.current_game.headers
                info.extend([
                    f"Event: {headers.get('Event', 'Unknown')}",
                    f"Site: {headers.get('Site', 'Unknown')}",
                    f"Date: {headers.get('Date', '?')}",
                    f"Round: {headers.get('Round', '?')}",
                    f"White: {headers.get('White', '?')}",
                    f"Black: {headers.get('Black', '?')}",
                    f"Result: {headers.get('Result', '*')}"
                ])
            
            self.info_text.delete('1.0', tk.END)
            self.info_text.insert('1.0', '\n'.join(info))
        except Exception as e:
            logger.error(f"Error updating game info: {e}")
            self.info_text.delete('1.0', tk.END)
            self.info_text.insert('1.0', "Error displaying game information")

    def initialize_engine(self):
        """Initialize the chess engine."""
        try:
            if self.engine_path and os.path.exists(self.engine_path):
                self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
                logger.info(f"Successfully initialized engine: {self.engine_path}")
        except Exception as e:
            logger.error(f"Failed to initialize engine: {e}")
            self.engine = None

    def toggle_analysis(self):
        """Toggle engine analysis on/off."""
        if self.analyzing:
            self.analyzing = False
            self.analyze_button.configure(text="start")
            self.analysis_text.delete('1.0', tk.END)
            return
        
        if not self.engine:
            self.initialize_engine()
            if not self.engine:
                return
        
        self.analyzing = True
        self.analyze_button.configure(text="stop")
        self.analyze_position()

    def analyze_position(self):
        """Analyze the current position with the chess engine."""
        if not self.engine or not self.analyzing:
            return
        
        try:
            # Get current position
            board = chess.Board()
            if isinstance(self.current_game, dict):
                game = chess.pgn.read_game(io.StringIO(self.current_game.get('pgn', '')))
            else:
                game = self.current_game
                
            if game:
                moves = list(game.mainline_moves())[:self.current_move_index]
                for move in moves:
                    board.push(move)
            
            # Clear previous analysis
            self.analysis_text.delete('1.0', tk.END)
            
            # Get analysis info
            info = self.engine.analyse(
                board,
                chess.engine.Limit(depth=self.engine_depth),
                multipv=self.num_lines
            )
            
            # Display each line of analysis
            for i, line in enumerate(info):
                score = line['score']  # Get the score directly
                pv = line.get('pv', [])
                
                # Format the score
                if score.is_mate():
                    score_str = f"M{score.mate()}"
                else:
                    cp_score = score.relative.score()
                    score_str = f"{cp_score/100:.2f}" if cp_score is not None else "0.00"
                
                # Format and display the entire line
                moves_str = board.variation_san(pv)
                analysis_line = f"Line {i+1}: {score_str} {moves_str}\n"
                self.analysis_text.insert(tk.END, analysis_line)
            
            self.analysis_text.see('1.0')  # Scroll to top
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            self.analysis_text.delete('1.0', tk.END)
            self.analysis_text.insert('1.0', f"Analysis error: {str(e)}")

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self.engine:
            self.engine.quit()

    def parse_pgn_moves(self, game_dict):
        """Convert PGN moves string into a chess.pgn.Game object."""
        try:
            # Create a new game
            game = chess.pgn.Game()
            
            # Set headers
            for key, value in game_dict.items():
                if key != 'moves':
                    game.headers[key] = value
            
            # Clean up moves string
            moves_str = game_dict.get('moves', '').strip()
            if not moves_str:
                logger.warning("No moves found in game")
                return None
                
            # Create a board for parsing moves
            board = chess.Board()
            node = game
            
            # Clean up moves string and split into tokens
            moves_str = moves_str.replace('  ', ' ')
            tokens = moves_str.split()
            
            current_move = []
            for token in tokens:
                # Skip move numbers and result
                if '.' in token or token in ['1-0', '0-1', '1/2-1/2', '*']:
                    continue
                
                try:
                    # Parse move in standard algebraic notation
                    move = board.parse_san(token)
                    node = node.add_variation(move)
                    board.push(move)
                except Exception as e:
                    logger.error(f"Error parsing move {token}: {e}")
                    continue
            
            return game
            
        except Exception as e:
            logger.error(f"Error converting moves to game object: {e}")
            return None

    def prev_game(self):
        """Go to the previous game in the list."""
        if not self.games_list:
            return
        
        current_index = self.game_listbox.curselection()
        if not current_index:
            return
        
        new_index = current_index[0] - 1
        if new_index >= 0:
            self.game_listbox.selection_clear(0, tk.END)
            self.game_listbox.selection_set(new_index)
            self.game_listbox.see(new_index)
            self.current_game = self.games_list[new_index]
            self.current_move_index = 0
            self.update_game_info()
            self.update_pieces()

    def next_game(self):
        """Go to the next game in the list."""
        if not self.games_list:
            return
        
        current_index = self.game_listbox.curselection()
        if not current_index:
            return
        
        new_index = current_index[0] + 1
        if new_index < len(self.games_list):
            self.game_listbox.selection_clear(0, tk.END)
            self.game_listbox.selection_set(new_index)
            self.game_listbox.see(new_index)
            self.current_game = self.games_list[new_index]
            self.current_move_index = 0
            self.update_game_info()
            self.update_pieces()

    def increase_lines(self):
        """Increase the number of analysis lines shown."""
        if self.num_lines < self.max_lines:
            self.num_lines += 1
            if self.analyzing:
                self.analyze_position()

    def decrease_lines(self):
        """Decrease the number of analysis lines shown."""
        if self.num_lines > 1:
            self.num_lines -= 1
            if self.analyzing:
                self.analyze_position()

    def setup_right_panel(self):
        """Set up the right panel with game info, analysis, and moves."""
        theme = self.themes[self.current_theme]
        
        # Game info display
        self.info_frame = ttk.LabelFrame(self.right_frame, text="info")
        self.info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_scroll = ttk.Scrollbar(self.info_frame)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.info_text = tk.Text(
            self.info_frame,
            height=6,
            wrap=tk.WORD,
            yscrollcommand=info_scroll.set,
            bg=theme['text_bg'],
            fg=theme['text_fg']
        )
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_scroll.config(command=self.info_text.yview)
        
        # Analysis frame
        self.analysis_frame = ttk.LabelFrame(self.right_frame, text="engine analysis")
        self.analysis_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Analysis controls
        self.analysis_controls = ttk.Frame(self.analysis_frame)
        self.analysis_controls.pack(fill=tk.X, padx=5, pady=2)
        
        self.analyze_button = ttk.Button(
            self.analysis_controls, 
            text="start",
            command=self.toggle_analysis
        )
        self.analyze_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.analysis_controls, text="Lines:").pack(side=tk.LEFT, padx=(10,2))
        ttk.Button(
            self.analysis_controls,
            text="-",
            width=2,
            command=self.decrease_lines
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            self.analysis_controls,
            text="+",
            width=2,
            command=self.increase_lines
        ).pack(side=tk.LEFT, padx=2)
        
        # Analysis text
        analysis_scroll = ttk.Scrollbar(self.analysis_frame)
        analysis_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.analysis_text = tk.Text(
            self.analysis_frame,
            height=6,
            wrap=tk.WORD,
            yscrollcommand=analysis_scroll.set,
            bg=theme['text_bg'],
            fg=theme['text_fg']
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        analysis_scroll.config(command=self.analysis_text.yview)
        
        # Moves display
        self.moves_frame = ttk.LabelFrame(self.right_frame, text="moves")
        self.moves_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        moves_scroll = ttk.Scrollbar(self.moves_frame)
        moves_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.moves_text = tk.Text(
            self.moves_frame,
            wrap=tk.WORD,
            yscrollcommand=moves_scroll.set,
            bg=theme['text_bg'],
            fg=theme['text_fg'],
            cursor="arrow"
        )
        self.moves_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        moves_scroll.config(command=self.moves_text.yview)
        
        # Initialize move positions dictionary
        self.move_positions = {}

    def prev_ply(self, event=None):
        """Go back one ply (half-move)."""
        if self.current_game and self.current_move_index > 0:
            self.current_move_index -= 1
            self.update_pieces()
        # Always prevent event from propagating
        return "break"

    def next_ply(self, event=None):
        """Go forward one ply (half-move)."""
        if not self.current_game:
            return "break"
        
        try:
            # Get moves list
            if isinstance(self.current_game, dict):
                pgn_str = self.current_game.get('pgn', '')
                if not pgn_str:
                    return "break"
                    
                game = chess.pgn.read_game(io.StringIO(pgn_str))
                if game:
                    moves = list(game.mainline_moves())
                else:
                    return "break"
            else:
                moves = list(self.current_game.mainline_moves())
            
            # Check if we can move forward one ply
            if self.current_move_index < len(moves):
                self.current_move_index += 1
                self.update_pieces()
            
        except Exception as e:
            logger.error(f"Error in next_ply: {e}")
        
        # Always prevent event from propagating
        return "break"

    def set_engine_depth(self):
        """Open dialog to set engine analysis depth."""
        dialog = tk.Toplevel(self)
        dialog.title("Set Analysis Depth")
        dialog.geometry("300x100")
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Analysis Depth:").pack(side=tk.LEFT, padx=5)
        
        depth_var = tk.StringVar(value=str(self.engine_depth))
        depth_entry = ttk.Entry(frame, textvariable=depth_var, width=5)
        depth_entry.pack(side=tk.LEFT, padx=5)
        
        def apply():
            try:
                new_depth = int(depth_var.get())
                if 1 <= new_depth <= 30:
                    self.engine_depth = new_depth
                    dialog.destroy()
                else:
                    messagebox.showwarning(title="Invalid Input", 
                                         message="Depth must be between 1 and 30")
            except ValueError:
                messagebox.showwarning(title="Invalid Input", 
                                     message="Please enter a valid number")
        
        ttk.Button(frame, text="Apply", command=apply).pack(side=tk.LEFT, padx=5)

    def update_engines_menu(self):
        """Update the engines menu with available engines."""
        # Clear existing engine entries after the separator
        last_index = self.engines_menu.index(tk.END)
        if last_index >= 2:  # Keep first three items (Select, Depth, separator)
            for i in range(last_index, 2, -1):
                self.engines_menu.delete(i)
        
        # Find all engine executables recursively
        engines_dir = os.path.join('res', 'engines')
        if not os.path.exists(engines_dir):
            os.makedirs(engines_dir)  # Create the directory if it doesn't exist
            return
        
        engine_paths = []
        for root, _, files in os.walk(engines_dir):
            for file in files:
                if file.endswith('.exe'):
                    full_path = os.path.join(root, file)
                    engine_paths.append(full_path)
        
        # Add each engine to the menu
        for engine_path in sorted(engine_paths):
            display_name = os.path.basename(engine_path)
            self.engines_menu.add_radiobutton(
                label=display_name,
                command=lambda p=engine_path: self.select_specific_engine(p),
                variable=self.selected_engine,
                value=engine_path
            )

    def select_specific_engine(self, engine_path):
        """Select a specific engine from the menu."""
        try:
            # Stop current engine if running
            if self.engine:
                self.analyzing = False
                self.engine.quit()
                self.engine = None
            
            self.engine_path = engine_path
            self.initialize_engine()
            
            # Update menu selection
            self.selected_engine.set(engine_path)
            
        except Exception as e:
            messagebox.showerror(
                title="Engine Error", 
                message=f"Failed to load engine: {str(e)}"
            )

    def select_engine(self):
        """Open file dialog to select an engine."""
        engine_path = filedialog.askopenfilename(
            title="Select Chess Engine",
            initialdir=os.path.join('res', 'engines'),
            filetypes=[
                ("Executable files", "*.exe"),
                ("All files", "*.*")
            ]
        )
        
        if engine_path:
            self.select_specific_engine(engine_path)

    def open_most_recent_pgn(self):
        """Open the most recent PGN file from the /in directory."""
        in_dir = os.path.join('in')
        if not os.path.exists(in_dir):
            os.makedirs(in_dir)
            return
        
        # Find all PGN files in the directory
        pgn_files = []
        for file in os.listdir(in_dir):
            if file.endswith('.pgn'):
                full_path = os.path.join(in_dir, file)
                pgn_files.append((full_path, os.path.getmtime(full_path)))
        
        # Sort by modification time and get the most recent
        if pgn_files:
            most_recent = sorted(pgn_files, key=lambda x: x[1], reverse=True)[0][0]
            self.open_pgn(most_recent)

    def find_default_engine(self):
        """Find and load the default engine (Stockfish preferred)."""
        engines_dir = os.path.join('res', 'engines')
        if not os.path.exists(engines_dir):
            os.makedirs(engines_dir)
            return
        
        engine_paths = []
        # First, look for Stockfish
        for root, _, files in os.walk(engines_dir):
            for file in files:
                if file.lower().startswith('stockfish') and file.endswith('.exe'):
                    self.select_specific_engine(os.path.join(root, file))
                    return
                if file.endswith('.exe'):
                    engine_paths.append(os.path.join(root, file))
        
        # If Stockfish not found, use most recent engine
        if engine_paths:
            most_recent = max(engine_paths, key=os.path.getmtime)
            self.select_specific_engine(most_recent)

    def on_closing(self):
        """Clean up resources and quit."""
        try:
            if self.engine:
                self.analyzing = False
                self.engine.quit()
                self.engine = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            self.root.quit()
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessViewer(root)
    try:
        root.mainloop()
    finally:
        # Ensure cleanup happens even on keyboard interrupt
        if app.engine:
            app.engine.quit()
        root.quit()
        root.destroy()
