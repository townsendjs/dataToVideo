import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except ImportError:  # pragma: no cover - GUI optional dependency
    TkinterDnD = tk  # type: ignore
    DND_AVAILABLE = False


FPS = 1
ASPECT_RATIOS = {
    "1:1": (1, 1),
    "4:3": (4, 3),
    "16:9": (16, 9),
    "9:16": (9, 16),
}
BASE_SIZES = [128, 256, 512, 1024]
PIXEL_SCALES = [1, 2, 3, 4]
FPS_CHOICES = [0.25, 0.5, 1, 2, 5, 10]


def bytes_to_frames(data: bytes, width: int, height: int):
    """Convert raw bytes into RGB frames with consistent layout.

    Bytes are written sequentially into rows, left-to-right then top-to-bottom,
    using RGB channel order. Each frame is width*height*3 bytes; the final frame
    is zero-padded if needed so that every pixel deterministically maps to the
    same byte offsets.
    """

    frame_size = width * height * 3
    frames = []
    if not data:
        data = b""  # ensure deterministic empty output

    for offset in range(0, len(data), frame_size):
        chunk = data[offset : offset + frame_size]
        if len(chunk) < frame_size:
            chunk += bytes(frame_size - len(chunk))
        frame = np.frombuffer(chunk, dtype=np.uint8).reshape((height, width, 3))
        frames.append(frame)

    if not frames:
        frames.append(np.zeros((height, width, 3), dtype=np.uint8))

    return frames


def convert_file_to_video(
    file_path: Path, width: int, height: int, fps: float = FPS, pixel_scale: int = 1
) -> Path:
    """Convert a binary file into a deterministic pixel-based MP4."""

    with file_path.open("rb") as f:
        data = f.read()

    frames = bytes_to_frames(data, width=width, height=height)
    if pixel_scale > 1:
        # Enlarge pixels while keeping the original byte layout by repeating rows/cols.
        frames = [
            np.repeat(np.repeat(frame, pixel_scale, axis=0), pixel_scale, axis=1)
            for frame in frames
        ]

    clip = ImageSequenceClip(frames, fps=fps)

    output_path = file_path.with_suffix("")
    output_path = output_path.with_name(output_path.name + "_datamosh.mp4")
    clip.write_videofile(
        output_path.as_posix(),
        codec="libx264",
        audio=False,
        fps=fps,
        preset="slow",
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    )

    return output_path


