import chess.pgn
from typing import List, Dict, Optional
import logging
import io

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

class PGNParser:
    """Parser for PGN chess game files."""
    
    def __init__(self):
        self.games: List[Dict] = []
        self.errors: List[str] = []

    def parse_file(self, filename):
        """Parse a PGN file and return list of games."""
        try:
            with open(filename, encoding='utf-8-sig') as pgn:
                games = []
                while True:
                    game = chess.pgn.read_game(pgn)
                    if game is None:
                        break
                    # Return the chess.pgn.Game object directly
                    games.append(game)
                
                logger.info(f"Successfully parsed {len(games)} games from {filename}")
                return games
                
        except Exception as e:
            self.errors.append(f"Error parsing file {filename}: {str(e)}")
            logger.error(f"Error parsing PGN file: {e}")
            return None

    def _parse_header_line(self, line: str) -> tuple[Optional[str], Optional[str]]:
        """Parse a single header line."""
        try:
            if ']' not in line:
                return None, None
                
            # Extract tag and value
            tag_start = line.find('[') + 1
            tag_end = line.find(' ')
            value_start = line.find('"') + 1
            value_end = line.rfind('"')
            
            if tag_end > tag_start and value_end > value_start:
                tag = line[tag_start:tag_end]
                value = line[value_start:value_end]
                return tag, value
                
        except Exception as e:
            logger.debug(f"Failed to parse header line '{line}': {e}")
        
        return None, None

    def _create_game_dict(self, headers: Dict[str, str], moves: List[str]) -> Optional[Dict]:
        """Create a game dictionary from headers and moves."""
        try:
            # Clean and join moves, preserving the PGN format
            moves_str = ' '.join(moves)
            # Clean up extra whitespace but preserve the moves
            moves_str = ' '.join(moves_str.split())
            
            # Create game dictionary with required fields
            game_dict = {
                'White': headers.get('White', 'Unknown'),
                'Black': headers.get('Black', 'Unknown'),
                'Result': headers.get('Result', '*'),
                'pgn': moves_str,  # Store the raw PGN moves
                'moves': moves_str  # Keep this for compatibility
            }
            
            # Add optional fields if they exist
            optional_fields = ['Event', 'Site', 'Date', 'Round']
            for field in optional_fields:
                if field in headers:
                    game_dict[field] = headers[field]
            
            # Basic validation
            if not moves_str or moves_str.isspace():
                logger.warning(f"No moves found for game: {game_dict['White']} vs {game_dict['Black']}")
                return None
                
            logger.debug(f"Created game: {game_dict['White']} vs {game_dict['Black']} with moves: {moves_str[:50]}...")
            return game_dict
            
        except Exception as e:
            logger.error(f"Failed to create game dictionary: {e}")
            return None

    def parse_game(self, pgn_text):
        """Parse a single game from PGN text."""
        try:
            game = chess.pgn.read_game(io.StringIO(pgn_text))
            if game:
                # Extract headers
                headers = game.headers
                return {
                    'event': headers.get('Event', '?'),
                    'site': headers.get('Site', '?'),
                    'date': headers.get('Date', '?'),
                    'round': headers.get('Round', '?'),
                    'white': headers.get('White', 'Unknown'),
                    'black': headers.get('Black', 'Unknown'),
                    'result': headers.get('Result', '?'),
                    'white_elo': headers.get('WhiteElo', '0'),
                    'black_elo': headers.get('BlackElo', '0'),
                    'eco': headers.get('ECO', '?'),
                    'pgn': pgn_text
                }
        except Exception as e:
            self.errors.append(f"Error parsing game: {str(e)}")
            return None
