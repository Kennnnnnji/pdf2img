#!/bin/bash
# PDF to Image Converter - macOS 打包脚本
# 生成独立 .app，可在任意 Mac 上双击运行

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 确保虚拟环境存在
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    uv venv 2>/dev/null || python3 -m venv .venv
fi

source .venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt pyinstaller Pillow -q

# 生成图标
if [ ! -f "app_icon.icns" ]; then
    echo "生成应用图标..."
    python gen_icon.py
fi

# 清理旧构建
rm -rf build dist

echo "开始打包..."
pyinstaller \
    --name "PDF2Image" \
    --windowed \
    --noconfirm \
    --clean \
    --icon "app_icon.icns" \
    --osx-bundle-identifier "com.pdf2img.app" \
    --strip \
    pdf2img.py

# 打包为可分发的 zip (保留 .app 目录结构)
cd dist
zip -r -y PDF2Image.zip PDF2Image.app
cd ..

echo ""
echo "========================================"
echo "  打包完成!"
echo "  应用位置: dist/PDF2Image.app"
echo "  分发压缩包: dist/PDF2Image.zip"
echo "========================================"
echo ""
echo "分发方式:"
echo "  1. 直接拷贝 PDF2Image.app 到 /Applications"
echo "  2. 或将 PDF2Image.zip 发给其他人，解压即可使用"
echo ""
echo "启动: open dist/PDF2Image.app"
