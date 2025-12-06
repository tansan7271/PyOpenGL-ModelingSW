# -*- coding: utf-8 -*-
"""
미로 게임 UI 모듈
"""

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QStackedWidget, QGroupBox, QSpinBox, QCheckBox, QComboBox, 
                             QSpacerItem, QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont
from miro_opengl import MiroOpenGLWidget

class MiroWindow(QMainWindow):
    """
    미로 찾기 게임의 메인 UI 위젯입니다.
    타이틀 화면과 게임 화면을 전환하며 관리합니다.
    """
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃 (스택 위젯 포함)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 툴바 생성 (메뉴바 대체)
        self._create_toolbar()
        
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # 1. 타이틀 화면 (Page 0)
        self.page_title = QWidget()
        self._setup_title_page()
        self.stack.addWidget(self.page_title)
        
        # 2. 게임 화면 (Page 1)
        self.page_game = QWidget()
        self._setup_game_page()
        self.stack.addWidget(self.page_game)
        
        # 초기 화면 설정
        self.stack.setCurrentIndex(0)

    def _create_toolbar(self):
        """툴바 설정 (뷰 모드 드롭다운, 미니맵 토글)"""
        from PyQt5.QtWidgets import QToolBar, QToolButton, QMenu, QAction, QActionGroup, QWidget, QLabel
        
        toolbar = QToolBar("Maze Toolbar")
        # toolbar.setMovable(True) # 기본값이 True이므로 명시적으로 설정하지 않아도 됨
        self.addToolBar(toolbar)
        
        # 0. 중단 및 타이틀 복귀 버튼
        action_abort = QAction("Abort and Return to Title", self)
        action_abort.triggered.connect(self._return_to_title)
        toolbar.addAction(action_abort)
        
        toolbar.addSeparator()
        
        # 1. 뷰 모드 (드롭다운)
        btn_view_mode = QToolButton()
        btn_view_mode.setText("View Mode")
        btn_view_mode.setPopupMode(QToolButton.InstantPopup) # 클릭 시 메뉴 즉시 표시
        # Windows에서 화살표 아이콘 공간 확보를 위한 스타일
        btn_view_mode.setStyleSheet("QToolButton { padding-right: 20px; } QToolButton::menu-indicator { width: 12px; }")
        
        view_menu = QMenu(btn_view_mode)
        view_group = QActionGroup(self)
        
        self.action_1st_person = QAction("1st Person View", self)
        self.action_1st_person.setCheckable(True)
        self.action_1st_person.setChecked(True) # 기본값
        view_menu.addAction(self.action_1st_person)
        view_group.addAction(self.action_1st_person)
        
        self.action_3rd_person = QAction("3rd Person View", self)
        self.action_3rd_person.setCheckable(True)
        view_menu.addAction(self.action_3rd_person)
        view_group.addAction(self.action_3rd_person)
        
        btn_view_mode.setMenu(view_menu)
        toolbar.addWidget(btn_view_mode)
        
        toolbar.addSeparator()
        
        # 2. 미니맵 (토글 액션)
        self.action_minimap = QAction("Show Minimap", self)
        self.action_minimap.setCheckable(True)
        self.action_minimap.setChecked(False) # 기본값
        toolbar.addAction(self.action_minimap)

    def _setup_title_page(self):
        """타이틀 화면 UI 구성"""
        from PyQt5.QtWidgets import QFrame
        
        layout = QVBoxLayout(self.page_title)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        
        # 사이드바 안내 라벨 (좌측 상단)
        hint_layout = QHBoxLayout()
        self.lbl_hint = QLabel("← Click here to use 3D Modeler")
        self.lbl_hint.setStyleSheet("color: gray; font-style: italic; font-size: 12px;")
        hint_layout.addWidget(self.lbl_hint)
        hint_layout.addStretch()
        layout.addLayout(hint_layout)
        
        # 1. 타이틀 이미지 (상단)
        self.lbl_title_image = QLabel()
        self.lbl_title_image.setAlignment(Qt.AlignCenter)
        
        # 이미지 로드 (assets/maze_title.png)
        image_path = os.path.join(os.path.dirname(__file__), 'assets', 'maze_title.png')
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # 이미지 크기 조정 (가로 800px, 비율 유지)
            scaled_pixmap = pixmap.scaled(800, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_title_image.setPixmap(scaled_pixmap)
        else:
            self.lbl_title_image.setText("Maze Game Title Image Not Found")
            self.lbl_title_image.setStyleSheet("font-size: 30px; color: white; font-weight: bold;")
            
        layout.addWidget(self.lbl_title_image)
        
        # 2. 메인 콘텐츠 영역 (좌우 분할)
        content_layout = QHBoxLayout()
        content_layout.setAlignment(Qt.AlignCenter)
        
        # --- [좌측] 스토리 모드 패널 ---
        group_story = QGroupBox("Story Mode")
        group_story.setFixedWidth(320) # Windows 폰트 크기 대응을 위해 너비 증가
        
        story_layout = QVBoxLayout(group_story)
        story_layout.setContentsMargins(20, 20, 20, 20)
        
        # 스토리 읽기
        self.btn_read_story = QPushButton("Read Story")
        self.btn_read_story.setMinimumHeight(40)
        self.btn_read_story.clicked.connect(lambda: self._start_game("Story Read"))
        story_layout.addWidget(self.btn_read_story)
        
        # 구분선
        line_story = QFrame()
        line_story.setFrameShape(QFrame.HLine)
        line_story.setFrameShadow(QFrame.Sunken)
        story_layout.addWidget(line_story)
        
        # 스테이지 버튼들
        self.btn_stage1 = QPushButton("Stage 1")
        self.btn_stage1.setMinimumHeight(40)
        self.btn_stage1.clicked.connect(lambda: self._start_game("Stage 1"))
        story_layout.addWidget(self.btn_stage1)
        
        self.btn_stage2 = QPushButton("Stage 2")
        self.btn_stage2.setMinimumHeight(40)
        self.btn_stage2.clicked.connect(lambda: self._start_game("Stage 2"))
        story_layout.addWidget(self.btn_stage2)
        
        self.btn_stage3 = QPushButton("Stage 3")
        self.btn_stage3.setMinimumHeight(40)
        self.btn_stage3.clicked.connect(lambda: self._start_game("Stage 3"))
        story_layout.addWidget(self.btn_stage3)
        
        story_layout.addStretch()
        content_layout.addWidget(group_story)
        
        # --- [우측] 커스텀 모드 패널 ---
        group_custom = QGroupBox("Custom Mode")
        group_custom.setFixedWidth(320) # Windows 폰트 크기 대응을 위해 너비 증가
        
        custom_layout = QVBoxLayout(group_custom)
        custom_layout.setSpacing(15)
        custom_layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. 시작 버튼 (최상단 이동)
        self.btn_start_custom = QPushButton("Start Game")
        self.btn_start_custom.setMinimumHeight(40) 
        self.btn_start_custom.clicked.connect(lambda: self._start_game("Custom"))
        custom_layout.addWidget(self.btn_start_custom)
        
        # 구분선
        line_custom = QFrame()
        line_custom.setFrameShape(QFrame.HLine)
        line_custom.setFrameShadow(QFrame.Sunken)
        custom_layout.addWidget(line_custom)
        
        # 2. 중첩된 설정 그룹
        
        # 미로 생성 설정 그룹
        group_maze_settings = QGroupBox("Generation")
        maze_settings_layout = QVBoxLayout(group_maze_settings)
        
        # 미로 크기
        size_layout = QHBoxLayout()
        lbl_size = QLabel("Size (W × H):")
        size_layout.addWidget(lbl_size)
        
        size_input_layout = QHBoxLayout()
        self.spin_width = QSpinBox(); self.spin_width.setRange(5, 50); self.spin_width.setValue(15)
        self.spin_height = QSpinBox(); self.spin_height.setRange(5, 50); self.spin_height.setValue(15)
        size_input_layout.addWidget(self.spin_width)
        size_input_layout.addWidget(QLabel("×")); 
        size_input_layout.addWidget(self.spin_height)
        size_layout.addLayout(size_input_layout)
        maze_settings_layout.addLayout(size_layout)
        
        custom_layout.addWidget(group_maze_settings)
        
        # 환경 설정 그룹
        group_env = QGroupBox("Environment")
        env_layout = QVBoxLayout(group_env)
        
        # 날씨
        env_layout.addWidget(QLabel("Weather:"))
        self.combo_weather = QComboBox()
        self.combo_weather.addItems(["Clear", "Rain", "Snow"])
        env_layout.addWidget(self.combo_weather)
        
        # 테마
        env_layout.addWidget(QLabel("Theme:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Inside 810-Gwan (One Hyung-Gwan)", "Between University Buildings", "The Path to the Main Gate"])
        env_layout.addWidget(self.combo_theme)
        
        custom_layout.addWidget(group_env)
        
        custom_layout.addStretch()
        content_layout.addWidget(group_custom)
        
        layout.addLayout(content_layout)
        layout.addStretch()
        
        # 안개 효과
        self.check_fog = QCheckBox("Enable Fog")
        self.check_fog.setChecked(True)
        env_layout.addWidget(self.check_fog)

        # 크레딧 (하단)
        lbl_credits = QLabel("컴퓨터그래픽스 02분반 ∙ 06조 ∙ 김도균(20225525), 오성진(20225534), 권민준(20231389)")
        lbl_credits.setAlignment(Qt.AlignCenter)
        lbl_credits.setStyleSheet("font-weight: bold; color: #666; font-size: 14px; margin-bottom: 20px;")
        layout.addWidget(lbl_credits)

    def _setup_game_page(self):
        """게임 화면 UI 구성"""
        layout = QVBoxLayout(self.page_game)
        
        # 상단 정보 바
        info_bar = QHBoxLayout()
        self.lbl_game_info = QLabel("Mode: None")
        self.lbl_game_info.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        
        btn_back = QPushButton("Back to Title")
        btn_back.setFixedSize(100, 30)
        btn_back.clicked.connect(self._return_to_title)
        
        info_bar.addWidget(self.lbl_game_info)
        info_bar.addStretch()
        info_bar.addWidget(btn_back)
        layout.addLayout(info_bar)
        
        # OpenGL 위젯
        self.gl_widget = MiroOpenGLWidget()
        layout.addWidget(self.gl_widget)

    def _toggle_custom_setup(self):
        """커스텀 설정 패널 표시/숨김 토글 (현재 사용 안 함)"""
        if hasattr(self, 'group_custom'):
            is_visible = self.group_custom.isVisible()
            self.group_custom.setVisible(not is_visible)

    def _start_game(self, mode):
        """게임 시작 처리"""
        print(f"Starting Game: {mode}")
        
        config = {}
        if mode == "Custom":
            config = {
                "width": self.spin_width.value(),
                "height": self.spin_height.value(),
                "fog": self.check_fog.isChecked(),
                "weather": self.combo_weather.currentText(),
                "theme": self.combo_theme.currentText()
            }
            print(f"Custom Config: {config}")
        
        # 게임 정보 업데이트
        self.lbl_game_info.setText(f"Current Mode: {mode}")
        
        # 화면 전환
        self.stack.setCurrentIndex(1)
        
        # TODO: OpenGL 위젯에 게임 모드 및 설정 전달
        # self.gl_widget.start_game(mode, config)

    def _return_to_title(self):
        """타이틀 화면으로 복귀"""
        self.stack.setCurrentIndex(0)

