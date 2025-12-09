import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QStackedWidget, QListWidget, QListWidgetItem, QGroupBox, QCheckBox, QLabel, QSlider, QComboBox)
from PyQt5.QtCore import Qt, QSize, QEvent, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPalette
from PyQt5.QtSvg import QSvgRenderer

# 서브 애플리케이션 호출~!
from modeler_ui_and_chang import MainWindow as ModelerWindow
from miro_ui_and_chang import MiroWindow
from miro_sound import SoundManager


class SettingsPage(QWidget):
    """전역 설정 페이지"""
    gpuAccelerationChanged = pyqtSignal(bool)
    shadowQualityChanged = pyqtSignal(str)  # "Off", "Low", "High"
    volumeChanged = pyqtSignal(int)
    moveSpeedChanged = pyqtSignal(int) # 0 ~ 100% -> scale to 0.04 ~ 0.16
    mouseSensitivityChanged = pyqtSignal(int) # 0 ~ 100% -> scale to 0.05 ~ 0.30

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 타이틀
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # 그래픽 설정 그룹
        graphics_group = QGroupBox("Graphics")
        graphics_layout = QVBoxLayout()

        self.chk_gpu_accel = QCheckBox("GPU Acceleration (VBO)")
        self.chk_gpu_accel.setChecked(True)
        self.chk_gpu_accel.setToolTip("Enable VBO-based rendering for better performance")
        self.chk_gpu_accel.stateChanged.connect(self._on_gpu_accel_changed)
        graphics_layout.addWidget(self.chk_gpu_accel)

        # Shadow Quality
        shadow_layout = QHBoxLayout()
        shadow_layout.addWidget(QLabel("Shadow Quality:"))
        self.combo_shadow = QComboBox()
        self.combo_shadow.addItems(["Off", "Low", "High"])
        self.combo_shadow.setCurrentText("Low")
        self.combo_shadow.currentTextChanged.connect(self._on_shadow_changed)
        shadow_layout.addWidget(self.combo_shadow)
        shadow_layout.addStretch()
        graphics_layout.addLayout(shadow_layout)

        graphics_group.setLayout(graphics_layout)
        layout.addWidget(graphics_group)

        # 오디오 설정 그룹
        audio_group = QGroupBox("Audio")
        audio_layout = QVBoxLayout()
        
        # 볼륨 슬라이더
        volume_label_layout = QHBoxLayout()
        volume_label_layout.addWidget(QLabel("Master Volume:"))
        self.lbl_volume_value = QLabel("100%")
        volume_label_layout.addWidget(self.lbl_volume_value)
        volume_label_layout.addStretch()
        audio_layout.addLayout(volume_label_layout)

        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.setTickPosition(QSlider.TicksBelow)
        self.slider_volume.setTickInterval(10)
        self.slider_volume.valueChanged.connect(self._on_volume_changed)
        audio_layout.addWidget(self.slider_volume)
        
        audio_group.setLayout(audio_layout)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # 게임플레이 설정 그룹
        gameplay_group = QGroupBox("Controls")
        gameplay_layout = QVBoxLayout()

        # 1. 이동 속도 (50% ~ 200%)
        speed_label_layout = QHBoxLayout()
        speed_label_layout.addWidget(QLabel("Movement Speed:"))
        self.lbl_speed_value = QLabel("100%")
        speed_label_layout.addWidget(self.lbl_speed_value)
        speed_label_layout.addStretch()
        gameplay_layout.addLayout(speed_label_layout)
        
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(50, 200) # 퍼센트
        self.slider_speed.setValue(100)
        self.slider_speed.setTickPosition(QSlider.TicksBelow)
        self.slider_speed.setTickInterval(25)
        self.slider_speed.valueChanged.connect(self._on_speed_changed)
        gameplay_layout.addWidget(self.slider_speed)

        # 2. 마우스 감도 (50% ~ 200%)
        sens_label_layout = QHBoxLayout()
        sens_label_layout.addWidget(QLabel("Mouse Sensitivity:"))
        self.lbl_sens_value = QLabel("100%")
        sens_label_layout.addWidget(self.lbl_sens_value)
        sens_label_layout.addStretch()
        gameplay_layout.addLayout(sens_label_layout)
        
        self.slider_sens = QSlider(Qt.Horizontal)
        self.slider_sens.setRange(50, 200) # 퍼센트
        self.slider_sens.setValue(100)
        self.slider_sens.setTickPosition(QSlider.TicksBelow)
        self.slider_sens.setTickInterval(25)
        self.slider_sens.valueChanged.connect(self._on_sens_changed)
        gameplay_layout.addWidget(self.slider_sens)

        gameplay_group.setLayout(gameplay_layout)
        layout.addWidget(gameplay_group)

        layout.addStretch()

    def _on_gpu_accel_changed(self, state):
        enabled = (state == Qt.Checked)
        self.gpuAccelerationChanged.emit(enabled)

    def _on_shadow_changed(self, text):
        self.shadowQualityChanged.emit(text)

    def _on_volume_changed(self, value):
        self.lbl_volume_value.setText(f"{value}%")
        self.volumeChanged.emit(value)
        
    def _on_speed_changed(self, value):
        self.lbl_speed_value.setText(f"{value}%")
        self.moveSpeedChanged.emit(value)
        
    def _on_sens_changed(self, value):
        self.lbl_sens_value.setText(f"{value}%")
        self.mouseSensitivityChanged.emit(value)


