"""Sinh brand image cho integration ariston_ha — icon trung tính, KHÔNG dùng logo Ariston.

Quy cách (home-assistant/brands, custom_integrations/<domain>/):
- PNG lossless, viền cắt sát, nền ngoài ô trong suốt, 1:1.
- icon.png 256×256, icon@2x.png 512×512.

Icon: giọt nước trên nền bo tròn (nước nóng) — hình tự vẽ, không phải nhãn hiệu của ai.
Dùng: python tools/make_brand.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "custom_components" / "ariston_ha" / "brand"
BG = (0, 122, 160, 255)      # xanh nước
DROP = (255, 255, 255, 255)
HEAT = (255, 138, 0, 255)    # cam ấm


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.18
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)
    # giọt nước: tam giác đỉnh trên + nửa tròn dưới
    cx = size / 2
    top = size * 0.20
    mid = size * 0.50
    half = size * 0.19
    d.polygon([(cx, top), (cx - half, mid), (cx + half, mid)], fill=DROP)
    d.ellipse([cx - half, mid - half, cx + half, mid + half], fill=DROP)
    # vạch "nóng" nhỏ dưới giọt
    d.rounded_rectangle(
        [cx - size * 0.16, size * 0.80, cx + size * 0.16, size * 0.855],
        radius=size * 0.03,
        fill=HEAT,
    )
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(256).save(OUT / "icon.png")
    draw(512).save(OUT / "icon@2x.png")
    print("wrote", OUT / "icon.png", "and icon@2x.png")


if __name__ == "__main__":
    main()
