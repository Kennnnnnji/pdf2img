"""
PDF to Image Converter for macOS
基于 PyQt6 + PyMuPDF 的现代化 PDF 转图片工具
"""

__version__ = "1.0.0"

import sys
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QLineEdit,
    QFileDialog, QProgressBar, QScrollArea, QFrame, QSizePolicy,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent

try:
    import fitz  # PyMuPDF
except ImportError:
    print("请先安装依赖: pip install PyMuPDF PyQt6")
    sys.exit(1)


# ── 颜色主题 (macOS 风格) ──────────────────────────────────────────
THEME = {
    "bg": "#F5F5F7",
    "card": "#FFFFFF",
    "accent": "#007AFF",
    "accent_hover": "#0062DB",
    "accent_pressed": "#004FC4",
    "text": "#1D1D1F",
    "text2": "#86868B",
    "border": "#D2D2D7",
    "border_light": "#E8E8ED",
    "success": "#34C759",
    "danger": "#FF3B30",
    "drop_bg": "#EDF4FF",
    "drop_border": "#007AFF",
    "item_hover": "#F5F5F7",
    "progress_bg": "#E8E8ED",
}

# ── 全局样式 ────────────────────────────────────────────────────────
STYLESHEET = f"""
QMainWindow {{
    background-color: {THEME['bg']};
}}
QWidget#central {{
    background-color: {THEME['bg']};
}}

/* 卡片容器 */
QFrame.card {{
    background-color: {THEME['card']};
    border: 1px solid {THEME['border_light']};
    border-radius: 12px;
}}

/* 标题 */
QLabel.title {{
    font-size: 22px;
    font-weight: 700;
    color: {THEME['text']};
}}
QLabel.subtitle {{
    font-size: 13px;
    color: {THEME['text2']};
}}
QLabel.section-title {{
    font-size: 14px;
    font-weight: 600;
    color: {THEME['text']};
}}
QLabel.label {{
    font-size: 13px;
    color: {THEME['text2']};
}}

/* 按钮 */
QPushButton.primary {{
    background-color: {THEME['accent']};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 32px;
    font-size: 15px;
    font-weight: 600;
    min-height: 22px;
}}
QPushButton.primary:hover {{
    background-color: {THEME['accent_hover']};
}}
QPushButton.primary:pressed {{
    background-color: {THEME['accent_pressed']};
}}
QPushButton.primary:disabled {{
    background-color: {THEME['border']};
    color: {THEME['text2']};
}}
QPushButton.secondary {{
    background-color: {THEME['card']};
    color: {THEME['accent']};
    border: 1px solid {THEME['border']};
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton.secondary:hover {{
    background-color: {THEME['item_hover']};
}}
QPushButton.link {{
    background: none;
    border: none;
    color: {THEME['accent']};
    font-size: 13px;
    font-weight: 500;
    padding: 2px 4px;
}}
QPushButton.link:hover {{
    color: {THEME['accent_hover']};
    text-decoration: underline;
}}
QPushButton.icon-btn {{
    background: none;
    border: none;
    color: {THEME['text2']};
    font-size: 16px;
    padding: 4px;
    border-radius: 4px;
}}
QPushButton.icon-btn:hover {{
    background-color: {THEME['item_hover']};
    color: {THEME['danger']};
}}

/* 输入控件 */
QComboBox, QSpinBox, QLineEdit {{
    background-color: {THEME['card']};
    border: 1px solid {THEME['border']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    color: {THEME['text']};
    min-height: 20px;
}}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
    border-color: {THEME['accent']};
}}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{
    background-color: {THEME['bg']};
    color: {THEME['border']};
    border-color: {THEME['border_light']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {THEME['card']};
    border: 1px solid {THEME['border']};
    border-radius: 8px;
    selection-background-color: {THEME['drop_bg']};
    selection-color: {THEME['text']};
    padding: 4px;
}}

/* 进度条 */
QProgressBar {{
    background-color: {THEME['progress_bg']};
    border: none;
    border-radius: 4px;
    text-align: center;
    font-size: 12px;
    color: {THEME['text2']};
    max-height: 8px;
}}
QProgressBar::chunk {{
    background-color: {THEME['accent']};
    border-radius: 4px;
}}

/* 滚动区域 */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {THEME['border']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


# ── 转换线程 ────────────────────────────────────────────────────────
class ConvertWorker(QThread):
    """后台 PDF 转图片工作线程"""
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(int, int)       # success_count, fail_count
    error = pyqtSignal(str)

    # 单页最大像素数 (~600MB 内存)
    MAX_PIXELS = 200_000_000

    def __init__(self, files: list, fmt: str, dpi: int,
                 page_mode: str, page_range: str, output_dir: str):
        super().__init__()
        self.files = files
        self.fmt = fmt.lower()
        self.dpi = dpi
        self.page_mode = page_mode
        self.page_range = page_range
        self.output_dir = output_dir
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    @property
    def _cancel(self) -> bool:
        return self._cancel_event.is_set()

    def _parse_pages(self, total: int) -> list[int]:
        """解析页面范围，返回 0-based 页码列表"""
        if self.page_mode == "all":
            return list(range(total))
        if self.page_mode == "first":
            return [0]
        if self.page_mode == "last":
            return [total - 1]
        # 自定义范围: "1-3, 5, 7-10"
        pages = set()
        for part in self.page_range.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    for p in range(int(a) - 1, min(int(b), total)):
                        if 0 <= p < total:
                            pages.add(p)
                except ValueError:
                    continue
            else:
                try:
                    p = int(part) - 1
                    if 0 <= p < total:
                        pages.add(p)
                except ValueError:
                    continue
        return sorted(pages) if pages else list(range(total))

    def run(self):
        ok_count, fail_count = 0, 0
        # 先统计总页数
        total_pages = 0
        file_pages = []
        for fpath in self.files:
            try:
                doc = fitz.open(fpath)
                try:
                    pages = self._parse_pages(len(doc))
                    file_pages.append((fpath, pages))
                    total_pages += len(pages)
                finally:
                    doc.close()
            except Exception as e:
                self.error.emit(f"无法打开 {Path(fpath).name}: {e}")
                fail_count += 1
                file_pages.append((fpath, []))

        done = 0
        for fpath, pages in file_pages:
            if self._cancel:
                break
            if not pages:
                continue
            name = Path(fpath).stem
            try:
                doc = fitz.open(fpath)
                try:
                    for pg in pages:
                        if self._cancel:
                            break
                        page = doc[pg]
                        zoom = self.dpi / 72.0

                        # 内存安全检查
                        est_pixels = int(page.rect.width * zoom) * int(page.rect.height * zoom)
                        if est_pixels > self.MAX_PIXELS:
                            self.error.emit(
                                f"{name} 第 {pg + 1} 页在 {self.dpi} DPI 下分辨率过高，已跳过"
                            )
                            done += 1
                            fail_count += 1
                            continue

                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, alpha=False)

                        out_name = f"{name}_p{pg + 1}.{self.fmt}"
                        out_path = os.path.join(self.output_dir, out_name)

                        try:
                            if self.fmt == "jpg":
                                pix.save(out_path, jpg_quality=95)
                            else:
                                pix.save(out_path)
                        except Exception as e:
                            self.error.emit(f"保存 {out_name} 失败: {e}")
                            done += 1
                            fail_count += 1
                            continue

                        done += 1
                        ok_count += 1
                        self.progress.emit(
                            done, total_pages,
                            f"正在转换 {name} 第 {pg + 1} 页..."
                        )
                finally:
                    doc.close()
            except Exception as e:
                self.error.emit(f"转换 {Path(fpath).name} 失败: {e}")
                fail_count += 1

        self.finished.emit(ok_count, fail_count)


# ── 拖拽区域 ────────────────────────────────────────────────────────
class DropZone(QLabel):
    """支持拖拽和点击的 PDF 文件选择区域"""
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self._set_normal_style()
        self._update_text()

    def _update_text(self):
        self.setText(
            '<div style="text-align:center; line-height:1.6;">'
            '<span style="font-size:32px;">📄</span><br/>'
            f'<span style="font-size:14px; font-weight:600; color:{THEME["text"]};">'
            '拖拽 PDF 文件到此处</span><br/>'
            f'<span style="font-size:12px; color:{THEME["text2"]};">'
            '或点击选择文件</span>'
            '</div>'
        )

    def _set_normal_style(self):
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {THEME['card']};
                border: 2px dashed {THEME['border']};
                border-radius: 12px;
            }}
        """)

    def _set_hover_style(self):
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {THEME['drop_bg']};
                border: 2px dashed {THEME['drop_border']};
                border-radius: 12px;
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".pdf") for u in urls):
                event.acceptProposedAction()
                self._set_hover_style()

    def dragLeaveEvent(self, event):
        self._set_normal_style()

    def dropEvent(self, event: QDropEvent):
        self._set_normal_style()
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                files.append(path)
        if files:
            self.files_dropped.emit(files)

    def mousePressEvent(self, event):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择 PDF 文件", "",
            "PDF 文件 (*.pdf);;所有文件 (*)"
        )
        if paths:
            self.files_dropped.emit(paths)


