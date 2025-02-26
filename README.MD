# Chess Viewer

A cross-platform chess game viewer with engine analysis support, built with Python and Tkinter.

## Features

- PGN file support (load and save)
- SQLite database integration for game storage
- Stockfish engine analysis integration
- Dark and light themes
- Move navigation with keyboard shortcuts
- Game list navigation
- Multiple analysis lines support
- Cross-platform compatibility (Windows, Linux, macOS)

## Setup

- put pgns/dbs in the 'in' folder
- the 'data' folder is used for output
- the 'res' folder contains the engine and pieces

## Requirements

- Python 3.8 or higher
- Dependencies:
  - python-chess
  - Pillow
  - tkinter

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/chess-viewer.git
cd chess-viewer
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install imagemagick separately if need be:
https://imagemagick.org/script/download.php

4. Run the application:
```bash
python run.py
```

## Keyboard Shortcuts

- `Left Arrow`: Previous move
- `Right Arrow`: Next move
- `Up Arrow`: First move
- `Down Arrow`: Last move
- `N`: Next game
- `P`: Previous game

## Building Executable

### Step 1: Install PyInstaller
```bash
pip install pyinstaller
```

### Step 2: Build for Your Platform

```bash
# Create single executable
pyinstaller --name chess_viewer --onefile --windowed --add-data "in;in" --add-data "data;data" --add-data "res;res" run.py
```

The executable will be created in the `dist` directory.

## Engine Setup

1. Download eg Stockfish:
   - Windows: [Official Stockfish](https://stockfishchess.org/download/)
   - Linux: `sudo apt install stockfish`
   - macOS: `brew install stockfish`

2. Place the engine in one of these locations:
   - `res/engines/stockfish` (Linux/macOS)
   - `res/engines/stockfish.exe` (Windows)
   - Or use "Load Engine" in the application menu

## Development

### Setting Up Development Environment

1. Clone the repository
2. Create virtual environment and install dependencies
3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
The project follows PEP 8 guidelines. Use flake8 for linting:
```bash
flake8 src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments

- [python-chess](https://python-chess.readthedocs.io/) for chess logic
- [Stockfish](https://stockfishchess.org/) for engine analysis
- [PIL/Pillow](https://python-pillow.org/) for image handling

## Support

For support, please:
1. Check the Common Issues section
2. Search existing GitHub issues
3. Create a new issue with:
   - Your OS and Python version
   - Steps to reproduce the problem
   - Error messages
   - Logs (if available)
