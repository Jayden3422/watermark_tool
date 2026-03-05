# -*- coding: utf-8 -*-
import sys
from dataclasses import asdict

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QFileDialog, QLineEdit, QFormLayout, QHBoxLayout, QVBoxLayout,
    QDoubleSpinBox, QSpinBox, QGroupBox, QMessageBox, QScrollArea,
    QComboBox, QColorDialog, QSplitter, QFrame, QSizePolicy, QBoxLayout
)

from watermark_core import WatermarkParams, apply_watermark, save_image, list_installed_fonts_windows


def pil_to_pixmap(pil_img: Image.Image) -> QPixmap:
    qimage = ImageQt(pil_img.convert("RGBA"))
    return QPixmap.fromImage(qimage)


def pick_default_yahei_bold(font_names: list[str]) -> str | None:
    prefers = [
      ("Microsoft YaHei UI", "bold"),
      ("Microsoft YaHei", "bold"),
      ("YaHei", "bold"),
      ("微软雅黑", "粗体"),
      ("微软雅黑", "bold"),
      ("Microsoft YaHei", ""),
      ("微软雅黑", ""),
    ]
    for a, b in prefers:
        for n in font_names:
          ln = n.lower()
          if a.lower() in ln and (b.lower() in ln if b else True):
            return n
    return None


I18N = {
    "zh": {
        "window_title": "斜向水印工具 (Win11)",
        "title": "斜向水印工具",
        "subtitle": "选择图片 → 调整参数 → 导出结果（左侧可滚动，右侧预览可滚动）",
        "lang_label": "语言",
        "preview_hint": "预览区：请先选择图片",
        "grp_file": "文件",
        "btn_open": "选择/替换图片…",
        "btn_export": "导出结果…",
        "no_image": "未选择图片",
        "grp_font": "字体",
        "font_search_ph": "输入关键字搜索字体…",
        "grp_style": "外观",
        "grp_layout": "排布",
        "dlg_open": "选择图片",
        "dlg_export": "导出结果",
        "dlg_color": "选择文字颜色",
        "dlg_fontfile": "选择字体文件",
        "msg_tip": "提示",
        "msg_choose_first": "请先选择图片。",
        "msg_open_failed": "打开失败",
        "msg_export_failed": "导出失败",
        "msg_success": "成功",
        "msg_exported": "已导出：\n{path}\n\n参数：\n{params}",
        "font_state_sys": "当前：使用系统字体：{sys_font}",
        "font_state_custom": "当前：字体文件覆盖中\n{path}\n（系统字体选择仍为：{sys_font}）",
        "default_wm_text": "仅供入职核验 – [公司名称]",
        # 表单 label（按你的布局行顺序）
        "lbl_system_font": "系统字体",
        "lbl_font_override": "字体文件覆盖",
        "lbl_text_color": "文字颜色",
        "lbl_opacity": "不透明度",
        "lbl_angle": "倾斜角度(°)",
        "lbl_font_ratio": "字号比例",
        "lbl_wm_text": "水印文字",
        "lbl_stepx": "水平间距系数",
        "lbl_stepy": "垂直间距系数",
        "lbl_shift": "行交错位移",
        "lbl_minrep": "每行至少重复",
        "lbl_stroke": "描边宽度",
        "btn_pick_font": "选择字体文件…",
        "btn_clear_font": "清除覆盖",
        "btn_pick_color": "选择颜色…",
    },
    "en": {
        "window_title": "Diagonal Watermark Tool (Win11)",
        "title": "Diagonal Watermark Tool",
        "subtitle": "Choose image → Adjust settings → Export (left & preview panels are scrollable)",
        "lang_label": "Language",
        "preview_hint": "Preview: choose an image first",
        "grp_file": "File",
        "btn_open": "Open/Replace Image…",
        "btn_export": "Export…",
        "no_image": "No image selected",
        "grp_font": "Font",
        "font_search_ph": "Type to search fonts…",
        "grp_style": "Style",
        "grp_layout": "Layout",
        "dlg_open": "Open Image",
        "dlg_export": "Export",
        "dlg_color": "Pick Text Color",
        "dlg_fontfile": "Choose Font File",
        "msg_tip": "Info",
        "msg_choose_first": "Please choose an image first.",
        "msg_open_failed": "Open failed",
        "msg_export_failed": "Export failed",
        "msg_success": "Done",
        "msg_exported": "Exported:\n{path}\n\nParams:\n{params}",
        "font_state_sys": "Using system font: {sys_font}",
        "font_state_custom": "Overriding with font file:\n{path}\n(System font selection is still: {sys_font})",
        "default_wm_text": "For employment verification only – [Company Name]",
        "lbl_system_font": "System font",
        "lbl_font_override": "Override font file",
        "lbl_text_color": "Text color",
        "lbl_opacity": "Opacity",
        "lbl_angle": "Angle (°)",
        "lbl_font_ratio": "Font size ratio",
        "lbl_wm_text": "Watermark text",
        "lbl_stepx": "Horizontal spacing",
        "lbl_stepy": "Vertical spacing",
        "lbl_shift": "Row stagger shift",
        "lbl_minrep": "Min repeats/row",
        "lbl_stroke": "Stroke width",
        "btn_pick_font": "Choose font file…",
        "btn_clear_font": "Clear override",
        "btn_pick_color": "Pick color…",
    },
}


