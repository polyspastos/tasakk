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

class ChessViewer:
    def __init__(self, root):
        print("Initializing ChessViewer...")
        self.root = root
        
        # Initialize components
        self.db = None
        self.parser = PGNParser()
        
        # Initialize variables
        self.current_game = None
        self.current_move_index = 0
        self.games_list = []
        self.piece_images = {}
        self.square_size = 45
        
        print("Creating menu...")
        self.create_menu()
        
        print("Setting up GUI...")
        self.setup_gui()
        
        print("Creating pieces...")
        self.create_default_pieces()
        
        print("Drawing board...")
        self.draw_board()
        
        # Bind keyboard events
        print("Binding events...")
        self.root.bind('<Left>', lambda e: self.prev_move())
        self.root.bind('<Right>', lambda e: self.next_move())
        self.root.bind('<Up>', lambda e: self.first_move())
        self.root.bind('<Down>', lambda e: self.last_move())
        self.root.bind('<Configure>', self.on_resize)
        
        print("ChessViewer initialization complete")

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open PGN", command=self.open_pgn)
        file_menu.add_command(label="Open Database", command=self.open_database)
        file_menu.add_command(label="Save to Database", command=self.save_to_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Flip Board", command=self.flip_board)

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
        print("Setting up right panel...")
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=2)
        
        # Board canvas
        self.canvas = tk.Canvas(self.right_frame, width=400, height=400, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
                    print(f"Creating piece {piece_key}...")
                    
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
                    
                    print(f"Created piece {piece_key}")
                
        except Exception as e:
            print(f"Error creating pieces: {e}")
            import traceback
            traceback.print_exc()
        
        print("Finished create_default_pieces")

    def draw_board(self):
        self.canvas.delete("all")
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        self.square_size = min(width, height) // 8
        
        x_offset = (width - self.square_size * 8) // 2
        y_offset = (height - self.square_size * 8) // 2
        
        # Draw squares
        for row in range(8):
            for col in range(8):
                x1 = x_offset + col * self.square_size
                y1 = y_offset + row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                
                color = "#DDB88C" if (row + col) % 2 == 0 else "#A66D4F"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                
                # Add coordinates
                if col == 0:
                    self.canvas.create_text(
                        x1 - 10, y1 + self.square_size/2,
                        text=str(8-row), fill="black"
                    )
                if row == 7:
                    self.canvas.create_text(
                        x1 + self.square_size/2, y2 + 10,
                        text=chr(97 + col), fill="black"
                    )

        self.update_pieces()

    def update_pieces(self):
        if not hasattr(self, 'canvas'):
            return
            
        board = chess.Board() if not self.current_game else self.current_game.board()
        
        if self.current_game:
            moves = list(self.current_game.mainline_moves())
            for move in moves[:self.current_move_index]:
                board.push(move)

        self.canvas.delete("piece")
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        x_offset = (width - self.square_size * 8) // 2
        y_offset = (height - self.square_size * 8) // 2
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                col = chess.square_file(square)
                row = 7 - chess.square_rank(square)
                
                x = x_offset + col * self.square_size + self.square_size // 2
                y = y_offset + row * self.square_size + self.square_size // 2
                
                color = 'w' if piece.color == chess.WHITE else 'b'
                piece_key = color + piece.symbol().upper()
                
                self.canvas.create_image(x, y, image=self.piece_images[piece_key], tags="piece")

        self.update_moves_display()

    def update_moves_display(self):
        """Update the moves text display."""
        try:
            if hasattr(self, 'moves_text'):
                self.moves_text.delete('1.0', tk.END)
                if self.current_game:
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
        if not self.current_game:
            self.info_text.delete('1.0', tk.END)
            return
            
        info = []
        headers = self.current_game.headers
        info.append(f"Event: {headers.get('Event', 'Unknown')}")
        info.append(f"Site: {headers.get('Site', 'Unknown')}")
        info.append(f"Date: {headers.get('Date', '?')}")
        info.append(f"White: {headers.get('White', '?')} ({headers.get('WhiteElo', '?')})")
        info.append(f"Black: {headers.get('Black', '?')} ({headers.get('BlackElo', '?')})")
        info.append(f"Result: {headers.get('Result', '?')}")
        
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0', '\n'.join(info))

    def open_pgn(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            self.games_list = self.parser.parse_file(file_path)
            self.game_listbox.delete(0, tk.END)
            
            for game in self.games_list:
                game_str = format_game_display(game)
                self.game_listbox.insert(tk.END, game_str)
            
            if self.parser.errors:
                messagebox.showwarning(
                    "Parser Warnings",
                    f"Some games could not be parsed:\n\n" + "\n".join(self.parser.errors[:5])
                )
            
            self.game_listbox.bind('<<ListboxSelect>>', self.on_select_game)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading PGN file: {str(e)}")

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
                game_str = format_game_display(game)
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
                game_str = format_game_display(game)
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

    def next_move(self):
        if self.current_game:
            moves = list(self.current_game.mainline_moves())
            if self.current_move_index < len(moves):
                self.current_move_index += 1
                self.update_pieces()

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

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessViewer(root)
    root.mainloop()
