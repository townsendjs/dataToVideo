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


def _compute_output_path(
    file_path: Path,
    mode: str,
    countframes: int,
    positframes: int,
    aggressiveness: float,
) -> Path:
    agg_percent = int(round(aggressiveness * 100))
    if agg_percent < 0:
        agg_percent = 0
    if agg_percent > 100:
        agg_percent = 100
    output_name = f"{file_path.stem}-{mode}-f{countframes}-l{positframes}-a{agg_percent}.avi"
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
        self.root.geometry("520x480")
        self.root.resizable(False, False)

        self.selected_path_var = tk.StringVar(value="No file selected")
        self.output_path_var = tk.StringVar(value="Output: (auto)")
        self.mode_var = tk.StringVar(value="void")
        self.freq_var = tk.IntVar(value=4)
        self.length_var = tk.IntVar(value=4)
        self.agg_var = tk.DoubleVar(value=0.5)
        self.audio_var = tk.BooleanVar(value=False)
        self.firstframe_var = tk.BooleanVar(value=True)

        self._run_button: ttk.Button | None = None

        self._build_ui()
        self.mode_var.trace_add("write", lambda *_: self._refresh_output_hint())
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

        export_frame = ttk.Frame(frame)
        export_frame.pack(fill="x", pady=(0, 12))
        ttk.Button(export_frame, text="Export To…", command=self._on_export_to).pack(
            side="left"
        )
        ttk.Label(export_frame, textvariable=self.output_path_var, wraplength=360).pack(
            side="left", padx=(8, 0), fill="x", expand=True
        )

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
        self.count_value_label = ttk.Label(controls, text=str(self.freq_var.get()))
        self.count_value_label.grid(row=0, column=2, padx=(8, 0), sticky="e")
        self.count_scale = ttk.Scale(
            controls,
            from_=1,
            to=12,
            orient="horizontal",
            variable=self.freq_var,
            command=self._on_count_change,
        )
        self.count_scale.grid(row=1, column=1, columnspan=2, padx=(12, 0), sticky="we")

        ttk.Label(controls, text="Glitch length").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.length_value_label = ttk.Label(controls, text=str(self.length_var.get()))
        self.length_value_label.grid(row=2, column=2, padx=(8, 0), sticky="e")
        self.length_scale = ttk.Scale(
            controls,
            from_=1,
            to=12,
            orient="horizontal",
            variable=self.length_var,
            command=self._on_length_change,
        )
        self.length_scale.grid(row=3, column=0, columnspan=3, sticky="we")

        ttk.Label(controls, text="Aggressiveness").grid(
            row=4, column=0, sticky="w", pady=(8, 0)
        )
        self.kill_value_label = ttk.Label(controls, text=self._format_agg_label())
        self.kill_value_label.grid(row=4, column=2, padx=(8, 0), sticky="e")
        self.kill_scale = ttk.Scale(
            controls,
            from_=0.30,
            to=1.00,
            orient="horizontal",
            variable=self.agg_var,
            command=self._on_kill_change,
        )
        self.kill_scale.grid(row=5, column=0, columnspan=3, sticky="we")

        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=0)

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

        self._set_slider_defaults()

    def _set_selected_path(self, path: Path) -> None:
        if path.suffix.lower() != ".avi":
            messagebox.showerror("Invalid file", "Please select an .avi file.")
            self.selected_path_var.set("No file selected")
            self.output_path_var.set("Output: (auto)")
            self._update_run_state()
            return

        self.selected_path_var.set(f"Input: {path}")
        self.output_path_var.set(f"Output: {self._default_output_path(path)}")
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

    def _on_export_to(self) -> None:
        input_path = Path(self.selected_path_var.get().replace("Input: ", ""))
        if not input_path.exists():
            messagebox.showerror("Missing file", "Please select an input .avi file first.")
            return

        suggested = self._default_output_path(input_path)
        save_path = filedialog.asksaveasfilename(
            title="Export Tomato output",
            defaultextension=".avi",
            initialfile=suggested.name,
            initialdir=str(suggested.parent),
            filetypes=[("AVI files", "*.avi")],
        )
        if save_path:
            self.output_path_var.set(f"Output: {save_path}")

    def _update_run_state(self) -> None:
        if not self._run_button:
            return

        path = Path(self.selected_path_var.get().replace("Input: ", ""))
        enabled = path.exists() and path.suffix.lower() == ".avi"
        state = "normal" if enabled else "disabled"
        self._run_button.configure(state=state)

    def _default_output_path(self, input_path: Path) -> Path:
        return _compute_output_path(
            input_path,
            mode=self.mode_var.get(),
            countframes=self.freq_var.get(),
            positframes=self.length_var.get(),
            aggressiveness=self.agg_var.get(),
        )

    def _build_args(self, input_path: Path) -> list[str]:
        args = [
            "-i",
            str(input_path),
            "-m",
            self.mode_var.get(),
            "-c",
            str(self.freq_var.get()),
            "-n",
            str(self.length_var.get()),
            "-k",
            f"{self.agg_var.get():.2f}",
        ]
        if self.audio_var.get():
            args.extend(["-a", "1"])
        if self.firstframe_var.get():
            args.extend(["-ff", "1"])
        else:
            args.extend(["-ff", "0"])
        return args

    def _run(self) -> None:
        input_path = Path(self.selected_path_var.get().replace("Input: ", ""))
        if not input_path.exists() or input_path.suffix.lower() != ".avi":
            messagebox.showerror("Invalid file", "Please select a valid .avi file.")
            self._update_run_state()
            return

        export_path_text = self.output_path_var.get().replace("Output: ", "").strip()
        export_path = Path(export_path_text) if export_path_text and export_path_text != "(auto)" else None

        args = self._build_args(input_path)
        print("Tomato args:", args)
        try:
            from glitch_hub import tomato

            tomato.main(args)
        except Exception as exc:  # pragma: no cover - UI guard
            messagebox.showerror("Tomato failed", str(exc))
            return

        output_path = self._default_output_path(input_path)
        if export_path and export_path != output_path:
            if output_path.exists():
                output_path.replace(export_path)
                output_path = export_path
            else:
                messagebox.showerror(
                    "Tomato failed",
                    "Tomato did not create the expected output file.",
                )
                return

        messagebox.showinfo("Tomato complete", f"Output saved to:\n{output_path}")

    def _set_slider_defaults(self) -> None:
        self.count_scale.set(self.freq_var.get())
        self.length_scale.set(self.length_var.get())
        self.kill_scale.set(self.agg_var.get())
        self._on_count_change(str(self.freq_var.get()))
        self._on_length_change(str(self.length_var.get()))
        self._on_kill_change(str(self.agg_var.get()))

    def _on_count_change(self, value: str) -> None:
        count = max(1, int(float(value)))
        if count > 12:
            count = 12
        self.freq_var.set(count)
        self.count_value_label.config(text=str(count))
        self._refresh_output_hint()

    def _on_length_change(self, value: str) -> None:
        length = max(1, int(float(value)))
        if length > 12:
            length = 12
        self.length_var.set(length)
        self.length_value_label.config(text=str(length))
        self._refresh_output_hint()

    def _on_kill_change(self, value: str) -> None:
        kill = float(value)
        if kill < 0.30:
            kill = 0.30
        if kill > 1.00:
            kill = 1.00
        self.agg_var.set(kill)
        self.kill_value_label.config(text=self._format_agg_label())
        self._refresh_output_hint()

    def _format_agg_label(self) -> str:
        percent = int(round(self.agg_var.get() * 100))
        return f"{percent}%"

    def _refresh_output_hint(self) -> None:
        input_text = self.selected_path_var.get().replace("Input: ", "")
        input_path = Path(input_text) if input_text and input_text != "No file selected" else None
        if input_path and input_path.exists():
            self.output_path_var.set(f"Output: {self._default_output_path(input_path)}")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = TomatoApp()
    app.run()


if __name__ == "__main__":
    main()
