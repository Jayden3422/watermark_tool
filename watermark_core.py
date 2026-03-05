import math
import os
import sys
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Dict

from PIL import Image, ImageDraw, ImageFont


def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)


ColorRGB = Tuple[int, int, int]


def _clean_font_display_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"\s*\((TrueType|OpenType)\)\s*$", "", name, flags=re.I)

    # 特别处理：像 "Microsoft YaHei Bold & Microsoft YaHei UI Bold" 这种，UI 用第一个更清爽
    if " & " in name and " UI " in name:
        name = name.split(" & ")[0].strip()

    name = re.sub(r"\s+", " ", name)
    return name


@lru_cache(maxsize=1)
def list_installed_fonts_windows() -> Dict[str, str]:
    """
    返回：{字体显示名: 字体文件完整路径}
    - 读取 HKLM / HKCU 的 Windows Fonts 注册表
    - 兼容系统字体 + 当前用户安装字体（%LOCALAPPDATA%\Microsoft\Windows\Fonts）
    """
    fonts: Dict[str, str] = {}

    if not sys.platform.startswith("win"):
        return fonts

    try:
        import winreg  # type: ignore
    except Exception:
        return fonts

    windir = os.environ.get("WINDIR", r"C:\Windows")
    sys_font_dir = os.path.join(windir, "Fonts")
    user_font_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")

    font_dirs = [sys_font_dir, user_font_dir]

    def normalize_font_path(raw: str) -> Optional[str]:
        if not raw:
            return None
        raw = str(raw).strip()
        # 有时会出现 "xxx.ttf,yyy.ttf" 这种写法，先取第一个
        raw = raw.split(",")[0].strip()
        raw = os.path.expandvars(raw)

        if os.path.isabs(raw):
            return raw if os.path.exists(raw) else raw  # 不强制存在（有些系统会返回不可直接访问的路径）
        # 相对路径：通常在 Fonts 目录
        for d in font_dirs:
            p = os.path.join(d, raw)
            if os.path.exists(p):
                return p
        # 最后兜底
        return os.path.join(sys_font_dir, raw)

    def add_from_reg(root, subkey: str) -> None:
        try:
            k = winreg.OpenKey(root, subkey)
        except OSError:
            return

        i = 0
        while True:
            try:
                name, data, _ = winreg.EnumValue(k, i)
                i += 1
            except OSError:
                break

            display = _clean_font_display_name(name)
            path = normalize_font_path(str(data))

            if not display or not path:
                continue

            # 同名保留先来的（一般 HKLM 更完整）
            if display not in fonts:
                fonts[display] = path

        try:
            winreg.CloseKey(k)
        except Exception:
            pass

    add_from_reg(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
    )
    add_from_reg(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
    )

    return fonts


@dataclass
class WatermarkParams:
    text: str = "For employment verification only – [Company Name]"
    angle_deg: float = 35.0
    font_size_ratio: float = 0.035

    # 新增：文字颜色（RGB）
    color_rgb: ColorRGB = (65, 65, 65)
    opacity: int = 40

    step_x_ratio: float = 2.6
    step_y_ratio: float = 3.0
    shift_ratio: float = 0.3
    min_repeat_per_row: float = 1.0
    stroke_width: int = 0

    # 新增：系统字体名（从下拉选择）
    font_name: Optional[str] = None
    # 新增：字体集合索引（ttc 用；一般用 0 就够）
    font_index: int = 0
    # 仍保留：用户自选字体文件（ttf/ttc/otf），优先级最高
    font_path: Optional[str] = None

    @property
    def stroke_darker_rgb(self) -> ColorRGB:
        r, g, b = self.color_rgb
        return (max(0, r - 60), max(0, g - 60), max(0, b - 60))


def _want_bold_from_name(name: Optional[str]) -> bool:
    s = (name or "").lower()
    return ("bold" in s) or ("粗体" in (name or "")) or ("黑体" in (name or "")) or ("semibold" in s)


def _try_load_ttc_best(path: str, font_size: int, want_bold: bool) -> Optional[ImageFont.ImageFont]:
    """
    对 .ttc/.otc 尝试多个 index，尽量挑到 Bold（或 Regular）
    """
    best = None
    for idx in range(0, 10):
        try:
            f = ImageFont.truetype(path, font_size, index=idx)
        except Exception:
            continue

        try:
            fam, style = f.getname()
        except Exception:
            fam, style = ("", "")

        style_l = (style or "").lower()

        if want_bold:
            if ("bold" in style_l) or ("粗" in (style or "")) or ("semibold" in style_l) or ("demi" in style_l):
                return f
        else:
            # 尽量找 regular/normal
            if ("regular" in style_l) or ("normal" in style_l) or (style_l.strip() == ""):
                return f

        if best is None:
            best = f

    return best


