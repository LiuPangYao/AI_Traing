# [AI協助 Claude] 由 Peter Liu 於 2026-10-28 審閱修改
"""用 PIL 畫工具列圖示（不用 emoji 字型，各台電腦長得一樣）。
產出 assets/icons/<名稱>_<light|dark>.png，64×64（顯示時縮成 18×18，4 倍超取樣）。
名稱：menu、prev、next、today、plus、undo、redo、attach、trash、settings
用法：python tools/make_icons.py"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "icons"
S = 256                     # 畫布（最後縮到 64）
W = 22                      # 線寬
COLORS = {"light": (40, 44, 52, 255), "dark": (225, 228, 235, 255)}


def canvas():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def save(img, name, variant):
    OUT.mkdir(parents=True, exist_ok=True)
    img.resize((128, 128), Image.LANCZOS).save(OUT / f"{name}_{variant}.png")   # 128 px：theme.icon 再 LANCZOS 縮到實際像素


def line(d, pts, c, w=W):
    d.line(pts, fill=c, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=c)


def arrow_head(d, tip, angle_deg, c, size=46, w=W):
    a = math.radians(angle_deg)
    for s in (+1, -1):
        b = a + s * math.radians(140)
        line(d, [tip, (tip[0] + size * math.cos(b), tip[1] + size * math.sin(b))], c, w)


def draw(name, c):
    img, d = canvas()
    m = 48
    if name == "menu":
        for y in (72, 128, 184):
            line(d, [(m, y), (S - m, y)], c)
    elif name == "prev":
        line(d, [(160, 56), (96, 128), (160, 200)], c)
    elif name == "next":
        line(d, [(96, 56), (160, 128), (96, 200)], c)
    elif name == "today":
        d.rounded_rectangle((m, 64, S - m, S - m), radius=22, outline=c, width=W)
        line(d, [(m, 112), (S - m, 112)], c, 16)
        for x in (88, 168):
            line(d, [(x, 40), (x, 84)], c)
        d.ellipse((112, 140, 144, 172), fill=c)
    elif name == "plus":
        line(d, [(128, 48), (128, 208)], c)
        line(d, [(48, 128), (208, 128)], c)
    elif name in ("undo", "redo"):
        # 弧線 + 箭頭；redo 左右鏡射
        bbox = (56, 72, 200, 216)
        d.arc(bbox, start=180, end=330, fill=c, width=W)
        tip = (62, 100)
        line(d, [(62, 60), tip], c)
        line(d, [tip, (108, 100)], c)
        if name == "redo":
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif name == "attach":
        # 迴紋針：一個外弧＋內弧用兩條折線近似
        d.rounded_rectangle((70, 44, 150, 196), radius=40, outline=c, width=W)
        d.rounded_rectangle((104, 80, 184, 212), radius=40, outline=c, width=W)
        d.rectangle((60, 100, 196, 150), fill=(0, 0, 0, 0))
        line(d, [(70, 100), (70, 150)], c)
        line(d, [(150, 100), (150, 150)], c)
        line(d, [(104, 100), (104, 150)], c)
        line(d, [(184, 100), (184, 150)], c)
    elif name == "trash":
        line(d, [(48, 76), (208, 76)], c)
        line(d, [(100, 76), (100, 48), (156, 48), (156, 76)], c, 18)
        d.rounded_rectangle((70, 76, 186, 216), radius=14, outline=c, width=W)
        for x in (104, 128, 152):
            line(d, [(x, 108), (x, 184)], c, 14)
    elif name == "settings":
        cx = cy = 128
        for k in range(8):
            a = math.radians(k * 45)
            line(d, [(cx + 62 * math.cos(a), cy + 62 * math.sin(a)), (cx + 96 * math.cos(a), cy + 96 * math.sin(a))], c, 28)
        d.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), outline=c, width=W)
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), outline=c, width=W)
    else:
        raise ValueError(name)
    return img


NAMES = ["menu", "prev", "next", "today", "plus", "undo", "redo", "attach", "trash", "settings"]
for n in NAMES:
    for v, c in COLORS.items():
        save(draw(n, c), n, v)
print("icons written:", OUT, NAMES)
