# Diagonal Watermark Tool (Win11 / PySide6)

[中文 README →](README.zh.md)

A small GUI tool to add **repeating diagonal text watermarks** to images. The left panel contains scrollable controls, and the right panel shows a live preview (auto-scaled to keep the whole image visible). Supports bilingual UI, Windows system fonts, and custom font-file override.

![UI](assets/UI.png)

---

## Features

- Repeating diagonal watermark with adjustable:
  - angle, spacing, row stagger shift, minimum repeats per row
- Style controls:
  - text color, opacity, font size ratio, stroke width
- Font support:
  - Windows system font dropdown (searchable)
  - Override with `.ttf / .ttc / .otf` font files (highest priority)
- Export formats: PNG / JPEG / BMP / WEBP
- Preview: debounced refresh (~180ms), auto fit-to-view scaling

---

## Suggested Project Layout
```
 ├─ app.py
 ├─ watermark_core.py
 ├─ requirements.txt
 └─ assets/
 └─ UI.png
```
---

## Requirements

- Windows 10/11 (**system font listing relies on Windows Registry**; on non-Windows it may fall back to default fonts)
- Python 3.10+ (recommended 3.11)
- Dependencies in `requirements.txt`: `pillow`, `pyside6`, `pyinstaller`

---

## Setup & Run (Conda)

```bash
conda create -n diagonal-watermark python=3.11 -y
conda activate diagonal-watermark
pip install -r requirements.txt
python app.py
```

------

## Setup & Run (Python venv)

**Windows (PowerShell / CMD):**

```
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

> If PowerShell blocks activation, adjust execution policy (e.g., `Set-ExecutionPolicy RemoteSigned`) or use CMD.

------

## How to Use

1. Start the app: `python app.py`
2. Click **“Open/Replace Image…”** and pick an image
3. Adjust parameters on the left (preview updates automatically):
   - **Language**: switch UI language (if the watermark text is still the default, it will switch with the language)
   - **System font**: select or type to search
   - **Override font file**: choose a font file to override; “Clear override” returns to system font
   - **Text color / Opacity**: opacity range is 0–255
   - **Angle / Font size ratio**
   - **Horizontal/Vertical spacing**: larger values → sparser watermarks
   - **Row stagger shift**: offsets every other row to avoid perfect alignment
   - **Min repeats/row**: keeps at least N repeats per row by limiting spacing
   - **Stroke width**: improves readability (0 disables stroke)
4. Click **“Export…”** and choose output path/format

------

## Packaging (Optional: PyInstaller)

`pyinstaller` is included in `requirements.txt`.

```
pyinstaller -F -w app.py
```

- `-F`: one-file executable
- `-w`: windowed mode (no console)

If you want to ship a custom font with the app, place it in your repo and use the “Override font file” button at runtime.

------

## Notes / FAQ

- **Why is the system font list empty on non-Windows?**
   This project enumerates Windows fonts via Registry. On other OSes it returns an empty list and uses fallback fonts.
- **Why does JPEG export look different?**
   JPEG doesn’t support alpha; the image is converted to RGB on export.