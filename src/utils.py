import os

def discover_engines():
    """Discover all engine executables recursively in the res/engines folder and its subdirectories."""
    engine_dir = os.path.join('res', 'engines')
    engines = []
    
    if os.path.exists(engine_dir):
        for root, dirs, files in os.walk(engine_dir):
            for file in files:
                if file.endswith('.exe'):
                    engine_path = os.path.join(root, file)
                    # Create name from relative path, replacing directory separators with spaces
                    rel_path = os.path.relpath(engine_path, engine_dir)
                    name = os.path.splitext(rel_path)[0].replace(os.sep, ' ')
                    engines.append({
                        'name': name,
                        'path': engine_path
                    })
    
    return engines