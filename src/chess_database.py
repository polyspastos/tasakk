import sqlite3
from datetime import datetime

class ChessDatabase:
    def __init__(self, db_path):
        """Initialize database with path to SQLite file."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """Connect to database and create tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign key support
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self._create_tables()
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        self.cursor.executescript('''
            -- Players table
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                first_seen_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_games INTEGER DEFAULT 0,
                UNIQUE(name)
            );

            -- Games table
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                site TEXT,
                date TEXT,
                round TEXT,
                subround TEXT,
                white_id INTEGER,
                black_id INTEGER,
                result TEXT,
                white_elo INTEGER,
                black_elo INTEGER,
                eco TEXT,
                moves TEXT,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (white_id) REFERENCES players(id),
                FOREIGN KEY (black_id) REFERENCES players(id)
            );

            -- Create indexes for better query performance
            CREATE INDEX IF NOT EXISTS idx_white_player ON games(white_id);
            CREATE INDEX IF NOT EXISTS idx_black_player ON games(black_id);
            CREATE INDEX IF NOT EXISTS idx_event ON games(event);
            CREATE INDEX IF NOT EXISTS idx_date ON games(date);
            CREATE INDEX IF NOT EXISTS idx_player_name ON players(name);
        ''')
        self.conn.commit()

    def add_game(self, game_data):
        """Add a single game to the database."""
        try:
            # Add or update players
            white_id = self._get_or_create_player(game_data['white'])
            black_id = self._get_or_create_player(game_data['black'])

            # Insert game
            self.cursor.execute('''
                INSERT INTO games (
                    event, site, date, round, subround,
                    white_id, black_id, result,
                    white_elo, black_elo, eco, moves
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_data['event'], game_data['site'], game_data['date'],
                game_data['round'], game_data['subround'],
                white_id, black_id, game_data['result'],
                game_data['white_elo'], game_data['black_elo'],
                game_data.get('eco'), ','.join(game_data['moves'])
            ))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error adding game: {e}")
            return False

    def _get_or_create_player(self, name):
        """Get player ID or create new player if doesn't exist."""
        self.cursor.execute('SELECT id FROM players WHERE name = ?', (name,))
        result = self.cursor.fetchone()
        
        if result:
            # Update last seen date
            self.cursor.execute('''
                UPDATE players 
                SET last_seen_date = CURRENT_TIMESTAMP,
                    total_games = total_games + 1
                WHERE id = ?
            ''', (result[0],))
            return result[0]
        
        # Create new player
        self.cursor.execute('''
            INSERT INTO players (name) VALUES (?)
        ''', (name,))
        return self.cursor.lastrowid

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

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