class MainContainer(QMainWindow):
    """
    메인 컨테이너 윈도우
    좌측 사이드바를 통해 모델러와 미로 게임을 전환합니다.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyOpenGL Project: Modeler & Maze")
        self.resize(1280, 800)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃 잡기
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- 1. 사이드바 ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(52)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(5, 35, 5, 5)
        sidebar_layout.setSpacing(0)

        # 사이드바 메뉴 아이템
        self.menu_list = QListWidget()
        self.menu_list.setFocusPolicy(Qt.NoFocus)
        self.menu_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # IconMode 설정 (중앙 정렬을 위해)
        self.menu_list.setViewMode(QListWidget.IconMode)
        self.menu_list.setFlow(QListWidget.LeftToRight)
        self.menu_list.setMovement(QListWidget.Static)
        self.menu_list.setResizeMode(QListWidget.Adjust)
        self.menu_list.setGridSize(QSize(42, 46))
        self.menu_list.setIconSize(QSize(32, 32)) 
        
        # 아이템 생성
        self.item_modeler = QListWidgetItem("", self.menu_list)
        self.item_modeler.setToolTip("3D Modeler")
        self.item_modeler.setTextAlignment(Qt.AlignCenter)
        
        self.item_maze = QListWidgetItem("", self.menu_list)
        self.item_maze.setToolTip("Maze Game")
        self.item_maze.setTextAlignment(Qt.AlignCenter)

        self.item_settings = QListWidgetItem("", self.menu_list)
        self.item_settings.setToolTip("Settings")
        self.item_settings.setTextAlignment(Qt.AlignCenter)

        sidebar_layout.addWidget(self.menu_list)
        main_layout.addWidget(self.sidebar)
        
        # --- 2. 컨텐츠 영역 (Stacked Widget) ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # 사운드 매니저 초기화
        self.sound_manager = SoundManager(self)
        self.sound_manager.load_title_bgm("bgm_title_clean.mp3", "bgm_title_muffled.mp3")
        self.sound_manager.play_title_bgm()

        # 서브 애플리케이션 호출
        self.modeler = ModelerWindow()
        self.modeler.setWindowFlags(Qt.Widget)
        
        self.modeler.setWindowFlags(Qt.Widget)
        
        self.maze = MiroWindow(self.sound_manager)
        
        self.stack.addWidget(self.modeler)
        self.stack.addWidget(self.maze)

        # 설정 페이지 추가
        self.settings_page = SettingsPage()
        self.stack.addWidget(self.settings_page)

        # 연결
        self.menu_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.settings_page.gpuAccelerationChanged.connect(self._on_gpu_accel_changed)
        self.settings_page.shadowQualityChanged.connect(self._on_shadow_quality_changed)
        self.settings_page.volumeChanged.connect(self.sound_manager.set_master_volume)
        
        # 게임플레이 설정 연결 (퍼센트 -> 실제 값 변환)
        # 기본값: Speed 0.08, Sensitivity 0.15
        self.settings_page.moveSpeedChanged.connect(
            lambda v: self.maze.gl_widget.set_move_speed((v / 100.0) * 0.08)
        )
        self.settings_page.mouseSensitivityChanged.connect(
            lambda v: self.maze.gl_widget.set_mouse_sensitivity((v / 100.0) * 0.15)
        )

        # 초기 화면 설정 (0: Modeler, 1: Maze Game, 2: Settings)
        self.stack.setCurrentIndex(1)
        self.menu_list.setCurrentRow(1)

        # 초기 스타일 및 아이콘 적용
        self._update_styles()

        # 탭 전환 시 사운드 Muffled 효과 적용
        self.stack.currentChanged.connect(self._on_stack_changed)
        
        # 초기 상태에 따른 사운드 설정 (초기 인덱스 1: Maze -> Clean)
        self._on_stack_changed(1)

    def _on_stack_changed(self, index):
        """탭 변경 시 사운드 효과 제어"""
        # 1번 탭(Maze Game)일 때만 선명하게, 나머지는 먹먹하게
        if index == 1:
            self.sound_manager.set_muffled(False)
        else:
            self.sound_manager.set_muffled(True)

    def changeEvent(self, event):
        """
        위젯의 상태 변경 이벤트를 처리하여 시스템 테마 변경을 감지합니다.
        """
        # ApplicationPaletteChange 또는 PaletteChange 이벤트가 발생하면 스타일을 업데이트합니다.
        if event.type() == QEvent.ApplicationPaletteChange or event.type() == QEvent.PaletteChange:
            self._update_styles()
        
        super().changeEvent(event)

    def _update_styles(self):
        """
        현재 시스템 테마(라이트/다크)에 맞춰 UI 스타일과 아이콘을 업데이트합니다.
        """
        # 전역 애플리케이션 팔레트를 사용하여 시스템 테마 감지
        app = QApplication.instance()
        if app:
            palette = app.palette()
        else:
            palette = self.palette()
            
        bg_color = palette.color(QPalette.Window)
        # 밝기가 128 미만이면 다크 모드로 간주
        is_dark_mode = bg_color.lightness() < 128

        # 모드에 따른 동적 색상 설정
        if is_dark_mode:
            hover_color = "#4a4a4a"    # 다크 모드 Hover 색상
            selected_color = "#636363" # 다크 모드 Selected 색상
            border_color = "#424242"   # 다크 모드 경계선 색상
            icon_color = "white"       # 다크 모드 아이콘 (Normal)
            selected_icon_color = "white" # 다크 모드 아이콘 (Selected)
        else:
            hover_color = "#e0e0e0"    # 라이트 모드 Hover 색상
            selected_color = "#c7c7c7" # 라이트 모드 Selected 색상
            border_color = "#dcdcdc"   # 라이트 모드 경계선 색상
            icon_color = "#333333"     # 라이트 모드 아이콘 (Normal)
            selected_icon_color = "#333333" # 라이트 모드 아이콘 (Selected) - 진한 회색 유지
        
        # 사이드바 경계선 색상 업데이트
        self.sidebar.setStyleSheet(f"QWidget {{ border-right: 1px solid {border_color}; }}")

        # 메뉴 리스트 스타일시트 업데이트 (아이템 스타일 복구)
        self.menu_list.setStyleSheet(f"""
            QListWidget {{
                border: none;
                background-color: transparent;
                outline: none;
                margin: 0px;
                padding: 0px;
            }}
            QListWidget::item {{
                border-radius: 5px;
                margin-bottom: 5px;
                padding-top: 2px;
                padding-bottom: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {selected_color};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {hover_color};
            }}
        """)
        
        # 아이콘 업데이트
        self.item_modeler.setIcon(self._create_themed_icon("icon_modeler", icon_color, selected_icon_color))
        self.item_maze.setIcon(self._create_themed_icon("icon_maze", icon_color, selected_icon_color))
        self.item_settings.setIcon(self._create_themed_icon("icon_settings", icon_color, selected_icon_color))

    def _create_themed_icon(self, name, normal_color_code, selected_color_code):
        """
        테마 색상이 적용된 QIcon을 생성합니다.
        Normal 상태: normal_color_code
        Selected 상태: selected_color_code
        """
        # 1. 원본 Pixmap 로드
        svg_path = os.path.join("assets", f"{name}.svg")
        png_path = os.path.join("assets", f"{name}.png")
        
        if os.path.exists(svg_path):
            icon = QIcon(svg_path)
            pixmap = icon.pixmap(64, 64) # 고해상도
        elif os.path.exists(png_path):
            pixmap = QPixmap(png_path)
            pixmap.setDevicePixelRatio(2)
        else:
            # Fallback
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
        
        # 2. Normal 상태 Pixmap 생성 (Tinting)
        normal_pixmap = self._tint_pixmap(pixmap, QColor(normal_color_code))
        
        # 3. Selected 상태 Pixmap 생성 (Tinting)
        selected_pixmap = self._tint_pixmap(pixmap, QColor(selected_color_code))
        
        # 4. QIcon 생성 및 상태별 Pixmap 추가
        final_icon = QIcon()
        final_icon.addPixmap(normal_pixmap, QIcon.Normal, QIcon.Off)
        final_icon.addPixmap(normal_pixmap, QIcon.Normal, QIcon.On)
        final_icon.addPixmap(selected_pixmap, QIcon.Selected, QIcon.Off)
        final_icon.addPixmap(selected_pixmap, QIcon.Selected, QIcon.On)
        
        # Active 상태도 Selected와 동일하게 처리 (포커스 등)
        final_icon.addPixmap(selected_pixmap, QIcon.Active, QIcon.Off)
        final_icon.addPixmap(selected_pixmap, QIcon.Active, QIcon.On)
        
        return final_icon

    def _tint_pixmap(self, pixmap, color):
        """Pixmap에 색상을 덮어씌웁니다 (SourceIn)."""
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.transparent)
        tinted.setDevicePixelRatio(pixmap.devicePixelRatio()) # DPI 유지
        
        painter = QPainter(tinted)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        
        return tinted

    def _on_gpu_accel_changed(self, enabled):
        """GPU 가속 설정을 모델러와 미로 게임 모두에 적용"""
        # 모델러
        self.modeler.glWidget.set_gpu_acceleration(enabled)
        # 미로 게임
        self.maze.gl_widget.set_gpu_acceleration(enabled)

    def _on_shadow_quality_changed(self, quality):
        """그림자 품질 설정을 미로 게임에 적용"""
        self.maze.gl_widget.set_shadow_quality(quality)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainContainer()
    window.show()
    sys.exit(app.exec_())
