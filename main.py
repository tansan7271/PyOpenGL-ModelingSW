import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPalette
# QtSvg 모듈은 .svg 파일을 아이콘으로 사용하기 위해 필요합니다.
from PyQt5.QtSvg import QSvgRenderer

# Import Sub-Applications
from modeler_ui_and_chang import MainWindow as ModelerWindow
from miro_ui_and_chang import MiroWindow

class MainContainer(QMainWindow):
    """
    메인 컨테이너 윈도우
    좌측 사이드바를 통해 모델러와 미로 게임을 전환합니다.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyOpenGL Project: Modeler & Maze")
        self.resize(1280, 800)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout (Horizontal: Sidebar | Content)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- 1. Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(52)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(5, 25, 5, 5)
        sidebar_layout.setSpacing(0)

        # Sidebar Menu Items
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
        
        sidebar_layout.addWidget(self.menu_list)
        main_layout.addWidget(self.sidebar)
        
        # --- 2. Content Area (Stacked Widget) ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # Initialize Sub-Apps
        self.modeler = ModelerWindow()
        self.modeler.setWindowFlags(Qt.Widget)
        
        self.maze = MiroWindow()
        
        self.stack.addWidget(self.modeler)
        self.stack.addWidget(self.maze)
        
        # Connect Signals
        self.menu_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        # 초기 화면 설정 (0: Modeler, 1: Maze Game)
        self.stack.setCurrentIndex(1)
        self.menu_list.setCurrentRow(1)

        # 초기 스타일 및 아이콘 적용
        self._update_styles()

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainContainer()
    window.show()
    sys.exit(app.exec_())
