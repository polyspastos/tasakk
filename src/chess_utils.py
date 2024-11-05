from typing import Dict, Optional
import re

def parse_elo(elo_str: str) -> Optional[int]:
    """
    Parse ELO rating string to integer.
    Returns None for invalid or missing ratings.
    """
    if not elo_str or elo_str == '?' or elo_str == '-':
        return None
        
    try:
        # Extract numbers only
        elo_num = re.sub(r'[^\d]', '', elo_str)
        rating = int(elo_num)
        # Validate reasonable ELO range
        if 100 <= rating <= 3000:
            return rating
    except:
        pass
        
    return None

def format_game_display(game_data: Dict) -> str:
    """Format game data for display in GUI."""
    display = []
    
    # Add players and result
    display.append(f"{game_data['white']} ({game_data.get('white_elo', '?')})")
    display.append("vs")
    display.append(f"{game_data['black']} ({game_data.get('black_elo', '?')})")
    display.append(f"[{game_data['result']}]")
    
    # Add event and date
    if game_data.get('event'):
        display.append(f"- {game_data['event']}")
    if game_data.get('date'):
        display.append(f"({game_data['date']})")
        
    return " ".join(display)

def get_result_score(result: str) -> float:
    """Convert chess result string to numerical score."""
    result_map = {
        '1-0': 1.0,
        '0-1': 0.0,
        '1/2-1/2': 0.5,
        '*': None
    }
    return result_map.get(result)
