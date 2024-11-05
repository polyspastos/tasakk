from src.chess_viewer import ChessViewer
import tkinter as tk

def main():
    print("Starting application...")
    root = tk.Tk()
    print("Created root window")
    
    root.geometry("1000x600")  # Set initial window size
    root.title("Chess Viewer")  # Set window title
    
    print("Creating ChessViewer instance...")
    app = ChessViewer(root)
    print("ChessViewer instance created")
    
    print("Starting mainloop...")
    root.mainloop()
    print("Mainloop ended")

if __name__ == "__main__":
    main()
