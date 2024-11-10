import sqlite3
from datetime import datetime
import logging
import os

# Set up logging
def setup_logger():
    """Set up module-specific logger."""
    logger = logging.getLogger(__name__)
    
    # If the logger already has handlers, assume it's configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler('logs/chess_database.log')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logger()

class ChessDatabase:
    def __init__(self, db_path):
        """Initialize database with path to SQLite file."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        logger.info(f"Initializing database at {db_path}")

    def connect(self):
        """Connect to database and create tables if they don't exist."""
        try:
            logger.info(f"Connecting to database at {self.db_path}")
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()
            self._create_tables()
            logger.info("Successfully connected to database")
            return True
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False

    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        self.cursor.executescript('''
            -- Players table
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                first_seen_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_games INTEGER DEFAULT 0
            );

            -- Games table
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                site TEXT,
                date TEXT,
                round TEXT,
                white_id INTEGER,
                black_id INTEGER,
                result TEXT,
                white_elo INTEGER,
                black_elo INTEGER,
                eco TEXT,
                pgn TEXT NOT NULL,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (white_id) REFERENCES players(id),
                FOREIGN KEY (black_id) REFERENCES players(id)
            );

            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_player_name ON players(name);
            CREATE INDEX IF NOT EXISTS idx_white_player ON games(white_id);
            CREATE INDEX IF NOT EXISTS idx_black_player ON games(black_id);
        ''')
        self.conn.commit()

    def get_or_create_player(self, name):
        """Get player ID or create new player if doesn't exist."""
        if not name or name == '?' or name == '':
            logger.warning(f"Invalid player name: {name}")
            # Create a special 'Unknown' player if it doesn't exist
            name = 'Unknown'
            
        try:
            # First try to get existing player
            self.cursor.execute('''
                SELECT id, total_games FROM players 
                WHERE name = ?
            ''', (name,))
            result = self.cursor.fetchone()
            
            if result:
                player_id = result[0]
                # Update last seen and total games
                self.cursor.execute('''
                    UPDATE players 
                    SET last_seen_date = CURRENT_TIMESTAMP,
                        total_games = total_games + 1
                    WHERE id = ?
                ''', (player_id,))
                self.conn.commit()
                logger.info(f"Updated existing player: {name} (ID: {player_id})")
                return player_id
            
            # Player doesn't exist, create new one
            self.cursor.execute('''
                INSERT INTO players (name, total_games)
                VALUES (?, 1)
            ''', (name,))
            self.conn.commit()
            new_id = self.cursor.lastrowid
            logger.info(f"Created new player: {name} (ID: {new_id})")
            return new_id
            
        except Exception as e:
            logger.error(f"Error managing player {name}: {e}")
            self.conn.rollback()
            return None

    def add_game(self, game_data):
        """Add a single game to the database."""
        if not self.conn:
            if not self.connect():
                return False
                
        try:
            # Get or create players first
            white_name = game_data.get('white', 'Unknown')
            black_name = game_data.get('black', 'Unknown')
            
            print(f"Processing game: {white_name} vs {black_name}")
            
            # Get player IDs
            white_id = self.get_or_create_player(white_name)
            black_id = self.get_or_create_player(black_name)
            
            if white_id is None or black_id is None:
                raise Exception("Failed to create player records")
            
            print(f"Player IDs - White: {white_id}, Black: {black_id}")
            
            # Insert game with player IDs
            self.cursor.execute('''
                INSERT INTO games (
                    event, site, date, round,
                    white_id, black_id, result,
                    white_elo, black_elo, eco, pgn
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_data.get('event', '?'),
                game_data.get('site', '?'),
                game_data.get('date', '?'),
                game_data.get('round', '?'),
                white_id,  # Use the actual player IDs
                black_id,  # Use the actual player IDs
                game_data.get('result', '?'),
                game_data.get('white_elo', 0),
                game_data.get('black_elo', 0),
                game_data.get('eco', '?'),
                game_data.get('pgn', '')
            ))
            
            self.conn.commit()
            print(f"Game added successfully with IDs {white_id} vs {black_id}")
            return True
            
        except Exception as e:
            print(f"Error adding game: {e}")
            self.conn.rollback()
            return False

    def get_games(self, filters=None, limit=None, offset=None):
        """
        Retrieve games from database with optional filters.
        
        Args:
            filters (dict): Dictionary of column:value pairs to filter by
            limit (int): Maximum number of games to return
            offset (int): Number of games to skip
        """
        query = '''
            SELECT 
                g.*,
                w.name as white_name,
                b.name as black_name
            FROM games g
            JOIN players w ON g.white_id = w.id
            JOIN players b ON g.black_id = b.id
        '''
        
        params = []
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = ?")
                params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY g.date DESC, g.id DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_player_stats(self):
        """Get statistics about players in the database."""
        try:
            self.cursor.execute('''
                SELECT 
                    name,
                    total_games,
                    first_seen_date,
                    last_seen_date
                FROM players
                ORDER BY total_games DESC
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting player stats: {e}")
            return []

    def close(self):
        """Close database connection."""
        if self.conn:
            try:
                logger.info("Closing database connection")
                self.conn.commit()
                self.conn.close()
                logger.info("Database connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing database: {e}")
            finally:
                self.conn = None
                self.cursor = None

    def get_all_games(self):
        """Get all games with player names from database."""
        if not self.conn:
            if not self.connect():
                return None
                
        try:
            # Join with players table to get actual names
            self.cursor.execute('''
                SELECT 
                    g.*,
                    w.name as white_name,
                    b.name as black_name
                FROM games g
                JOIN players w ON g.white_id = w.id
                JOIN players b ON g.black_id = b.id
                ORDER BY g.import_date DESC
            ''')
            
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Error getting games: {e}")
            return None
