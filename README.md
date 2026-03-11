# PDF → Image

一款运行在 macOS 上的现代化 PDF 转图片工具。基于 PyQt6 + PyMuPDF 构建，支持打包为独立 `.app`，无需 Python 环境即可运行。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![macOS](https://img.shields.io/badge/macOS-13.0+-black)
![License](https://img.shields.io/badge/License-MIT-green)

## 功能

- **拖拽导入** — 直接将 PDF 拖入窗口，或点击选择文件
- **批量转换** — 同时处理多个 PDF 文件
- **多格式输出** — PNG / JPG / WEBP / TIFF
- **DPI 可调** — 72 ~ 1200，默认 300
- **页面范围** — 全部 / 首页 / 末页 / 自定义 (如 `1-3, 5, 7-10`)
- **后台转换** — 多线程处理，UI 不卡顿
- **实时进度** — 显示当前页数和百分比
- **可取消** — 转换过程中随时取消
- **独立分发** — 打包为 `.app`，拷贝即用

## 快速开始

### 方式一：直接运行源码

```bash
git clone https://github.com/Kennnnnnji/pdf2img.git
cd pdf2img
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python pdf2img.py
```

### 方式二：打包为独立应用

```bash
./build.sh
```

完成后：
- `dist/PDF2Image.app` — 双击即可运行
- `dist/PDF2Image.zip` — 发给其他人，解压即可使用

## 项目结构

```
pdf2img/
├── pdf2img.py          # 主程序
├── gen_icon.py         # 图标生成脚本
├── app_icon.icns       # macOS 应用图标
├── build.sh            # 一键打包脚本
└── requirements.txt    # Python 依赖
```

## 技术栈

| 组件 | 用途 |
|------|------|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | GUI 框架 |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF 解析与渲染 |
| [PyInstaller](https://pyinstaller.org/) | 打包为独立应用 |
| [Pillow](https://pillow.readthedocs.io/) | 图标生成 |

## 作者

Made by **Ken** with **Claude Code**
