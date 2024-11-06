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
                'menu_fg': 'black'
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
                'menu_fg': '#ffffff'
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
        self.eval_var = tk.StringVar(value="Evaluation: 0.0")
        
        print("Creating menu...")
        self.create_menu()
        
        print("Setting up GUI...")
        self.setup_gui()
        
        print("Creating pieces...")
        self.create_default_pieces()
        
        print("Drawing board...")
        self.draw_board()
        
        # Show welcome screen
        self.after(100, lambda: WelcomeScreen(self))
        
        # Bind keyboard events
        print("Binding events...")
        self.root.bind('<Left>', lambda e: self.prev_move())
        self.root.bind('<Right>', lambda e: self.next_move())
        self.root.bind('<Up>', lambda e: self.first_move())
        self.root.bind('<Down>', lambda e: self.last_move())
        self.root.bind('<Configure>', self.on_resize)
        
        print("ChessViewer initialization complete")

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
        # Main container with paned window
        print("Creating main paned window...")
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel setup
        print("Setting up left panel...")
        self.setup_left_panel()
        
        # Right panel setup
        print("Setting up right panel...")
        self.setup_right_panel()

    def setup_left_panel(self):
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=1)
        
        # Search frame
        self.search_frame = ttk.Frame(self.left_frame)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(self.search_frame, text="Search", command=self.search_games).pack(side=tk.RIGHT)

        # Games list
        self.games_frame = ttk.LabelFrame(self.left_frame, text="Games")
        self.games_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.game_listbox = tk.Listbox(self.games_frame, selectmode=tk.EXTENDED)
        scrollbar = ttk.Scrollbar(self.games_frame, orient=tk.VERTICAL)
        self.game_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.game_listbox.yview)
        
        self.game_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_right_panel(self):
        """Set up the right panel with consistent dark theme."""
        theme = self.themes[self.current_theme]
        
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=2)
        
        # Game info display
        self.info_frame = ttk.LabelFrame(self.right_frame, text="Game Info")
        self.info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add scrollbar to info text
        info_scroll = ttk.Scrollbar(self.info_frame)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.info_text = tk.Text(
            self.info_frame,
            height=6,
            wrap=tk.WORD,
            yscrollcommand=info_scroll.set,
            bg=theme['text_bg'],
            fg=theme['text_fg'],
            insertbackground=theme['text_fg']
        )
        self.info_text.pack(fill=tk.X, padx=5, pady=5)
        info_scroll.config(command=self.info_text.yview)
        
        # Board canvas
        self.canvas = tk.Canvas(self.right_frame, width=400, height=400, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Evaluation display
        eval_frame = ttk.Frame(self.right_frame)
        eval_frame.pack(fill=tk.X, padx=5)
        
        eval_label = ttk.Label(eval_frame, textvariable=self.eval_var)
        eval_label.pack(side=tk.LEFT, padx=5)
        
        analyze_btn = ttk.Button(eval_frame, text="Analyze Position", 
                               command=self.toggle_analysis)
        analyze_btn.pack(side=tk.RIGHT, padx=5)
        
        # Controls frame
        self.controls = ttk.Frame(self.right_frame)
        self.controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(self.controls, text="<<", command=self.first_move).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls, text="<", command=self.prev_move).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls, text=">", command=self.next_move).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.controls, text=">>", command=self.last_move).pack(side=tk.LEFT, padx=2)
        
        # Moves display
        self.moves_frame = ttk.LabelFrame(self.right_frame, text="Moves")
        self.moves_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add scrollbar to moves text
        moves_scroll = ttk.Scrollbar(self.moves_frame)
        moves_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.moves_text = tk.Text(self.moves_frame, height=4, wrap=tk.WORD, 
                                 yscrollcommand=moves_scroll.set)
        self.moves_text.pack(fill=tk.X, padx=5, pady=5)
        moves_scroll.config(command=self.moves_text.yview)

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
        """Draw the chess board with current position."""
        self.create_squares()
        self.draw_position()

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

    def create_squares(self):
        # Clear existing squares
        self.canvas.delete("square")
        
        # Create new squares
        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size
                y1 = row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                
                # Determine square color
                color = self.light_squares if (row + col) % 2 == 0 else self.dark_squares
                
                # Create square
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags="square")

    def draw_position(self):
        # Clear existing pieces
        self.canvas.delete("piece")
        
        # Draw pieces in their current positions
        for row in range(8):
            for col in range(8):
                piece = self.position[row][col]
                if piece != '.':
                    x = col * self.square_size
                    y = row * self.square_size
                    self.canvas.create_image(x, y, image=self.piece_images[piece], 
                                           anchor="nw", tags="piece")

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

    def on_resize(self, event):
        if event.widget == self.root:
            self.create_default_pieces()
            self.draw_board()

    # Navigation methods
    def first_move(self):
        if self.current_game:
            self.current_move_index = 0
            self.update_pieces()

    def last_move(self):
        if self.current_game:
            moves = list(self.current_game.mainline_moves())
            self.current_move_index = len(moves)
            self.update_pieces()

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

    def resize_board(self, event=None):
        # Get the new window size
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Calculate the maximum possible board size that fits the window
        # while maintaining the aspect ratio of 1:1
        board_size = min(width, height)
        
        # Calculate the square size based on the board size
        self.square_size = board_size // 8
        
        # Recalculate board size to ensure it's exactly 8 squares
        board_size = self.square_size * 8
        
        # Center the board in the window
        x_offset = (width - board_size) // 2
        y_offset = (height - board_size) // 2
        
        # Update the canvas size and position
        self.canvas.place(x=x_offset, y=y_offset, width=board_size, height=board_size)
        
        # Recreate the squares with new size
        self.create_squares()
        
        # Recreate the pieces with new size
        self.create_default_pieces()
        
        # Redraw the current position
        self.draw_position()

    def update_pieces(self):
        """Update the chess pieces on the board."""
        try:
            # Create a new board
            board = chess.Board()
            
            # Apply moves up to current index
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

            self.canvas.delete("piece")
            
            # Update board display
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece:
                    col = chess.square_file(square)
                    row = 7 - chess.square_rank(square)
                    
                    x = col * self.square_size + self.square_size // 2
                    y = row * self.square_size + self.square_size // 2
                    
                    color = 'w' if piece.color == chess.WHITE else 'b'
                    piece_key = color + piece.symbol().upper()
                    
                    self.canvas.create_image(x, y, image=self.piece_images[piece_key], tags="piece")

            # Update moves display
            self.update_moves_display()
            
            # Update evaluation if analyzing
            if self.analyzing:
                self.analyze_position()
            
        except Exception as e:
            logger.error(f"Error updating pieces: {e}")

    def update_moves_display(self):
        """Update the moves text display."""
        try:
            if hasattr(self, 'moves_text'):
                self.moves_text.delete('1.0', tk.END)
                if self.current_game:
                    if isinstance(self.current_game, dict):
                        # If it's a dictionary, get moves from PGN
                        game = chess.pgn.read_game(io.StringIO(self.current_game.get('pgn', '')))
                        if game:
                            moves = list(game.mainline_moves())
                    else:
                        # If it's a chess.pgn.Game object
                        moves = list(self.current_game.mainline_moves())
                    
                    board = chess.Board()
                    move_text = []
                    
                    for i, move in enumerate(moves[:self.current_move_index]):
                        if i % 2 == 0:
                            move_text.append(f"{i//2 + 1}.")
                        move_text.append(board.san(move))
                        board.push(move)
                    
                    self.moves_text.insert('1.0', ' '.join(move_text))
        except Exception as e:
            print(f"Error updating moves display: {e}")

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
        """Initialize the Stockfish engine."""
        if self.engine is None and self.engine_path and os.path.exists(self.engine_path):
            try:
                import chess.engine
                self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
                self.engine.configure({"Threads": 2, "Hash": 128})
            except Exception as e:
                messagebox.showerror("Engine Error", f"Failed to start engine: {str(e)}")
                self.engine = None

    def toggle_analysis(self):
        """Toggle engine analysis on/off."""
        if self.analyzing:
            self.analyzing = False
            self.eval_var.set("Evaluation: 0.0")
            return
        
        if not self.engine:
            self.initialize_engine()
            if not self.engine:
                return
        
        self.analyzing = True
        self.analyze_position()

    def analyze_position(self):
        """Analyze the current position."""
        if not self.analyzing or not self.engine:
            return
        
        try:
            # Get current position
            board = chess.Board()
            if self.current_game:
                moves = list(self.current_game.mainline_moves())
                for move in moves[:self.current_move_index]:
                    board.push(move)
            
            # Get engine evaluation
            info = self.engine.analyse(board, chess.engine.Limit(depth=self.engine_depth))
            score = info["score"].white()
            
            # Convert score to string
            if score.is_mate():
                eval_str = f"Mate in {score.mate()}"
            else:
                eval_str = f"{score.score() / 100:.2f}"
            
            self.eval_var.set(f"Evaluation: {eval_str}")
            
        except Exception as e:
            print(f"Analysis error: {e}")
            self.analyzing = False

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

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessViewer(root)
    root.mainloop()
