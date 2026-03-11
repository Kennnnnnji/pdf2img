"""
生成 PDF2Image 应用图标
现代 macOS 风格：圆角矩形 + 渐变背景 + PDF→图片视觉隐喻
"""

import math
import os
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont


def rounded_rect(draw, xy, radius, fill):
    """绘制圆角矩形"""
    x0, y0, x1, y1 = xy
    r = radius
    # 四个角的圆弧
    draw.pieslice([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=fill)
    # 中间填充
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)


def create_gradient_bg(size):
    """创建蓝色渐变背景"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 渐变色: 从深蓝到亮蓝
    top_color = (0, 90, 230)      # 深蓝
    bot_color = (40, 160, 255)    # 亮蓝

    margin = int(size * 0.04)
    radius = int(size * 0.18)
    rect = (margin, margin, size - margin, size - margin)

    # 先画基础圆角矩形
    rounded_rect(draw, rect, radius, top_color)

    # 逐行渐变覆盖（仅在矩形范围内）
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    rounded_rect(mask_draw, rect, radius, 255)

    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(margin, size - margin):
        t = (y - margin) / (size - 2 * margin)
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * t)
        for x in range(margin, size - margin):
            gradient.putpixel((x, y), (r, g, b, 255))

    img = Image.composite(gradient, img, mask)

    return img, draw, mask


def draw_doc_shape(draw, cx, cy, w, h, fold, fill, outline=None):
    """绘制带折角的文档形状"""
    # 文档主体（左上、右上折角点、右上折角底、右下、左下）
    points = [
        (cx - w // 2, cy - h // 2),                   # 左上
        (cx + w // 2 - fold, cy - h // 2),             # 右上折角起
        (cx + w // 2, cy - h // 2 + fold),             # 右上折角底
        (cx + w // 2, cy + h // 2),                    # 右下
        (cx - w // 2, cy + h // 2),                    # 左下
    ]
    draw.polygon(points, fill=fill, outline=outline)
    # 折角三角
    fold_points = [
        (cx + w // 2 - fold, cy - h // 2),
        (cx + w // 2 - fold, cy - h // 2 + fold),
        (cx + w // 2, cy - h // 2 + fold),
    ]
    fold_color = tuple(max(0, c - 30) for c in fill[:3])
    if len(fill) > 3:
        fold_color = fold_color + (fill[3],)
    draw.polygon(fold_points, fill=fold_color)


def draw_mountain_icon(draw, cx, cy, w, h, fill_mountain, fill_sun):
    """绘制简化的风景图标（代表图片）"""
    # 山
    m1 = [
        (cx - w // 2, cy + h // 3),
        (cx - w // 6, cy - h // 3),
        (cx + w // 3, cy + h // 3),
    ]
    draw.polygon(m1, fill=fill_mountain)

    m2 = [
        (cx, cy + h // 3),
        (cx + w // 4, cy - h // 6),
        (cx + w // 2, cy + h // 3),
    ]
    draw.polygon(m2, fill=fill_mountain)

    # 太阳
    sun_r = w // 8
    draw.ellipse(
        [cx + w // 5 - sun_r, cy - h // 3 - sun_r,
         cx + w // 5 + sun_r, cy - h // 3 + sun_r],
        fill=fill_sun
    )


def draw_arrow(draw, cx, cy, size, fill):
    """绘制右箭头"""
    s = size
    hw = s // 2
    # 箭头三角
    points = [
        (cx - hw, cy - hw),
        (cx + hw, cy),
        (cx - hw, cy + hw),
    ]
    draw.polygon(points, fill=fill)


def create_icon(size=1024):
    """创建完整图标"""
    img, _, mask = create_gradient_bg(size)
    draw = ImageDraw.Draw(img)

    u = size / 1024  # 缩放单位

    # ── 左侧: PDF 文档 ──
    doc_cx = int(300 * u)
    doc_cy = int(480 * u)
    doc_w = int(320 * u)
    doc_h = int(400 * u)
    doc_fold = int(60 * u)

    # 文档阴影
    draw_doc_shape(draw,
                   doc_cx + int(6 * u), doc_cy + int(6 * u),
                   doc_w, doc_h, doc_fold,
                   fill=(0, 50, 150, 80))
    # 文档主体
    draw_doc_shape(draw,
                   doc_cx, doc_cy,
                   doc_w, doc_h, doc_fold,
                   fill=(255, 255, 255, 240))

    # PDF 文字
    pdf_font_size = int(90 * u)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", pdf_font_size)
    except Exception:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", pdf_font_size)
        except Exception:
            font = ImageFont.load_default()

    text = "PDF"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (doc_cx - tw // 2, doc_cy - th // 2 + int(30 * u)),
        text, fill=(0, 90, 230), font=font
    )

    # 文档上的横线（装饰）
    line_y_start = doc_cy - int(120 * u)
    for i in range(3):
        ly = line_y_start + i * int(30 * u)
        lx0 = doc_cx - int(100 * u)
        lx1 = doc_cx + int(60 * u) if i < 2 else doc_cx
        draw.rounded_rectangle(
            [lx0, ly, lx1, ly + int(8 * u)],
            radius=int(4 * u),
            fill=(200, 215, 240, 180)
        )

    # ── 中间: 箭头 ──
    arrow_cx = int(540 * u)
    arrow_cy = int(480 * u)
    draw_arrow(draw, arrow_cx, arrow_cy, int(60 * u), fill=(255, 255, 255, 200))

    # ── 右侧: 图片图标 ──
    img_cx = int(750 * u)
    img_cy = int(480 * u)
    img_w = int(280 * u)
    img_h = int(240 * u)
    img_r = int(20 * u)

    # 图片框阴影
    draw.rounded_rectangle(
        [img_cx - img_w // 2 + int(6 * u), img_cy - img_h // 2 + int(6 * u),
         img_cx + img_w // 2 + int(6 * u), img_cy + img_h // 2 + int(6 * u)],
        radius=img_r,
        fill=(0, 50, 150, 80)
    )
    # 图片框
    draw.rounded_rectangle(
        [img_cx - img_w // 2, img_cy - img_h // 2,
         img_cx + img_w // 2, img_cy + img_h // 2],
        radius=img_r,
        fill=(255, 255, 255, 240)
    )

    # 图片内容: 风景
    draw_mountain_icon(
        draw,
        img_cx, img_cy + int(15 * u),
        int(200 * u), int(140 * u),
        fill_mountain=(40, 160, 255, 200),
        fill_sun=(255, 220, 80, 230)
    )

    return img


def create_icns(icon_img, output_path):
    """从 PIL Image 创建 macOS .icns 文件"""
    iconset_dir = output_path.replace(".icns", ".iconset")
    os.makedirs(iconset_dir, exist_ok=True)

    sizes = [16, 32, 64, 128, 256, 512]
    for s in sizes:
        # 标准分辨率
        resized = icon_img.resize((s, s), Image.LANCZOS)
        resized.save(os.path.join(iconset_dir, f"icon_{s}x{s}.png"))
        # Retina (@2x)
        s2 = s * 2
        if s2 <= 1024:
            resized2 = icon_img.resize((s2, s2), Image.LANCZOS)
            resized2.save(os.path.join(iconset_dir, f"icon_{s}x{s}@2x.png"))

    # 512@2x = 1024
    icon_img.save(os.path.join(iconset_dir, "icon_512x512@2x.png"))

    # 使用 macOS iconutil 生成 .icns
    subprocess.run(
        ["iconutil", "-c", "icns", iconset_dir, "-o", output_path],
        check=True
    )
    shutil.rmtree(iconset_dir)
    print(f"图标已生成: {output_path}")


if __name__ == "__main__":
    icon = create_icon(1024)

    # 保存 PNG 预览
    icon.save("icon_preview.png")
    print("预览已保存: icon_preview.png")

    # 生成 .icns
    create_icns(icon, "app_icon.icns")