class DataToVideoApp:
    def __init__(self):
        self.root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
        self.root.title("Data to Video")
        self.root.resizable(False, False)

        self.aspect_ratio_var = tk.StringVar(value="16:9")
        self.base_size_var = tk.StringVar(value=str(BASE_SIZES[1]))
        self.fps_var = tk.StringVar(value=str(FPS))
        self.pixel_scale_var = tk.StringVar(value=str(PIXEL_SCALES[0]))
        self.resolution_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="Estimated duration: —")
        self.selected_file_path: Path | None = None

        self.status_var = tk.StringVar(value="Drop a file or use the Add File button")

        self._build_ui()
        self._update_resolution_display()
        self._fit_to_content()

    def _build_ui(self):
        padding = {"padx": 16, "pady": 12}
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True, **padding)

        title = ttk.Label(frame, text="Data→Video", font=("Helvetica", 16, "bold"))
        title.pack(pady=(0, 10))

        settings = ttk.Frame(frame)
        settings.pack(fill="x", pady=(0, 8))

        ttk.Label(settings, text="Aspect ratio").grid(row=0, column=0, sticky="w")
        ratio_combo = ttk.Combobox(
            settings,
            textvariable=self.aspect_ratio_var,
            values=list(ASPECT_RATIOS.keys()),
            state="readonly",
            width=10,
        )
        ratio_combo.grid(row=1, column=0, sticky="w")
        ratio_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_settings_change())

        ttk.Label(settings, text="Base width").grid(row=0, column=1, padx=(12, 0), sticky="w")
        base_combo = ttk.Combobox(
            settings,
            textvariable=self.base_size_var,
            values=[str(size) for size in BASE_SIZES],
            state="readonly",
            width=10,
        )
        base_combo.grid(row=1, column=1, padx=(12, 0), sticky="w")
        base_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_settings_change())

        ttk.Label(settings, text="Frame rate (fps)").grid(row=0, column=2, padx=(12, 0), sticky="w")
        fps_combo = ttk.Combobox(
            settings,
            textvariable=self.fps_var,
            values=[str(fps) for fps in FPS_CHOICES],
            width=10,
        )
        fps_combo.grid(row=1, column=2, padx=(12, 0), sticky="w")
        fps_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_settings_change())

        ttk.Label(settings, text="Pixel scale").grid(row=0, column=3, padx=(12, 0), sticky="w")
        scale_combo = ttk.Combobox(
            settings,
            textvariable=self.pixel_scale_var,
            values=[str(scale) for scale in PIXEL_SCALES],
            state="readonly",
            width=10,
        )
        scale_combo.grid(row=1, column=3, padx=(12, 0), sticky="w")
        scale_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_settings_change())

        ttk.Label(frame, textvariable=self.resolution_var).pack(anchor="w", pady=(2, 0))
        ttk.Label(frame, textvariable=self.duration_var).pack(anchor="w", pady=(0, 8))

        drop_label = ttk.Label(
            frame,
            text=(
                "Drag a file here" if DND_AVAILABLE else "Install tkinterdnd2 for drag-and-drop"
            ),
            relief=tk.RIDGE,
            padding=20,
            anchor="center",
        )
        drop_label.pack(fill="both", expand=True)

        if DND_AVAILABLE:
            drop_label.drop_target_register(DND_FILES)
            drop_label.dnd_bind("<<Drop>>", self._on_drop)

        button_row = ttk.Frame(frame)
        button_row.pack(pady=(12, 6))

        add_button = ttk.Button(button_row, text="Add File", command=self._on_add_file)
        add_button.pack(side="left")

        self.run_button = ttk.Button(
            button_row,
            text="Run",
            command=self._on_run,
            state="disabled",
        )
        self.run_button.pack(side="left", padx=(10, 0))

        status = ttk.Label(frame, textvariable=self.status_var, wraplength=360)
        status.pack(pady=(6, 0))

    def _fit_to_content(self):
        """Resize window to the requested size of its children."""
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        self.root.minsize(width, height)
        self.root.geometry(f"{width}x{height}")

    def _on_add_file(self):
        file_path = filedialog.askopenfilename(title="Select a file to convert")
        if file_path:
            path = Path(file_path)
            self.selected_file_path = path
            self._update_duration_hint()
            self.status_var.set(f"Selected: {path.name}")
            self.run_button.config(state="normal")

    def _on_drop(self, event):
        # event.data may contain multiple paths, with braces around those that include spaces.
        raw_path = event.data.strip()

        paths: list[str] = []
        current = ""
        in_brace = False

        for ch in raw_path:
            if ch == "{":
                in_brace = True
                current = ""
            elif ch == "}":
                in_brace = False
                if current:
                    paths.append(current)
                    current = ""
            elif ch == " " and not in_brace:
                # separator between paths
                if current:
                    paths.append(current)
                    current = ""
            else:
                current += ch

        if current:
            paths.append(current)

        first_path = paths[0] if paths else ""

        if first_path:
            path = Path(first_path)
            self.selected_file_path = path
            self._update_duration_hint()
            self.status_var.set(f"Selected: {path.name}")
            self.run_button.config(state="normal")

    def _on_settings_change(self):
        self._update_resolution_display()
        self._update_duration_hint()

    def _current_resolution(self) -> tuple[int, int]:
        aspect = self.aspect_ratio_var.get()
        width_ratio, height_ratio = ASPECT_RATIOS.get(aspect, (1, 1))
        base_width = int(self.base_size_var.get())
        computed_height = max(1, int(round(base_width * (height_ratio / width_ratio))))
        return base_width, computed_height

    def _current_fps(self) -> float:
        try:
            fps = float(self.fps_var.get())
            return max(0.01, fps)
        except ValueError:
            return float(FPS)

    def _current_pixel_scale(self) -> int:
        try:
            scale = int(self.pixel_scale_var.get())
            return max(1, scale)
        except ValueError:
            return 1

    def _update_resolution_display(self):
        width, height = self._current_resolution()
        scale = self._current_pixel_scale()
        self.resolution_var.set(
            f"Resolution: {width}×{height} ({self.aspect_ratio_var.get()}) | Pixel scale: {scale}x → {width*scale}×{height*scale}"
        )

    def _update_duration_hint(self):
        if not self.selected_file_path or not self.selected_file_path.exists():
            self.duration_var.set("Estimated duration: —")
            return

        width, height = self._current_resolution()
        frame_size = width * height * 3
        file_size = self.selected_file_path.stat().st_size
        frames = max(1, math.ceil(file_size / frame_size))
        fps = self._current_fps()
        seconds = frames / fps
        self.duration_var.set(
            f"Estimated duration: {frames} frame(s) ≈ {seconds:.2f} sec @ {fps} fps"
        )

    def _on_run(self):
        if not self.selected_file_path:
            messagebox.showwarning("No file selected", "Add or drop a file before running.")
            return

        self._convert(self.selected_file_path)

    def _convert(self, path: Path):
        if not path.exists():
            messagebox.showerror("Error", f"File not found: {path}")
            return

        self.status_var.set("Converting… this may take a moment")
        self.root.update_idletasks()

        try:
            width, height = self._current_resolution()
            fps = self._current_fps()
            scale = self._current_pixel_scale()
            output_path = convert_file_to_video(
                path,
                width=width,
                height=height,
                fps=fps,
                pixel_scale=scale,
            )
        except Exception as exc:  # pragma: no cover - GUI level handling
            messagebox.showerror("Conversion failed", str(exc))
            self.status_var.set("Conversion failed")
        else:
            self.status_var.set(f"Saved: {output_path}")
            messagebox.showinfo("Done", f"Video saved to:\n{output_path}")


def main():
    app = DataToVideoApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()