def load_font(
    font_size: int,
    font_path: Optional[str] = None,
    font_index: int = 0,
    font_name: Optional[str] = None,
) -> ImageFont.ImageFont:
    # 1) 用户指定字体文件优先
    if font_path:
        try:
            ext = os.path.splitext(font_path)[1].lower()
            want_bold = _want_bold_from_name(font_name) or _want_bold_from_name(os.path.basename(font_path))
            # 若是 ttc/otc，尽量自动选到 bold（font_index=0 且想要 bold 时）
            if ext in [".ttc", ".otc"] and int(font_index) == 0 and want_bold:
                f = _try_load_ttc_best(font_path, font_size, want_bold=True)
                if f:
                    return f
            return ImageFont.truetype(font_path, font_size, index=int(font_index))
        except Exception:
            pass

    # 2) 按系统字体名查注册表路径
    if font_name and sys.platform.startswith("win"):
        fonts = list_installed_fonts_windows()
        p = fonts.get(font_name)
        if p:
            try:
                ext = os.path.splitext(p)[1].lower()
                want_bold = _want_bold_from_name(font_name)
                if ext in [".ttc", ".otc"] and want_bold:
                    f = _try_load_ttc_best(p, font_size, want_bold=True)
                    if f:
                        return f
                return ImageFont.truetype(p, font_size, index=0)
            except Exception:
                pass

    # 3) 兜底（优先微软雅黑粗体）
    fallback_names = [
        "Microsoft YaHei UI Bold",
        "Microsoft YaHei Bold",
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "微软雅黑 粗体",
        "微软雅黑",
        "SimHei",
        "Arial",
    ]
    if sys.platform.startswith("win"):
        fonts = list_installed_fonts_windows()
        for n in fallback_names:
            for k, p in fonts.items():
                if n.lower() in k.lower():
                    try:
                        ext = os.path.splitext(p)[1].lower()
                        want_bold = _want_bold_from_name(n) or _want_bold_from_name(k)
                        if ext in [".ttc", ".otc"] and want_bold:
                            f = _try_load_ttc_best(p, font_size, want_bold=True)
                            if f:
                                return f
                        return ImageFont.truetype(p, font_size, index=0)
                    except Exception:
                        continue

    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, stroke_width: int) -> Tuple[int, int]:
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        return r - l, b - t
    except Exception:
        return draw.textsize(text, font=font)


def make_diagonal_watermark(base_w: int, base_h: int, p: WatermarkParams) -> Image.Image:
    diag = int(math.hypot(base_w, base_h))
    canvas = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    font_size = max(18, int(min(base_w, base_h) * float(p.font_size_ratio)))
    font = load_font(
        font_size=font_size,
        font_path=p.font_path,
        font_index=p.font_index,
        font_name=p.font_name,
    )

    tw, th = text_size(draw, p.text, font, p.stroke_width)

    theta = math.radians(float(p.angle_deg))
    visible_span_along_text = base_w * abs(math.cos(theta)) + base_h * abs(math.sin(theta))

    step_x_default = int(max(1, tw * float(p.step_x_ratio)))

    repeats = float(p.min_repeat_per_row) if p.min_repeat_per_row is not None else 1.0
    repeats = max(0.1, repeats)  # 防止除 0；UI 已限制 >=1.0，这里只是兜底

    step_x_target_max = max(1, int(visible_span_along_text / repeats))
    step_x = max(1, min(step_x_default, step_x_target_max))

    step_y = max(1, int(th * float(p.step_y_ratio)))

    r, g, b = p.color_rgb
    a = int(max(0, min(255, p.opacity)))
    fill = (int(r), int(g), int(b), a)

    stroke_fill = None
    if int(p.stroke_width) > 0:
        sr, sg, sb = p.stroke_darker_rgb
        stroke_fill = (int(sr), int(sg), int(sb), a)

    y_positions = list(range(-th - diag, diag + th + diag, step_y))
    for row_idx, y in enumerate(y_positions):
        shift = int((row_idx % 2) * step_x * float(p.shift_ratio))
        start_x = -tw - diag + shift
        end_x = diag + tw + diag
        for x in range(start_x, end_x, step_x):
            draw.text(
                (x, y),
                p.text,
                font=font,
                fill=fill,
                stroke_width=int(p.stroke_width),
                stroke_fill=stroke_fill,
            )

    rotated = canvas.rotate(float(p.angle_deg), resample=Image.BICUBIC, expand=True)
    rw, rh = rotated.size
    left = (rw - base_w) // 2
    top = (rh - base_h) // 2
    return rotated.crop((left, top, left + base_w, top + base_h))


def apply_watermark(im: Image.Image, p: WatermarkParams) -> Image.Image:
    base = im.convert("RGBA")
    w, h = base.size
    wm = make_diagonal_watermark(w, h, p)
    out = Image.alpha_composite(base, wm)
    return out


def save_image(im: Image.Image, path: str) -> None:
    out_p = Path(path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    ext = (out_p.suffix or ".png").lower()
    if ext in [".jpg", ".jpeg"]:
        im = im.convert("RGB")  # JPEG 不支持 alpha

    fmt_map = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".bmp": "BMP",
        ".webp": "WEBP",
    }
    fmt = fmt_map.get(ext, "PNG")

    # 用二进制流保存：对“任意字符路径”更稳
    with open(str(out_p), "wb") as f:
        # 让 PIL 在 file-object 模式下也能正确识别格式
        if fmt == "JPEG":
            im.save(f, format=fmt, quality=95)
        else:
            im.save(f, format=fmt)