# ── 文件列表项 ──────────────────────────────────────────────────────
class FileItem(QFrame):
    """文件列表中的单个项目"""
    removed = pyqtSignal(str)

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            FileItem {{
                background: transparent;
                border-radius: 8px;
                padding: 0 4px;
            }}
            FileItem:hover {{
                background-color: {THEME['item_hover']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(10)

        # 图标
        icon = QLabel("📄")
        icon.setFixedWidth(20)
        icon.setStyleSheet("font-size: 16px;")
        layout.addWidget(icon)

        # 文件名
        name = Path(filepath).name
        name_label = QLabel(name)
        name_label.setStyleSheet(f"font-size: 13px; color: {THEME['text']}; font-weight: 500;")
        name_label.setToolTip(filepath)
        layout.addWidget(name_label, 1)

        # 页数和大小
        info_parts = []
        try:
            doc = fitz.open(filepath)
            try:
                info_parts.append(f"{len(doc)} 页")
            finally:
                doc.close()
        except Exception:
            info_parts.append("读取失败")

        try:
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if size_mb >= 1:
                info_parts.append(f"{size_mb:.1f} MB")
            else:
                info_parts.append(f"{size_mb * 1024:.0f} KB")
        except OSError:
            pass

        info_label = QLabel("  ·  ".join(info_parts))
        info_label.setStyleSheet(f"font-size: 12px; color: {THEME['text2']};")
        layout.addWidget(info_label)

        # 删除按钮
        remove_btn = QPushButton("✕")
        remove_btn.setProperty("class", "icon-btn")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.filepath))
        layout.addWidget(remove_btn)


# ── 主窗口 ──────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF → Image")
        self.setMinimumSize(520, 640)
        self.resize(560, 720)
        self.files: list[str] = []
        self.worker: Optional[ConvertWorker] = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # ── 标题 ──
        title_row = QHBoxLayout()
        title = QLabel("PDF → Image")
        title.setProperty("class", "title")
        title_row.addWidget(title)
        title_row.addStretch()
        ver_label = QLabel(f"v{__version__}")
        ver_label.setStyleSheet(
            f"font-size: 12px; color: {THEME['text2']}; padding-top: 8px;"
        )
        title_row.addWidget(ver_label)
        root.addLayout(title_row)

        subtitle = QLabel("将 PDF 文档转换为高质量图片")
        subtitle.setProperty("class", "subtitle")
        root.addWidget(subtitle)
        root.addSpacing(20)

        # ── 拖拽区域 ──
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._add_files)
        root.addWidget(self.drop_zone)
        root.addSpacing(16)

        # ── 文件列表头 ──
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.file_count_label = QLabel("已添加文件 (0)")
        self.file_count_label.setProperty("class", "section-title")
        header.addWidget(self.file_count_label)
        header.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.setProperty("class", "link")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_files)
        header.addWidget(clear_btn)
        root.addLayout(header)
        root.addSpacing(8)

        # ── 文件列表 ──
        self.file_list_container = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_container)
        self.file_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_list_layout.setSpacing(2)
        self.file_list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self.file_list_container)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setMinimumHeight(50)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.file_scroll = scroll
        root.addWidget(scroll)
        root.addSpacing(20)

        # ── 输出设置卡片 ──
        settings_card = QFrame()
        settings_card.setProperty("class", "card")
        card_layout = QVBoxLayout(settings_card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(14)

        settings_title = QLabel("输出设置")
        settings_title.setProperty("class", "section-title")
        card_layout.addWidget(settings_title)

        # 第一行: 格式 + DPI
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        fmt_group = QVBoxLayout()
        fmt_label = QLabel("图片格式")
        fmt_label.setProperty("class", "label")
        fmt_group.addWidget(fmt_label)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["PNG", "JPG", "WEBP", "TIFF"])
        self.fmt_combo.setFixedWidth(130)
        fmt_group.addWidget(self.fmt_combo)
        row1.addLayout(fmt_group)

        dpi_group = QVBoxLayout()
        dpi_label = QLabel("分辨率 (DPI)")
        dpi_label.setProperty("class", "label")
        dpi_group.addWidget(dpi_label)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.setFixedWidth(130)
        dpi_group.addWidget(self.dpi_spin)
        row1.addLayout(dpi_group)

        row1.addStretch()
        card_layout.addLayout(row1)

        # 第二行: 页面范围
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        page_group = QVBoxLayout()
        page_label = QLabel("页面范围")
        page_label.setProperty("class", "label")
        page_group.addWidget(page_label)
        self.page_combo = QComboBox()
        self.page_combo.addItem("全部页面", "all")
        self.page_combo.addItem("仅首页", "first")
        self.page_combo.addItem("仅末页", "last")
        self.page_combo.addItem("自定义", "custom")
        self.page_combo.setFixedWidth(130)
        self.page_combo.currentIndexChanged.connect(self._on_page_mode_changed)
        page_group.addWidget(self.page_combo)
        row2.addLayout(page_group)

        range_group = QVBoxLayout()
        range_label = QLabel("自定义范围")
        range_label.setProperty("class", "label")
        range_group.addWidget(range_label)
        self.range_input = QLineEdit()
        self.range_input.setPlaceholderText("例: 1-3, 5, 7-10")
        self.range_input.setEnabled(False)
        self.range_input.setFixedWidth(160)
        range_group.addWidget(self.range_input)
        row2.addLayout(range_group)

        row2.addStretch()
        card_layout.addLayout(row2)

        # 第三行: 输出目录
        dir_group = QVBoxLayout()
        dir_label = QLabel("输出目录")
        dir_label.setProperty("class", "label")
        dir_group.addWidget(dir_label)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self.dir_input = QLineEdit()
        self.dir_input.setText(str(Path.home() / "Desktop"))
        self.dir_input.setReadOnly(True)
        dir_row.addWidget(self.dir_input)

        dir_btn = QPushButton("选择…")
        dir_btn.setProperty("class", "secondary")
        dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dir_btn.clicked.connect(self._choose_dir)
        dir_row.addWidget(dir_btn)

        dir_group.addLayout(dir_row)
        card_layout.addLayout(dir_group)

        root.addWidget(settings_card)
        root.addSpacing(20)

        # ── 进度区域 ──
        self.progress_label = QLabel("")
        self.progress_label.setProperty("class", "label")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.hide()
        root.addWidget(self.progress_label)
        root.addSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.hide()
        root.addWidget(self.progress_bar)
        root.addSpacing(16)

        # ── 底部按钮 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.setProperty("class", "secondary")
        self.open_dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_dir_btn.clicked.connect(self._open_output_dir)
        self.open_dir_btn.hide()
        btn_row.addWidget(self.open_dir_btn)

        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setProperty("class", "primary")
        self.convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_btn.setFixedWidth(160)
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        btn_row.addWidget(self.convert_btn)

        btn_row.addStretch()
        root.addLayout(btn_row)
        root.addStretch()

        # ── 底部作者信息 ──
        footer = QLabel(f"Made by Ken with Claude Code  ·  v{__version__}")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"font-size: 11px; color: {THEME['border']}; padding: 4px 0;")
        root.addWidget(footer)

        self._update_file_count()

    # ── 文件管理 ──────────────────────────────────────────────────

    def _add_files(self, paths: list[str]):
        for p in paths:
            p = str(Path(p).resolve())
            if p not in self.files:
                item = FileItem(p)
                item.removed.connect(self._remove_file)
                # 在 stretch 之前插入
                idx = self.file_list_layout.count() - 1
                self.file_list_layout.insertWidget(idx, item)
        self._update_file_count()

    def _remove_file(self, filepath: str):
        if filepath in self.files:
            self.files.remove(filepath)
        # 从布局中移除对应 widget
        for i in range(self.file_list_layout.count()):
            w = self.file_list_layout.itemAt(i).widget()
            if isinstance(w, FileItem) and w.filepath == filepath:
                w.setParent(None)
                w.deleteLater()
                break
        self._update_file_count()

    def _clear_files(self):
        self.files.clear()
        while self.file_list_layout.count() > 1:  # 保留 stretch
            item = self.file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._update_file_count()

    def _update_file_count(self):
        n = len(self.files)
        self.file_count_label.setText(f"已添加文件 ({n})")
        self.convert_btn.setEnabled(n > 0)

    # ── 设置交互 ──────────────────────────────────────────────────

    def _on_page_mode_changed(self, _index: int):
        is_custom = self.page_combo.currentData() == "custom"
        self.range_input.setEnabled(is_custom)
        if not is_custom:
            self.range_input.clear()

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.dir_input.text()
        )
        if d:
            self.dir_input.setText(d)

    def _open_output_dir(self):
        path = self.dir_input.text()
        if os.path.isdir(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # ── 转换逻辑 ──────────────────────────────────────────────────

    def _on_convert_clicked(self):
        if self.worker and self.worker.isRunning():
            # 正在转换，点击取消
            self.worker.cancel()
            self.convert_btn.setText("正在取消...")
            self.convert_btn.setEnabled(False)
            return

        if not self.files:
            return

        output_dir = self.dir_input.text()
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        page_mode = self.page_combo.currentData()

        if page_mode == "custom" and not self.range_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入自定义页面范围")
            return

        fmt = self.fmt_combo.currentText()
        dpi = self.dpi_spin.value()

        self.worker = ConvertWorker(
            files=list(self.files),
            fmt=fmt,
            dpi=dpi,
            page_mode=page_mode,
            page_range=self.range_input.text(),
            output_dir=output_dir,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

        # UI 状态
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("准备转换...")
        self.progress_label.show()
        self.open_dir_btn.hide()
        self.convert_btn.setText("取消转换")
        self._set_inputs_enabled(False)

        self.worker.start()

    def _on_progress(self, current: int, total: int, msg: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        pct = int(current / total * 100) if total else 0
        self.progress_label.setText(f"{msg}  ({current}/{total} · {pct}%)")

    def _on_finished(self, ok: int, fail: int):
        self.convert_btn.setText("开始转换")
        self.convert_btn.setEnabled(True)
        self._set_inputs_enabled(True)
        self.open_dir_btn.show()

        if fail == 0:
            self.progress_label.setText(
                f'<span style="color:{THEME["success"]}; font-weight:600;">'
                f"✓ 转换完成！共 {ok} 张图片</span>"
            )
            self.progress_bar.setValue(self.progress_bar.maximum())
        else:
            self.progress_label.setText(
                f'<span style="color:{THEME["text"]};">'
                f"完成 {ok} 张，失败 {fail} 张</span>"
            )

    def _on_error(self, msg: str):
        self.progress_label.setText(
            f'<span style="color:{THEME["danger"]};">{msg}</span>'
        )

    def _set_inputs_enabled(self, enabled: bool):
        self.drop_zone.setEnabled(enabled)
        self.fmt_combo.setEnabled(enabled)
        self.dpi_spin.setEnabled(enabled)
        self.page_combo.setEnabled(enabled)
        self.range_input.setEnabled(enabled and self.page_combo.currentData() == "custom")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(5000)
        event.accept()


# ── 入口 ────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # macOS 专属调优
    font = app.font()
    font.setFamily("-apple-system")
    font.setPointSize(13)
    app.setFont(font)

    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
