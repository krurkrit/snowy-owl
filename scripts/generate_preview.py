#!/usr/bin/env python3
"""Generate the README theme-comparison preview from canonical tokens."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from token_resolver import load_token_documents
from validate_contrast import contrast

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/images/snowy-owl-preview.png"
W, H = 1800, 1500


def load_font(size, bold=False):
    """Use a native UI font when available and remain portable."""
    names = (
        [
            "C:/Windows/Fonts/seguisb.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/System/Library/Fonts/SFNS.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "C:/Windows/Fonts/segoeui.ttf",
            "/System/Library/Fonts/SFNS.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def rgb(value):
    """Convert a hexadecimal RGB color to a three-component tuple."""
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def mix(first, second, amount):
    """Mix two canonical colors without introducing another palette value."""
    a, b = rgb(first), rgb(second)
    return tuple(round(x * (1 - amount) + y * amount) for x, y in zip(a, b))


def text(draw, xy, value, color, size, bold=False, anchor=None):
    """Draw text using the first available portable UI font."""
    draw.text(xy, value, fill=color, font=load_font(size, bold), anchor=anchor)


def check(draw, x, y, color, scale=1.0):
    """Draw a scalable checkmark icon."""
    draw.line(
        [(x, y + 8 * scale), (x + 7 * scale, y + 15 * scale), (x + 20 * scale, y)],
        fill=color,
        width=max(2, round(4 * scale)),
        joint="curve",
    )


def swatch(draw, x, y, color, border, size=34):
    """Draw a rounded color swatch."""
    draw.rounded_rectangle(
        (x, y, x + size, y + size), radius=5, fill=color, outline=border, width=1
    )


def owl_mark(draw, x, y, dark_color, light_color, accent_color):
    """Draw the compact Snowy Owl brand mark from token colors."""
    draw.ellipse((x, y, x + 88, y + 88), fill=dark_color)
    draw.ellipse((x + 20, y + 24, x + 68, y + 71), fill=light_color)
    draw.polygon(
        [(x + 22, y + 33), (x + 20, y + 14), (x + 37, y + 25)], fill=light_color
    )
    draw.polygon(
        [(x + 66, y + 33), (x + 68, y + 14), (x + 51, y + 25)], fill=light_color
    )
    draw.ellipse((x + 30, y + 34, x + 38, y + 42), fill=dark_color)
    draw.ellipse((x + 50, y + 34, x + 58, y + 42), fill=dark_color)
    draw.polygon(
        [(x + 40, y + 45), (x + 48, y + 45), (x + 44, y + 53)], fill=accent_color
    )
    draw.polygon(
        [(x + 43, y + 53), (x + 30, y + 72), (x + 53, y + 64)], fill=light_color
    )


def theme_icon(draw, x, y, kind, color, background):
    """Draw a sun or moon icon for a theme panel."""
    if kind == "sun":
        draw.ellipse((x + 12, y + 12, x + 42, y + 42), fill=color)
        for dx, dy in ((27, 0), (27, 54), (0, 27), (54, 27), (8, 8), (46, 46), (46, 8), (8, 46)):
            draw.ellipse((x + dx - 3, y + dy - 3, x + dx + 3, y + dy + 3), fill=color)
    else:
        draw.ellipse((x + 4, y + 4, x + 50, y + 50), fill=color)
        draw.ellipse((x + 20, y - 2, x + 56, y + 39), fill=background)


def draw_demo(draw, box, theme):
    """Draw interactive control examples for one theme."""
    x1, y1, x2, y2 = box

    fg = theme["foreground"]
    bg = theme["background"]

    surface = theme["secondaryBackground"]
    border = mix(fg, bg, 0.72)
    link = theme["link"]
    secondary_accent = theme["secondaryAccent"]

    draw.rounded_rectangle(box, radius=15, fill=bg, outline=border, width=2)
    text(draw, (x1 + 26, y1 + 28), "The quick brown fox", fg, 31, True)
    text(draw, (x1 + 26, y1 + 78), "Comfortable text for long sessions.", fg, 19)
    text(draw, (x1 + 26, y1 + 109), "Links and buttons use Snowy Owl colors.", fg, 19)
    text(draw, (x1 + 26, y1 + 153), "This is a theme link", link, 19, True)
    draw.line((x1 + 26, y1 + 179, x1 + 190, y1 + 179), fill=link, width=1)
    text(draw, (x1 + 26, y1 + 188), "This is a secondary accent", secondary_accent, 19, True)
    draw.line((x1 + 26, y1 + 214, x1 + 212, y1 + 214), fill=secondary_accent, width=1)

    button_y = y2 - 68
    draw.rounded_rectangle((x1 + 26, button_y, x1 + 238, y2 - 20), radius=8, fill=theme["accent"])
    text(draw, (x1 + 132, button_y + 24), "Primary button", theme["accentText"], 17, True, "mm")
    draw.rounded_rectangle(
        (x1 + 252, button_y, x1 + 458, y2 - 20),
        radius=8,
        fill=theme["accent"],
    )
    text(
        draw,
        (x1 + 355, button_y + 24),
        "Action button",
        theme["accentText"],
        17,
        True,
        "mm",
    )

    # Optional for visual intent
    card_x = x1 + 485
    draw.rounded_rectangle((card_x, y1 + 25, x2 - 22, y2 - 20), radius=12, fill=surface, outline=border)
    text(draw, (card_x + 22, y1 + 52), "Card / Surface", fg, 21, True)
    text(draw, (card_x + 22, y1 + 94), "A nested surface with", fg, 17)
    text(draw, (card_x + 22, y1 + 121), "text, a link, and input.", fg, 17)
    text(draw, (card_x + 22, y1 + 170), "Learn more  →", link, 17, True)
    draw.rounded_rectangle((card_x + 22, y2 - 78, x2 - 43, y2 - 34), radius=7, fill=bg, outline=border)
    text(draw, (card_x + 38, y2 - 66), "Input text", fg, 16)


def draw_contrast_table(draw, box, rows, theme_fg, theme_bg, colors, minimum):
    """Draw color pairs, ratios, and pass indicators for one theme."""
    x1, y1, x2, y2 = box
    border = mix(theme_fg, theme_bg, 0.76)
    header_bg = mix(theme_fg, theme_bg, 0.88)
    draw.rounded_rectangle(box, radius=12, fill=theme_bg, outline=border, width=1)
    draw.rounded_rectangle((x1, y1, x2, y1 + 50), radius=12, fill=header_bg)
    columns = (x1 + 18, x1 + 205, x1 + 390, x1 + 575, x2 - 54)
    for pos, label in zip(columns, ("Element", "Foreground", "Background", "Contrast", "Pass")):
        text(draw, (pos, y1 + 17), label, theme_fg, 15, True, "ma" if label == "Pass" else None)
    row_h = (y2 - y1 - 50) / len(rows)
    for index, (label, fg, bg) in enumerate(rows):
        top = y1 + 50 + index * row_h
        if index % 2:
            draw.rectangle((x1 + 1, top, x2 - 1, top + row_h), fill=mix(theme_fg, theme_bg, 0.965))
        draw.line((x1, top, x2, top), fill=border, width=1)
        cy = top + row_h / 2
        text(draw, (columns[0], cy), label, theme_fg, 15, anchor="lm")
        swatch(draw, columns[1], cy - 14, fg, border, 28)
        text(draw, (columns[1] + 39, cy), fg, theme_fg, 14, anchor="lm")
        swatch(draw, columns[2], cy - 14, bg, border, 28)
        text(draw, (columns[2] + 39, cy), bg, theme_fg, 14, anchor="lm")
        ratio = contrast(fg, bg)
        text(draw, (columns[3], cy), f"{ratio:.2f} : 1", theme_fg, 15, True, "lm")
        if ratio >= minimum:
            check(draw, columns[4] - 10, cy - 9, colors["status"]["success"], 0.8)


def draw_theme_panel(draw, box, title, kind, colors, minimum):
    """Draw a complete light or dark theme preview panel."""
    x1, y1, x2, y2 = box

    is_dark = kind == "moon"
    theme_key = "dark" if is_dark else "light"
    theme = colors[theme_key]

    bg = theme["background"]
    fg = theme["foreground"]
    border = mix(fg, bg, 0.76)

    # Special condition that light theme will show icon in warning color (yellow tone)
    icon_color = colors["dark"]["foreground"] if is_dark else colors["status"]["warning"]

    draw.rounded_rectangle(box, radius=18, fill=bg, outline=border, width=2)
    theme_icon(draw, x1 + 28, y1 + 26, kind, icon_color, bg)
    text(draw, (x1 + 105, y1 + 25), title, fg, 33, True)
    text(
        draw,
        (x1 + 105, y1 + 68),
        f"colors.{theme_key}.background  {bg}   |   colors.{theme_key}.foreground  {fg}",
        fg,
        17,
    )

    descriptions = {
        "dark": "Deep, focused background with clear text.",
        "light": "Clean, paper-like background with comfortable text.",
    }
    text(draw, (x1 + 105, y1 + 102), descriptions[theme_key], fg, 15)
    draw_demo(draw, (x1 + 24, y1 + 145, x2 - 24, y1 + 458), theme)

    rows = [
        ("Normal text", fg, bg),
        ("Link", colors["dark" if is_dark else "light"]["link"], bg),
        ("Primary button / Accent", theme["accentText"], theme["accent"]),
        ("Orange link", colors["orange"]["dark" if is_dark else "light"], bg),
        ("Orange button text", colors["orange"]["accentText"], colors["orange"]["accent"]),
        ("Error text", colors["status"]["lightText"], colors["status"]["error"]),
        ("Warning text", colors["status"]["darkText"], colors["status"]["warning"]),
        ("Success text", colors["status"]["lightText"], colors["status"]["success"]),
    ]
    draw_contrast_table(draw, (x1 + 24, y1 + 480, x2 - 24, y2 - 24), rows, fg, bg, colors, minimum)


def draw_info_card(draw, box, title, lines, colors, tint):
    """Draw a tinted summary card with checkmarked statements."""
    x1, y1, x2, y2 = box
    fg = colors["light"]["foreground"]
    bg = mix(colors["light"]["background"], tint, 0.09)
    border = mix(
        colors["light"]["foreground"], colors["light"]["background"], 0.82
    )
    draw.rounded_rectangle(box, radius=14, fill=bg, outline=border)
    text(draw, (x1 + 20, y1 + 18), title, fg, 20, True)
    for index, line in enumerate(lines):
        cy = y1 + 61 + index * 27
        check(draw, x1 + 21, cy - 8, colors["status"]["success"], 0.62)
        text(draw, (x1 + 51, cy), line, fg, 15, anchor="lm")


def main():
    """Load canonical tokens and write the generated PNG preview."""
    tokens = load_token_documents(ROOT / "tokens")
    colors = tokens["colors"]
    typography = tokens["typography"]
    minimum = float(tokens["contrast-rules"]["policy"]["minimum"])

    # Required preview foundations come directly from the four base tokens.
    light_bg = colors["light"]["background"]
    light_fg = colors["light"]["foreground"]
    dark_bg = colors["dark"]["background"]
    dark_fg = colors["dark"]["foreground"]
    img = Image.new("RGB", (W, H), light_bg)
    draw = ImageDraw.Draw(img)

    owl_mark(draw, 34, 30, dark_bg, light_bg, colors["orange"]["accent"])
    text(draw, (140, 25), "Snowy Owl", dark_bg, 43, True)
    text(draw, (140, 76), "Personalization Preview & Color Comparison", light_fg, 24)
    text(draw, (34, 127), "A consistent, accessible experience across every supported app.", light_fg, 17)

    key_x, key_y, key_w = 820, 18, 956
    key_bg = mix(light_bg, colors["light"]["secondaryBackground"], 0.7)
    draw.rounded_rectangle((key_x, key_y, key_x + key_w, 158), radius=14, fill=key_bg)
    text(draw, (key_x + 22, key_y + 13), "Token variables", light_fg, 20, True)
    palette = [
        ("colors.light.background", light_bg),
        ("colors.light.foreground", light_fg),
        ("colors.dark.background", dark_bg),
        ("colors.dark.foreground", dark_fg),
        ("colors.light.accentText", colors["light"]["accentText"]),
        ("colors.light.accent", colors["light"]["accent"]),
        ("colors.dark.accentText", colors["dark"]["accentText"]),
        ("colors.dark.accent", colors["dark"]["accent"]),
    ]
    for index, (label, value) in enumerate(palette):
        column = index % 4
        row = index // 4
        x = key_x + 22 + column * 232
        y = key_y + 49 + row * 52
        swatch(draw, x, y, value, mix(light_fg, light_bg, 0.65), 38)
        text(draw, (x + 49, y), label, light_fg, 12, True)
        text(draw, (x + 49, y + 21), value, light_fg, 13)

    draw_theme_panel(draw, (24, 180, 888, 1162), "Light theme", "sun", colors, minimum)
    draw_theme_panel(draw, (912, 180, 1776, 1162), "Dark theme", "moon", colors, minimum)

    dark_link_ratio = contrast(colors["dark"]["link"], dark_bg)
    draw_info_card(
        draw,
        (24, 1182, 588, 1390),
        "Link on the dark theme",
        [
            f"{colors['dark']['link']} reaches {dark_link_ratio:.2f}:1",
            f"Meets the {minimum:.1f}:1 project gate",
            "Clear for links and focus states",
            "Shared by every supported adapter",
        ],
        colors,
        colors["dark"]["link"],
    )
    draw_info_card(
        draw,
        (606, 1182, 1190, 1390),
        "Why this palette?",
        [
            "Comfortable for long-term use",
            "Semantic roles remain consistent",
            "Light and dark modes share intent",
            "App limitations stay in adapters",
        ],
        colors,
        colors["status"]["success"],
    )
    draw_info_card(
        draw,
        (1208, 1182, 1776, 1390),
        "Guiding principles",
        [
            f"Required contrast is at least {minimum:.1f}:1",
            "Canonical tokens drive every output",
            "Portable across Windows, macOS, Linux",
            "Settings remain safe and reproducible",
        ],
        colors,
        colors["blue"]["light"],
    )

    banner_bg = mix(light_bg, colors["status"]["success"], 0.10)
    draw.rounded_rectangle((24, 1410, 1776, 1478), radius=13, fill=banner_bg)
    draw.ellipse((47, 1424, 87, 1464), fill=colors["status"]["success"])
    check(draw, 57, 1434, colors["status"]["lightText"], 0.78)
    ui_families = " → ".join(item["family"] for item in typography["ui"]["fonts"])
    text(draw, (105, 1428), "Result: one accessible palette for app-wide personalization.", light_fg, 18, True)
    text(draw, (105, 1453), f"UI font fallback: {ui_families}", light_fg, 15)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(OUT)


if __name__ == "__main__":
    main()
