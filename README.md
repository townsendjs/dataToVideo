# Data to Video

Minimal macOS-friendly desktop app that maps any file's bytes directly to pixel data and saves the result as an MP4. Drag a file onto the window (requires `tkinterdnd2`) or click **Add File** to run the conversion.

Choose an aspect ratio (1:1, 4:3, 16:9, 9:16), base width (256/512/1024), and frame rate (1/12/24/30). The app computes the corresponding height (e.g., 512×384 for 4:3, 1024×1820 for 9:16) and shows an estimated duration based on the file size, selected resolution, and FPS.

## How it works
- Bytes are written sequentially into RGB frames (left-to-right, top-to-bottom, channel order RGB).
- Each frame uses `width * height * 3` bytes; the final frame is zero-padded for deterministic layout.
- Frames are stitched into an H.264 MP4 (`*_datamosh.mp4`) at the selected FPS that opens cleanly in Premiere Pro/After Effects.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### macOS drag-and-drop
Install the optional dependency for drag-and-drop:
```bash
pip install tkinterdnd2
```

## Run the app
```bash
python app.py
```

## Glitch Hub menu
Launch the combined tool selector:
```bash
python glitch_hub/hub.py
```

This menu lets you choose between the Data → Video GUI or the Tomato AVI datamosh tool. Running `python app.py` still launches the standalone Data → Video GUI.

## Tweaks
- The GUI offers aspect ratios and base widths; adjust `BASE_SIZES` or `ASPECT_RATIOS` in `app.py` for different presets.
- Change `FPS` or the `write_videofile` codec/preset in `app.py` to target other formats (e.g., ProRes) if desired.
