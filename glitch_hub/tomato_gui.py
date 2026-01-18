import tkinter as tk
from tkinter import messagebox


def show_tomato_gui(parent: tk.Misc | None = None) -> None:
    messagebox.showinfo("Tomato", "Tomato GUI coming soon", parent=parent)