class MainWindow(QMainWindow):
    def __init__(self):
      super().__init__()
      self.setWindowTitle("Diagonal Watermark Tool (Win11)")
      self.resize(1200, 800)

      self.lang = "en"
      self.params = WatermarkParams()
      self.default_text_by_lang = {
          "zh": I18N["zh"]["default_wm_text"],
          "en": I18N["en"]["default_wm_text"],
      }
      self.params.text = self.default_text_by_lang[self.lang]
      self.src_image: Image.Image | None = None
      self.src_path: str | None = None

      # 字体：系统字体映射 + 自选字体文件
      self.installed_fonts = list_installed_fonts_windows()
      self.custom_font_path: str | None = None

      # 颜色
      r, g, b = self.params.color_rgb
      self.current_color = QColor(int(r), int(g), int(b))

      # 预览防抖
      self.preview_timer = QTimer(self)
      self.preview_timer.setSingleShot(True)
      self.preview_timer.timeout.connect(self.update_preview)

      # ===== 主体：左右分割 =====
      root = QWidget()
      self.setCentralWidget(root)
      root_layout = QVBoxLayout(root)
      root_layout.setContentsMargins(10, 10, 10, 10)
      root_layout.setSpacing(10)

      splitter = QSplitter(Qt.Horizontal)
      root_layout.addWidget(splitter)

      # ===== 左侧：参数区（可滚动）=====
      left_panel = QWidget()
      left_layout = QVBoxLayout(left_panel)
      left_layout.setContentsMargins(0, 0, 0, 0)
      left_layout.setSpacing(10)

      left_scroll = QScrollArea()
      left_scroll.setWidgetResizable(True)
      left_scroll.setFrameShape(QFrame.NoFrame)
      left_scroll.setWidget(left_panel)

      splitter.addWidget(left_scroll)
      splitter.setChildrenCollapsible(False)
      left_scroll.setMinimumWidth(380)  # 按UI实际调整

      # ===== 右侧：预览区 =====
      right_panel = QWidget()
      right_layout = QVBoxLayout(right_panel)
      right_layout.setContentsMargins(0, 0, 0, 0)
      right_layout.setSpacing(10)

      self.preview_label = QLabel("预览区：请先选择图片")
      self.preview_label.setAlignment(Qt.AlignCenter)
      self.preview_label.setStyleSheet("QLabel{color:#666; font-size:14px;}")
      self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

      # ===== 右侧：预览区 =====
      self.preview_label = QLabel(self.tr("preview_hint"))
      self.preview_label.setAlignment(Qt.AlignCenter)
      self.preview_label.setStyleSheet("QLabel{color:#666; font-size:14px;}")
      self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

      self.preview_scroll = QScrollArea()
      self.preview_scroll.setWidgetResizable(True)
      self.preview_scroll.setFrameShape(QFrame.StyledPanel)
      self.preview_scroll.setWidget(self.preview_label)

      # 关键：始终“整图可见”，所以禁用滚动条（可选）
      self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

      # 关键：给边框留出内边距，避免视觉上被边框“盖住”
      self.preview_scroll.setViewportMargins(8, 8, 8, 8)

      right_layout.addWidget(self.preview_scroll)

      # 保存“原始预览 pixmap”（未缩放）
      self._preview_pixmap_src: QPixmap | None = None

      # 监听 viewport 尺寸变化（拖 splitter 也会触发），自动重新缩放
      self.preview_scroll.viewport().installEventFilter(self)

      splitter.addWidget(right_panel)

      splitter.setStretchFactor(0, 0)
      splitter.setStretchFactor(1, 1)
      splitter.setSizes([420, 780])

      # ===== 顶部说明 =====
      self.title_label = QLabel()
      self.title_label.setStyleSheet("QLabel{font-size:18px; font-weight:700;}")
      self.subtitle_label = QLabel()
      self.subtitle_label.setStyleSheet("QLabel{color:#666;}")
      left_layout.addWidget(self.title_label)
      left_layout.addWidget(self.subtitle_label)

      # ===== 语言切换 =====
      lang_row = QHBoxLayout()
      self.lbl_lang = QLabel()
      self.cmb_lang = QComboBox()
      self.cmb_lang.addItem("中文", "zh")
      self.cmb_lang.addItem("English", "en")
      self.cmb_lang.setCurrentIndex(0 if self.lang == "zh" else 1)
      self.cmb_lang.currentIndexChanged.connect(self.on_lang_changed)
      lang_row.addWidget(self.lbl_lang)
      lang_row.addWidget(self.cmb_lang)
      lang_row.addStretch(1)
      left_layout.addLayout(lang_row)

      # ===== Group 1：文件 =====
      grp_file = QGroupBox("文件")
      self.grp_file = grp_file
      file_layout = QVBoxLayout(grp_file)
      file_layout.setContentsMargins(12, 14, 12, 12)
      file_layout.setSpacing(8)

      row_btn = QBoxLayout(QBoxLayout.LeftToRight)
      self.file_btn_layout = row_btn
      self.btn_open = QPushButton("选择/替换图片…")
      self.btn_open.clicked.connect(self.open_image)
      self.btn_export = QPushButton("导出结果…")
      self.btn_export.clicked.connect(self.export_image)
      row_btn.addWidget(self.btn_open, 1)
      row_btn.addWidget(self.btn_export, 1)
      file_layout.addLayout(row_btn)

      self.btn_open.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
      self.btn_open.setMinimumWidth(0)
      self.btn_export.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
      self.btn_export.setMinimumWidth(0)

      self.lbl_path = QLabel("未选择图片")
      self.lbl_path.setWordWrap(True)
      self.lbl_path.setStyleSheet("QLabel{color:#555;}")
      file_layout.addWidget(self.lbl_path)

      left_layout.addWidget(grp_file)

      # ===== Group 2：字体 =====
      grp_font = QGroupBox("字体")
      font_layout = QFormLayout(grp_font)
      self.font_layout = font_layout
      self.grp_font = grp_font
      font_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)
      font_layout.setContentsMargins(12, 14, 12, 12)
      font_layout.setHorizontalSpacing(10)
      font_layout.setVerticalSpacing(10)
      font_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
      font_layout.setFormAlignment(Qt.AlignTop)
      font_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

      # 系统字体下拉（可输入搜索）
      self.cmb_fonts = QComboBox()
      self.cmb_fonts.setEditable(True)
      self.cmb_fonts.setInsertPolicy(QComboBox.NoInsert)
      self.cmb_fonts.setMinimumHeight(30)
      self.cmb_fonts.lineEdit().setPlaceholderText("输入关键字搜索字体…")
      self.cmb_fonts.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
      self.cmb_fonts.setMinimumContentsLength(18)
      self.cmb_fonts.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)

      names = sorted(self.installed_fonts.keys(), key=lambda s: s.lower())
      if names:
        self.cmb_fonts.addItems(names)
        default_font = pick_default_yahei_bold(names)
        if default_font:
            self.cmb_fonts.setCurrentText(default_font)
            self.params.font_name = default_font
      else:
        self.cmb_fonts.addItem("（未检测到系统字体）")
        self.cmb_fonts.setEnabled(False)

      self.cmb_fonts.currentTextChanged.connect(self.on_system_font_changed)
      font_layout.addRow("系统字体", self.cmb_fonts)

      # 字体文件覆盖 + 清除
      font_file_row = QWidget()
      font_file_h = QBoxLayout(QBoxLayout.LeftToRight)
      font_file_row.setLayout(font_file_h)
      self.font_btn_layout = font_file_h
      font_file_h.setContentsMargins(0, 0, 0, 0)
      font_file_h.setSpacing(8)

      self.btn_pick_font_file = QPushButton()
      self.btn_pick_font_file.clicked.connect(self.pick_font_file)
      self.btn_pick_font_file.clicked.connect(self.pick_font_file)

      self.btn_clear_font = QPushButton()
      self.btn_clear_font.clicked.connect(self.clear_font_file)
      self.btn_clear_font.clicked.connect(self.clear_font_file)

      # 长按钮允许被压缩（忽略 sizeHint），避免挤掉右侧按钮
      self.btn_pick_font_file.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
      self.btn_pick_font_file.setMinimumWidth(0)

      # 清除按钮尽量保持完整显示
      self.btn_clear_font.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
      self.btn_clear_font.setMinimumWidth(0)

      font_file_h.addWidget(self.btn_pick_font_file, 1)
      font_file_h.addWidget(self.btn_clear_font, 0)

      font_layout.addRow("字体文件覆盖", font_file_row)

      self.lbl_font_state = QLabel("当前：使用系统字体（默认优先微软雅黑-粗体）")
      self.lbl_font_state.setWordWrap(True)
      self.lbl_font_state.setStyleSheet("QLabel{color:#666;}")
      font_layout.addRow("", self.lbl_font_state)

      left_layout.addWidget(grp_font)

      # ===== Group 3：外观（颜色/不透明度/字号/角度）=====
      grp_style = QGroupBox("外观")
      style_form = QFormLayout(grp_style)
      self.style_form = style_form
      self.grp_style = grp_style
      style_form.setContentsMargins(12, 14, 12, 12)
      style_form.setHorizontalSpacing(10)
      style_form.setVerticalSpacing(10)
      style_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
      style_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

      # 文字颜色选择
      color_row = QWidget()
      color_h = QHBoxLayout(color_row)
      color_h.setContentsMargins(0, 0, 0, 0)
      color_h.setSpacing(8)

      self.btn_pick_color = QPushButton()
      self.btn_pick_color.clicked.connect(self.pick_color)

      self.color_swatch = QFrame()
      self.color_swatch.setFixedSize(26, 26)
      self.color_swatch.setFrameShape(QFrame.StyledPanel)

      self.lbl_color_hex = QLabel()
      self.lbl_color_hex.setStyleSheet("QLabel{color:#666;}")

      color_h.addWidget(self.btn_pick_color, 0)
      color_h.addWidget(self.color_swatch, 0)
      color_h.addWidget(self.lbl_color_hex, 1)

      style_form.addRow("文字颜色", color_row)

      self.sp_opacity = QSpinBox()
      self.sp_opacity.setRange(0, 255)
      self.sp_opacity.setValue(self.params.opacity)
      self.sp_opacity.valueChanged.connect(self.schedule_preview)
      self.sp_opacity.setMinimumHeight(30)
      style_form.addRow("不透明度", self.sp_opacity)

      self.sp_angle = QDoubleSpinBox()
      self.sp_angle.setRange(-89.0, 89.0)
      self.sp_angle.setSingleStep(1.0)
      self.sp_angle.setValue(self.params.angle_deg)
      self.sp_angle.valueChanged.connect(self.schedule_preview)
      self.sp_angle.setMinimumHeight(30)
      style_form.addRow("倾斜角度(°)", self.sp_angle)

      self.sp_font_ratio = QDoubleSpinBox()
      self.sp_font_ratio.setRange(0.005, 0.2)
      self.sp_font_ratio.setSingleStep(0.005)
      self.sp_font_ratio.setDecimals(3)
      self.sp_font_ratio.setValue(self.params.font_size_ratio)
      self.sp_font_ratio.valueChanged.connect(self.schedule_preview)
      self.sp_font_ratio.setMinimumHeight(30)
      style_form.addRow("字号比例", self.sp_font_ratio)

      left_layout.addWidget(grp_style)

      # ===== Group 4：排布（间距/位移/重复/描边）=====
      grp_layout = QGroupBox("排布")
      layout_form = QFormLayout(grp_layout)
      self.layout_form = layout_form
      self.grp_layout = grp_layout
      layout_form.setContentsMargins(12, 14, 12, 12)
      layout_form.setHorizontalSpacing(10)
      layout_form.setVerticalSpacing(10)
      layout_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
      layout_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

      self.ed_text = QLineEdit(self.params.text)
      self.ed_text.textChanged.connect(self.schedule_preview)
      self.ed_text.setMinimumHeight(30)
      layout_form.addRow("水印文字", self.ed_text)

      self.sp_stepx = QDoubleSpinBox()
      self.sp_stepx.setRange(0.5, 10.0)
      self.sp_stepx.setSingleStep(0.1)
      self.sp_stepx.setValue(self.params.step_x_ratio)
      self.sp_stepx.valueChanged.connect(self.schedule_preview)
      self.sp_stepx.setMinimumHeight(30)
      layout_form.addRow("水平间距系数", self.sp_stepx)

      self.sp_stepy = QDoubleSpinBox()
      self.sp_stepy.setRange(0.5, 10.0)
      self.sp_stepy.setSingleStep(0.1)
      self.sp_stepy.setValue(self.params.step_y_ratio)
      self.sp_stepy.valueChanged.connect(self.schedule_preview)
      self.sp_stepy.setMinimumHeight(30)
      layout_form.addRow("垂直间距系数", self.sp_stepy)

      self.sp_shift = QDoubleSpinBox()
      self.sp_shift.setRange(0.0, 1.0)
      self.sp_shift.setSingleStep(0.05)
      self.sp_shift.setValue(self.params.shift_ratio)
      self.sp_shift.valueChanged.connect(self.schedule_preview)
      self.sp_shift.setMinimumHeight(30)
      layout_form.addRow("行交错位移", self.sp_shift)

      self.sp_minrep = QDoubleSpinBox()
      self.sp_minrep.setRange(1.0, 20.0)
      self.sp_minrep.setSingleStep(0.1)
      self.sp_minrep.setDecimals(1)
      self.sp_minrep.setValue(float(self.params.min_repeat_per_row))
      self.sp_minrep.valueChanged.connect(self.schedule_preview)
      self.sp_minrep.setMinimumHeight(30)
      layout_form.addRow("每行至少重复", self.sp_minrep)

      self.sp_stroke = QSpinBox()
      self.sp_stroke.setRange(0, 8)
      self.sp_stroke.setValue(self.params.stroke_width)
      self.sp_stroke.valueChanged.connect(self.schedule_preview)
      self.sp_stroke.setMinimumHeight(30)
      layout_form.addRow("描边宽度", self.sp_stroke)

      left_layout.addWidget(grp_layout)
      left_layout.addStretch(1)

      # 统一按钮高度
      for b in [self.btn_open, self.btn_export, self.btn_pick_font_file, self.btn_clear_font, self.btn_pick_color]:
        b.setMinimumHeight(34)

      # 初始化颜色预览 & 字体状态
      self.update_color_preview()
      self.refresh_font_state_label()

      self.apply_language()

      # 轻量美化（不和系统主题打架）
      self.setStyleSheet("""
          QGroupBox {
              font-weight: 600;
              border: 1px solid rgba(0,0,0,0.15);
              border-radius: 8px;
              margin-top: 8px;
          }
          QGroupBox::title {
              subcontrol-origin: margin;
              left: 10px;
              padding: 0 6px;
          }
          QPushButton {
              padding: 6px 10px;
          }
          QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
              padding: 4px 8px;
          }
      """)
    
      self._update_button_rows_layout()

    # ===== UI helpers =====
    def update_color_preview(self):
        hex_color = self.current_color.name()
        self.lbl_color_hex.setText(hex_color)
        self.color_swatch.setStyleSheet(
          f"background-color: {hex_color}; border: 1px solid rgba(0,0,0,0.25); border-radius: 4px;"
        )
    
    def _update_button_rows_layout(self):
      # 你可以按体验调整阈值
      compact = self.width() < 900 or self.centralWidget().width() < 900

      # 文件按钮行
      if hasattr(self, "file_btn_layout"):
        self.file_btn_layout.setDirection(QBoxLayout.TopToBottom if compact else QBoxLayout.LeftToRight)

      # 字体覆盖按钮行
      if hasattr(self, "font_btn_layout"):
        self.font_btn_layout.setDirection(QBoxLayout.TopToBottom if compact else QBoxLayout.LeftToRight)
    
    def tr(self, key: str) -> str:
        return I18N.get(self.lang, I18N["zh"]).get(key, key)

    def _set_form_label(self, form, row: int, text: str):
        item = form.itemAt(row, QFormLayout.LabelRole)
        if item and item.widget():
            w = item.widget()
            if isinstance(w, QLabel):
                w.setText(text)
    
    def resizeEvent(self, e):
      super().resizeEvent(e)
      self._update_button_rows_layout()
      self._rescale_preview()
    
    def _rescale_preview(self):
      """把原始预览图等比缩放到当前可视区域，保证整图可见。"""
      if not self._preview_pixmap_src or not hasattr(self, "preview_scroll"):
        return

      size = self.preview_scroll.viewport().size()
      if size.width() <= 0 or size.height() <= 0:
        return

      scaled = self._preview_pixmap_src.scaled(
        size, Qt.KeepAspectRatio, Qt.SmoothTransformation
      )
      self.preview_label.setPixmap(scaled)


    def eventFilter(self, obj, event):
      # viewport 尺寸变化（包含拖 splitter）时，重新 fit-to-view
      if hasattr(self, "preview_scroll") and obj is self.preview_scroll.viewport():
        if event.type() == QEvent.Type.Resize:
          self._rescale_preview()
      return super().eventFilter(obj, event)

    def apply_language(self):
        self.setWindowTitle(self.tr("window_title"))

        # 顶部
        if self._preview_pixmap_src is None:
          self.preview_label.setText(self.tr("preview_hint"))
        self.title_label.setText(self.tr("title"))
        self.subtitle_label.setText(self.tr("subtitle"))

        self.lbl_lang.setText(self.tr("lang_label"))

        # group titles
        self.grp_file.setTitle(self.tr("grp_file"))
        self.grp_font.setTitle(self.tr("grp_font"))
        self.grp_style.setTitle(self.tr("grp_style"))
        self.grp_layout.setTitle(self.tr("grp_layout"))

        # buttons
        self.btn_open.setText(self.tr("btn_open"))
        self.btn_export.setText(self.tr("btn_export"))
        self.btn_pick_font_file.setText(self.tr("btn_pick_font"))
        self.btn_clear_font.setText(self.tr("btn_clear_font"))
        self.btn_pick_color.setText(self.tr("btn_pick_color"))

        # misc labels
        if not self.src_path:
            self.lbl_path.setText(self.tr("no_image"))

        # placeholder
        if self.cmb_fonts.isEnabled() and self.cmb_fonts.lineEdit():
            self.cmb_fonts.lineEdit().setPlaceholderText(self.tr("font_search_ph"))

        # form labels（按你 addRow 的顺序）
        self._set_form_label(self.font_layout, 0, self.tr("lbl_system_font"))
        self._set_form_label(self.font_layout, 1, self.tr("lbl_font_override"))

        self._set_form_label(self.style_form, 0, self.tr("lbl_text_color"))
        self._set_form_label(self.style_form, 1, self.tr("lbl_opacity"))
        self._set_form_label(self.style_form, 2, self.tr("lbl_angle"))
        self._set_form_label(self.style_form, 3, self.tr("lbl_font_ratio"))

        self._set_form_label(self.layout_form, 0, self.tr("lbl_wm_text"))
        self._set_form_label(self.layout_form, 1, self.tr("lbl_stepx"))
        self._set_form_label(self.layout_form, 2, self.tr("lbl_stepy"))
        self._set_form_label(self.layout_form, 3, self.tr("lbl_shift"))
        self._set_form_label(self.layout_form, 4, self.tr("lbl_minrep"))
        self._set_form_label(self.layout_form, 5, self.tr("lbl_stroke"))

        self.refresh_font_state_label()

    def on_lang_changed(self):
        old = self.lang
        self.lang = self.cmb_lang.currentData() or "zh"

        # 如果用户没改过水印文字，就跟着语言自动切换默认文案
        if self.ed_text.text() == self.default_text_by_lang.get(old, ""):
            self.ed_text.setText(self.default_text_by_lang.get(self.lang, self.ed_text.text()))

        self.apply_language()
        self.schedule_preview()

    def refresh_font_state_label(self):
      sys_font = self.cmb_fonts.currentText() if self.cmb_fonts.isEnabled() else "N/A"
      if self.custom_font_path:
        self.lbl_font_state.setText(self.tr("font_state_custom").format(path=self.custom_font_path, sys_font=sys_font))
      else:
        self.lbl_font_state.setText(self.tr("font_state_sys").format(sys_font=sys_font))

    # ===== Actions =====
    def pick_color(self):
        c = QColorDialog.getColor(self.current_color, self, self.tr("dlg_color"))
        if c.isValid():
          self.current_color = c
          self.update_color_preview()
          self.schedule_preview()

    def on_system_font_changed(self, _name: str):
        self.refresh_font_state_label()
        self.schedule_preview()

    def pick_font_file(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("dlg_fontfile"), "", "Font Files (*.ttf *.ttc *.otf);;All Files (*.*)")
        if path:
            self.custom_font_path = path
            self.refresh_font_state_label()
            self.schedule_preview()

    def clear_font_file(self):
        self.custom_font_path = None
        self.refresh_font_state_label()
        self.schedule_preview()

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("dlg_open"), "", "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                img = Image.open(f)
                img.load()  # 强制读入，避免文件句柄关闭后再懒加载出错
            self.src_image = img
            self.src_path = path
            self.lbl_path.setText(path)
            self.update_preview()
        except Exception as e:
            QMessageBox.critical(self, self.tr("msg_open_failed"), str(e))

    def gather_params(self) -> WatermarkParams:
        rgb = (self.current_color.red(), self.current_color.green(), self.current_color.blue())
        p = WatermarkParams(
            text=self.ed_text.text(),
            angle_deg=float(self.sp_angle.value()),
            font_size_ratio=float(self.sp_font_ratio.value()),
            color_rgb=rgb,
            opacity=int(self.sp_opacity.value()),
            step_x_ratio=float(self.sp_stepx.value()),
            step_y_ratio=float(self.sp_stepy.value()),
            shift_ratio=float(self.sp_shift.value()),
            min_repeat_per_row=float(self.sp_minrep.value()),
            stroke_width=int(self.sp_stroke.value()),
            font_name=self.cmb_fonts.currentText() if self.cmb_fonts.isEnabled() else None,
            font_index=0,
            font_path=self.custom_font_path,
        )
        return p

    def schedule_preview(self):
        self.preview_timer.start(180)

    def update_preview(self):
        if self.src_image is None:
            return

        p = self.gather_params()

        preview = self.src_image.copy()
        preview.thumbnail((1600, 1600))
        try:
          out = apply_watermark(preview, p)
          pix = pil_to_pixmap(out)
          self._preview_pixmap_src = pix          # 保存原始预览图
          self._rescale_preview()                # 按 viewport 等比缩放显示
        except Exception as e:
          self.preview_label.setText(f"预览失败：{e}")

    def export_image(self):
        if self.src_image is None:
            QMessageBox.information(self, self.tr("msg_tip"), self.tr("msg_choose_first"))
            return

        default_name = "watermarked.png"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("dlg_export"), default_name, "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;WEBP (*.webp)"
        )
        if not path:
            return

        p = self.gather_params()
        try:
            out_full = apply_watermark(self.src_image, p)
            save_image(out_full, path)
            QMessageBox.information(
              self,
              self.tr("msg_success"),
              self.tr("msg_exported").format(path=path, params=asdict(p)),
            )
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())