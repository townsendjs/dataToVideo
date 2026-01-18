import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from glitch_hub import tomato_gui


def _ensure_repo_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _launch_data_to_video() -> None:
    _ensure_repo_on_path()
    import app

    app.main()


def _launch_tomato(root: tk.Tk) -> None:
    tomato_gui.show_tomato_gui(parent=root)


def main() -> None:
    root = tk.Tk()
    root.title("Glitch Hub")
    root.geometry("360x220")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Glitch Hub", font=("Helvetica", 16, "bold")).pack(pady=(0, 16))

    data_button = ttk.Button(
        frame,
        text="Data → Video",
        command=_launch_data_to_video,
    )
    data_button.pack(fill="x", pady=6, ipady=8)

    tomato_button = ttk.Button(
        frame,
        text="Tomato (AVI datamosh)",
        command=lambda: _launch_tomato(root),
    )
    tomato_button.pack(fill="x", pady=6, ipady=8)

    root.mainloop()


if __name__ == "__main__":
    main()
