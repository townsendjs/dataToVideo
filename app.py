import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
from moviepy.editor import ImageSequenceClip

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
BASE_SIZES = [256, 512, 1024]


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


def convert_file_to_video(file_path: Path, width: int, height: int, fps: int = FPS) -> Path:
    """Convert a binary file into a deterministic pixel-based MP4."""

    with file_path.open("rb") as f:
        data = f.read()

    frames = bytes_to_frames(data, width=width, height=height)
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
        self.root.geometry("460x360")
        self.root.resizable(False, False)

        self.aspect_ratio_var = tk.StringVar(value="16:9")
        self.base_size_var = tk.StringVar(value=str(BASE_SIZES[1]))
        self.resolution_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="Estimated duration: —")
        self.selected_file_path: Path | None = None

        self.status_var = tk.StringVar(value="Drop a file or use the Add File button")

        self._build_ui()
        self._update_resolution_display()

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

        button = ttk.Button(frame, text="Add File", command=self._on_add_file)
        button.pack(pady=(12, 6))

        status = ttk.Label(frame, textvariable=self.status_var, wraplength=360)
        status.pack(pady=(6, 0))

    def _on_add_file(self):
        file_path = filedialog.askopenfilename(title="Select a file to convert")
        if file_path:
            path = Path(file_path)
            self.selected_file_path = path
            self._update_duration_hint()
            self._convert(path)

    def _on_drop(self, event):
        # event.data may contain braces and spaces; take the first path
        raw_path = event.data
        cleaned = raw_path.strip("{}")
        first_path = cleaned.split(" ")[0]
        if first_path:
            path = Path(first_path)
            self.selected_file_path = path
            self._update_duration_hint()
            self._convert(path)

    def _on_settings_change(self):
        self._update_resolution_display()
        self._update_duration_hint()

    def _current_resolution(self) -> tuple[int, int]:
        aspect = self.aspect_ratio_var.get()
        width_ratio, height_ratio = ASPECT_RATIOS.get(aspect, (1, 1))
        base_width = int(self.base_size_var.get())
        computed_height = max(1, int(round(base_width * (height_ratio / width_ratio))))
        return base_width, computed_height

    def _update_resolution_display(self):
        width, height = self._current_resolution()
        self.resolution_var.set(
            f"Resolution: {width}×{height} ({self.aspect_ratio_var.get()})"
        )

    def _update_duration_hint(self):
        if not self.selected_file_path or not self.selected_file_path.exists():
            self.duration_var.set("Estimated duration: —")
            return

        width, height = self._current_resolution()
        frame_size = width * height * 3
        file_size = self.selected_file_path.stat().st_size
        frames = max(1, math.ceil(file_size / frame_size))
        seconds = frames / FPS
        self.duration_var.set(
            f"Estimated duration: {frames} frame(s) ≈ {seconds:.2f} sec @ {FPS} fps"
        )

    def _convert(self, path: Path):
        if not path.exists():
            messagebox.showerror("Error", f"File not found: {path}")
            return

        self.status_var.set("Converting… this may take a moment")
        self.root.update_idletasks()

        try:
            width, height = self._current_resolution()
            output_path = convert_file_to_video(path, width=width, height=height, fps=FPS)
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
