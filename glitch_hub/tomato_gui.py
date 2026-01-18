import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    TkinterDnD = tk  # type: ignore
    DND_AVAILABLE = False


MODES = ["void", "random", "reverse", "invert", "bloom", "pulse", "jiggle", "overlap"]


def _ensure_repo_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _parse_drop_paths(raw_path: str) -> list[str]:
    paths: list[str] = []
    current = ""
    in_brace = False

    for ch in raw_path.strip():
        if ch == "{":
            in_brace = True
            current = ""
        elif ch == "}":
            in_brace = False
            if current:
                paths.append(current)
                current = ""
        elif ch == " " and not in_brace:
            if current:
                paths.append(current)
                current = ""
        else:
            current += ch

    if current:
        paths.append(current)

    return paths


def _compute_output_path(file_path: Path, mode: str, countframes: int, positframes: int) -> Path:
    cname = f"-c{countframes}" if countframes > 1 else ""
    pname = f"-n{positframes}" if positframes > 1 else ""
    output_name = f"{file_path.stem}-{mode}{cname}{pname}.avi"
    return file_path.with_name(output_name)


class TomatoApp:
    def __init__(self, parent: tk.Misc | None = None):
        _ensure_repo_on_path()
        if parent and DND_AVAILABLE and hasattr(TkinterDnD, "Toplevel"):
            self.root = TkinterDnD.Toplevel(parent)
        elif parent and DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        elif parent:
            self.root = tk.Toplevel(parent)
        else:
            self.root = TkinterDnD.Tk()
        self.root.title("Tomato – AVI Datamosh")
        self.root.geometry("520x420")
        self.root.resizable(False, False)

        self.selected_path_var = tk.StringVar(value="No file selected")
        self.mode_var = tk.StringVar(value="void")
        self.count_var = tk.IntVar(value=1)
        self.length_var = tk.IntVar(value=1)
        self.kill_var = tk.DoubleVar(value=0.7)
        self.audio_var = tk.BooleanVar(value=False)
        self.firstframe_var = tk.BooleanVar(value=True)

        self._run_button: ttk.Button | None = None

        self._build_ui()
        self._update_run_state()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="Tomato – AVI Datamosh", font=("Helvetica", 16, "bold"))
        title.pack(pady=(0, 12))

        drop_label = ttk.Label(
            frame,
            text=(
                "Drop file here" if DND_AVAILABLE else "Install tkinterdnd2 for drag-and-drop"
            ),
            relief=tk.RIDGE,
            padding=18,
            anchor="center",
        )
        drop_label.pack(fill="x", pady=(0, 8))

        if DND_AVAILABLE:
            drop_label.drop_target_register(DND_FILES)
            drop_label.dnd_bind("<<Drop>>", self._on_drop)

        ttk.Button(frame, text="Add File", command=self._on_add_file).pack(pady=(0, 12))

        ttk.Label(frame, textvariable=self.selected_path_var, wraplength=460).pack(pady=(0, 12))

        controls = ttk.Frame(frame)
        controls.pack(fill="x")

        ttk.Label(controls, text="Mode").grid(row=0, column=0, sticky="w")
        mode_combo = ttk.Combobox(
            controls,
            textvariable=self.mode_var,
            values=MODES,
            state="readonly",
            width=12,
        )
        mode_combo.grid(row=1, column=0, sticky="w")

        ttk.Label(controls, text="Glitch frequency").grid(row=0, column=1, padx=(12, 0), sticky="w")
        ttk.Scale(
            controls,
            from_=1,
            to=20,
            orient="horizontal",
            variable=self.count_var,
            command=lambda _val: self.count_var.set(int(float(self.count_var.get()))),
        ).grid(row=1, column=1, padx=(12, 0), sticky="we")

        ttk.Label(controls, text="Glitch length").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(
            controls,
            from_=1,
            to=20,
            orient="horizontal",
            variable=self.length_var,
            command=lambda _val: self.length_var.set(int(float(self.length_var.get()))),
        ).grid(row=3, column=0, sticky="we")

        ttk.Label(controls, text="Aggressiveness").grid(
            row=2, column=1, padx=(12, 0), sticky="w", pady=(8, 0)
        )
        ttk.Scale(
            controls,
            from_=0.3,
            to=1.0,
            orient="horizontal",
            variable=self.kill_var,
        ).grid(row=3, column=1, padx=(12, 0), sticky="we")

        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        options = ttk.Frame(frame)
        options.pack(fill="x", pady=(12, 0))

        ttk.Checkbutton(
            options, text="Preserve audio", variable=self.audio_var
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            options, text="Keep first frame clean", variable=self.firstframe_var
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))

        self._run_button = ttk.Button(frame, text="Run Tomato", command=self._run)
        self._run_button.pack(pady=(16, 0))

    def _set_selected_path(self, path: Path) -> None:
        if path.suffix.lower() != ".avi":
            messagebox.showerror("Invalid file", "Please select an .avi file.")
            self.selected_path_var.set("No file selected")
            self._update_run_state()
            return

        self.selected_path_var.set(str(path))
        self._update_run_state()

    def _on_add_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select an AVI file",
            filetypes=[("AVI files", "*.avi")],
        )
        if file_path:
            self._set_selected_path(Path(file_path))

    def _on_drop(self, event) -> None:
        raw_path = event.data.strip()
        paths = _parse_drop_paths(raw_path)
        if paths:
            self._set_selected_path(Path(paths[0]))

    def _update_run_state(self) -> None:
        if not self._run_button:
            return

        path = Path(self.selected_path_var.get())
        enabled = path.exists() and path.suffix.lower() == ".avi"
        state = "normal" if enabled else "disabled"
        self._run_button.configure(state=state)

    def _build_args(self, input_path: Path) -> list[str]:
        args = [
            "-i",
            str(input_path),
            "-m",
            self.mode_var.get(),
            "-c",
            str(self.count_var.get()),
            "-n",
            str(self.length_var.get()),
            "-k",
            f"{self.kill_var.get():.2f}",
            "-a",
            "1" if self.audio_var.get() else "0",
            "-ff",
            "1" if self.firstframe_var.get() else "0",
        ]
        return args

    def _run(self) -> None:
        input_path = Path(self.selected_path_var.get())
        if not input_path.exists() or input_path.suffix.lower() != ".avi":
            messagebox.showerror("Invalid file", "Please select a valid .avi file.")
            self._update_run_state()
            return

        args = self._build_args(input_path)
        try:
            from glitch_hub import tomato

            tomato.main(args)
        except Exception as exc:  # pragma: no cover - UI guard
            messagebox.showerror("Tomato failed", str(exc))
            return

        output_path = _compute_output_path(
            input_path,
            mode=self.mode_var.get(),
            countframes=self.count_var.get(),
            positframes=self.length_var.get(),
        )
        messagebox.showinfo("Tomato complete", f"Output saved to:\n{output_path}")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = TomatoApp()
    app.run()


if __name__ == "__main__":
    main()
