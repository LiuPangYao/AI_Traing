# [AI協助 Claude] 由 Peter Liu 於 2026-10-29 審閱修改
"""畫啟動畫面 assets/splash.png（PyInstaller --splash 用）：白底圓角卡、黑底白 N 的圖標、程式名、「載入中…」。
exe 是 onefile，點兩下後要先解壓 1～2 秒才有視窗，這張圖就是那段時間給使用者看的。
跑法：python tools/make_splash.py（改了 APP_NAME 或想換樣子就重跑，再 build_exe.bat）"""
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from personalnote import APP_NAME, __version__  # noqa: E402

SS = 4                                   # 超取樣：放大 4 倍畫，最後 LANCZOS 縮回 360×180，邊才平滑（Peter：有鋸齒）
W, H = 360 * SS, 180 * SS
img = Image.new("RGB", (W, H), (255, 255, 255))                 # 整張不透明：PyInstaller 的啟動畫面不支援半透明，圓角外的透明像素會混成粉紅邊（Peter 2026-10-30）
d = ImageDraw.Draw(img)
d.rectangle((0, 0, W - 1, H - 1), outline=(200, 204, 212), width=2 * SS)
# 圖標：黑方塊白 N（跟 icon.ico 同一個意思）
d.rounded_rectangle((28 * SS, 46 * SS, (28 + 88) * SS, (46 + 88) * SS), radius=14 * SS, fill=(20, 20, 20))


def font(size: int, bold: bool = False):
    for name in (("msjhbd.ttc" if bold else "msjh.ttc"), "msjh.ttc", "arial.ttf"):
        p = pathlib.Path(r"C:\Windows\Fonts") / name
        if p.is_file():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


d.text(((28 + 44) * SS, (46 + 44) * SS), "N", font=font(56 * SS, True), fill=(255, 255, 255), anchor="mm")
d.text((140 * SS, 70 * SS), APP_NAME, font=font(30 * SS, True), fill=(30, 30, 30), anchor="lm")
# 第二行「載入中…  vX」不畫在圖上：由 PyInstaller 的啟動畫面文字區動態顯示（Notion.spec 的 text_pos；app.py 每 0.3 秒換點點）
out = ROOT / "assets" / "splash.png"
img = img.resize((W // SS, H // SS), Image.LANCZOS)
img.save(out)
print("寫出", out, img.size)
