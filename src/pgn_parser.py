import chess.pgn
from typing import List, Dict, Optional
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

class PGNParser:
    """Parser for PGN chess game files."""
    
    def __init__(self):
        self.games: List[Dict] = []
        self.errors: List[str] = []

    def parse_file(self, file_path: str) -> List[Dict]:
        """Parse a PGN file and return a list of games."""
        games = []
        current_headers = {}
        current_moves = []
        in_headers = True  # Start in header section
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to open PGN file {file_path}: {e}")
            return []

        try:
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Empty line marks separation between headers and moves
                if not line:
                    in_headers = True  # Reset to headers for next game
                    if current_headers and current_moves:
                        game = self._create_game_dict(current_headers, current_moves)
                        if game:
                            games.append(game)
                        current_headers = {}
                        current_moves = []
                    continue

                # Parse headers
                if line.startswith('['):
                    in_headers = True
                    try:
                        tag, value = self._parse_header_line(line)
                        if tag and value:
                            current_headers[tag] = value
                    except Exception as e:
                        logger.warning(f"Error parsing header at line {line_num}: {e}")
                # Parse moves (any non-header line after headers section)
                elif not in_headers or not line.startswith('['):
                    in_headers = False
                    current_moves.append(line)

            # Don't forget the last game
            if current_headers and current_moves:
                game = self._create_game_dict(current_headers, current_moves)
                if game:
                    games.append(game)

            logger.info(f"Successfully parsed {len(games)} games from {file_path}")
            return games

        except Exception as e:
            logger.error(f"Error parsing PGN file: {e}")
            return []

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
