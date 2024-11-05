import chess.pgn
import io
from datetime import datetime
from typing import List, Dict, Optional

class PGNParser:
    """Parser for PGN chess game files."""
    
    def __init__(self):
        self.games: List[Dict] = []
        self.errors: List[str] = []

    def parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse a PGN file and extract games with their metadata.
        
        Args:
            file_path: Path to the PGN file
            
        Returns:
            List of dictionaries containing game data
        """
        self.games = []
        self.errors = []
        
        try:
            with open(file_path, encoding='utf-8-sig') as pgn_file:
                while True:
                    try:
                        game = chess.pgn.read_game(pgn_file)
                        if game is None:
                            break
                            
                        game_data = self._process_game(game)
                        if game_data:
                            self.games.append(game_data)
                            
                    except Exception as e:
                        self.errors.append(f"Error parsing game: {str(e)}")
                        continue
                        
        except Exception as e:
            raise Exception(f"Error opening file {file_path}: {str(e)}")
            
        return self.games

    def _process_game(self, game: chess.pgn.Game) -> Optional[Dict]:
        """Process a single game and extract relevant data."""
        try:
            # Extract round and subround
            round_data = self._parse_round(game.headers.get('Round', '?'))
            
            # Get moves in SAN notation
            moves = self._get_moves(game)
            
            return {
                'event': game.headers.get('Event', 'Unknown'),
                'site': game.headers.get('Site', 'Unknown'),
                'date': self._parse_date(game.headers.get('Date', '????-??-??')),
                'round': round_data['round'],
                'subround': round_data['subround'],
                'white': game.headers.get('White', 'Unknown'),
                'black': game.headers.get('Black', 'Unknown'),
                'result': game.headers.get('Result', '*'),
                'white_elo': game.headers.get('WhiteElo', '?'),
                'black_elo': game.headers.get('BlackElo', '?'),
                'eco': game.headers.get('ECO', '?'),
                'moves': moves
            }
            
        except Exception as e:
            self.errors.append(f"Error processing game: {str(e)}")
            return None

    def _parse_round(self, round_str: str) -> Dict[str, Optional[str]]:
        """
        Parse round string into round and subround.
        Examples: "1" -> {round: "1", subround: None}
                 "1.1" -> {round: "1", subround: "1"}
                 "Quarter-final" -> {round: "Quarter-final", subround: None}
        """
        try:
            if '.' in round_str:
                main_round, sub_round = round_str.split('.', 1)
                return {'round': main_round, 'subround': sub_round}
            return {'round': round_str, 'subround': None}
        except:
            return {'round': '?', 'subround': None}

    def _parse_date(self, date_str: str) -> str:
        """
        Parse PGN date string into standardized format.
        Handles partial dates (????-??-??) and returns them unchanged.
        """
        if '?' in date_str:
            return date_str
            
        try:
            # Try to parse the date
            parts = date_str.split('.')
            if len(parts) == 3:
                year, month, day = parts
                return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        except:
            pass
            
        return date_str

    def _get_moves(self, game: chess.pgn.Game) -> List[str]:
        """Extract moves from game in SAN notation."""
        moves = []
        board = game.board()
        
        for move in game.mainline_moves():
            try:
                moves.append(board.san(move))
                board.push(move)
            except Exception as e:
                self.errors.append(f"Error processing move: {str(e)}")
                break
                
        return moves
