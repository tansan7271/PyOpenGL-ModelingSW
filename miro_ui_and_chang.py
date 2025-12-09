# -*- coding: utf-8 -*-
"""
미로 게임 UI 모듈
"""

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QStackedWidget, QGroupBox, QSpinBox, QCheckBox, QComboBox, 
                             QSpacerItem, QSizePolicy, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QPixmap, QFont
from miro_opengl import MiroOpenGLWidget
from miro_story import MiroStoryWidget

class MiroWindow(QMainWindow):
    """
    미로 찾기 게임의 메인 UI 위젯입니다.
    타이틀 화면과 게임 화면을 전환하며 관리합니다.
    """
    def __init__(self, sound_manager=None):
        super().__init__()
        self.sound_manager = sound_manager
        
        # 모델 리스트 초기화
        # 구조: {'name': str, 'path': str, 'is_sample': bool, 'checked': bool}
        self.models_list = []      # (legacy name used internally) -> items_list alias
        self.items_list = []       # Main list
        self.items_spawn_enabled = True # 마스터 스위치
        self.spawn_count = 3       # 아이템 스폰 개수
        self._init_sample_items()
        
        # 스킬 활성화 상태 (BGM Ducking 용)
        self.active_skill_count = 0
        self.is_cheat_paused = False # 치트로 인한 타이머 정지 상태
        self.game_session_id = 0 # 게임 세션 ID (타이머 콜백 제어용)

        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self._update_timer)
        self.time_limit = 0
        self.current_time = 0
        self.is_custom_mode = False
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
        
        # 3. 스토리 모드 화면 (Page 2)
        self.story_widget = MiroStoryWidget()
        self.story_widget.finished.connect(self._return_to_title)
        self.stack.addWidget(self.story_widget)
        
        # 초기 화면 설정
        self.stack.setCurrentIndex(0)
        
        # 아이템 리스트 초기화 (재설정)
        self.items_list = []
        self._init_sample_items()

    def _init_sample_items(self):
        """샘플 아이템 리스트 초기화"""
        import glob
        
        base_path = os.path.join(os.path.dirname(__file__), 'datasets')
        # item_*.dat 파일 찾기
        sample_files = sorted(glob.glob(os.path.join(base_path, "item_*.dat")))
        
        for f in sample_files:
            name = os.path.basename(f)
            self.items_list.append({
                'name': name,
                'path': f,
                'is_sample': True,
                'checked': True # 기본값 활성화
            })


    def _create_toolbar(self):
        """툴바 설정 (뷰 모드 드롭다운, 미니맵 토글)"""
        from PyQt5.QtWidgets import QToolBar, QAction, QToolButton, QMenu
        
        toolbar = QToolBar("Maze Toolbar")
        # toolbar.setMovable(True) # 기본값이 True
        self.addToolBar(toolbar)
        
        # 0. 중단 및 타이틀 복귀 버튼
        action_abort = QAction("Return to Title", self)
        action_abort.triggered.connect(self._return_to_title)
        toolbar.addAction(action_abort)
        

        
        # 2. 치트 메뉴 (드롭다운)
        from PyQt5.QtWidgets import QToolButton, QMenu

        self.btn_cheats = QToolButton()
        self.btn_cheats.setText("Cheats ▾")
        self.btn_cheats.setPopupMode(QToolButton.InstantPopup)
        self.btn_cheats.setToolButtonStyle(Qt.ToolButtonTextOnly)

        self.menu_cheats = QMenu(self.btn_cheats)
        
        # 2.1 퍼즈 (Trigger) - 10초간 타이머 정지
        self.action_cheat_pause = QAction("Pause Timer [1]", self)
        self.action_cheat_pause.triggered.connect(lambda: self._on_cheat_pause_timer(10))
        self.menu_cheats.addAction(self.action_cheat_pause)

        # 2.2 미니맵 (Toggle)
        self.action_cheat_minimap = QAction("Show Minimap [2]", self)
        self.action_cheat_minimap.setCheckable(True)
        self.action_cheat_minimap.setChecked(False)
        self.action_cheat_minimap.toggled.connect(self._cheat_toggle_minimap)
        self.menu_cheats.addAction(self.action_cheat_minimap)

        # 2.3 고스트 모드 (Toggle) - 벽 뚫기
        self.action_cheat_ghost = QAction("Ghost Mode (No Clip) [3]", self)
        self.action_cheat_ghost.setCheckable(True)
        self.action_cheat_ghost.setChecked(False)
        self.action_cheat_ghost.toggled.connect(self._cheat_toggle_ghost)
        self.menu_cheats.addAction(self.action_cheat_ghost)

        # 2.4 투시 (Toggle) - 벽 투명화
        self.action_cheat_xray = QAction("X-Ray Vision [4]", self)
        self.action_cheat_xray.setCheckable(True)
        self.action_cheat_xray.setChecked(False)
        self.action_cheat_xray.toggled.connect(self._cheat_toggle_xray)
        self.menu_cheats.addAction(self.action_cheat_xray)

        # 2.5 이글 아이 (Toggle) - 시야 상승
        self.action_cheat_eagle = QAction("Eagle Eye View [5]", self)
        self.action_cheat_eagle.setCheckable(True)
        self.action_cheat_eagle.setChecked(False)
        self.action_cheat_eagle.toggled.connect(self._cheat_toggle_eagle)
        self.menu_cheats.addAction(self.action_cheat_eagle)

        self.menu_cheats.addSeparator()

        # 2.6 시간 조작 (Trigger) - 네이밍: "Time Boost" (스토리: +10s / 커스텀: -10s)
        self.action_cheat_time = QAction("Time Boost (+10s / -10s)", self)
        self.action_cheat_time.triggered.connect(self._cheat_time_boost)
        self.menu_cheats.addAction(self.action_cheat_time)

        self.menu_cheats.addSeparator()
        self.menu_cheats.addSection("Simulation (Trigger)")
        
        # 시뮬레이션 버튼들 (일회성 발동)
        sim_effects = [
            ("Simulate: Time Pause", "time_pause"),
            ("Simulate: Time Boost", "time_boost"),
            ("Simulate: Minimap", "minimap"),
            ("Simulate: Ghost Mode", "ghost"),
            ("Simulate: X-Ray", "xray"),
            ("Simulate: Eagle Eye", "eagle")
        ]
        
        for name, effect in sim_effects:
            action = QAction(name, self)
            # lambda의 closure 문제 방지를 위해 default argument 사용
            action.triggered.connect(lambda checked, eff=effect: self._activate_specific_skill(eff))
            self.menu_cheats.addAction(action)

        self.btn_cheats.setMenu(self.menu_cheats)
        toolbar.addWidget(self.btn_cheats)

        # 3. 아이템 메뉴 (드롭다운)
        self.btn_items = QToolButton()
        self.btn_items.setText("Items ▾")
        self.btn_items.setPopupMode(QToolButton.InstantPopup)
        self.btn_items.setToolButtonStyle(Qt.ToolButtonTextOnly)
        
        self.menu_items = QMenu(self.btn_items)
        self.btn_items.setMenu(self.menu_items)
        toolbar.addWidget(self.btn_items)
        
        # 메뉴 초기 구성
        self._refresh_items_menu()

    def _setup_title_page(self):
        """타이틀 화면 UI 구성"""
        from PyQt5.QtWidgets import QFrame, QDoubleSpinBox
        
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
        content_layout.setSpacing(40) # 패널 간 간격 추가
        content_layout.setContentsMargins(50, 0, 50, 0) # 좌우 여백 추가
        
        # --- [좌측] 스토리 모드 패널 ---
        group_story = QGroupBox("Story Mode")
        group_story.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # 동적 너비
        group_story.setMinimumWidth(300) # 최소 너비 설정
        
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
        group_custom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # 동적 너비
        group_custom.setMinimumWidth(300) # 최소 너비 설정
        
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
        
        # 미로 상세 설정 그룹 (Environment 대체)
        group_maze_details = QGroupBox("Details")
        details_layout = QVBoxLayout(group_maze_details)
        
        # 벽 두께 설정
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Wall Thickness:"))
        self.spin_thickness = QDoubleSpinBox()
        self.spin_thickness.setRange(0.1, 1.0)
        self.spin_thickness.setSingleStep(0.1)
        self.spin_thickness.setValue(0.1)
        self.spin_thickness.valueChanged.connect(self._on_thickness_changed)
        thickness_layout.addWidget(self.spin_thickness)
        details_layout.addLayout(thickness_layout)

        # 벽 높이 설정 (추가)
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Wall Height:"))
        self.spin_wall_height = QDoubleSpinBox()
        self.spin_wall_height.setRange(0.5, 5.0) # 0.5 ~ 5.0 높이
        self.spin_wall_height.setSingleStep(0.5)
        self.spin_wall_height.setValue(2.0)
        height_layout.addWidget(self.spin_wall_height)
        details_layout.addLayout(height_layout)
        
        # 높낮이 활성화 (두께가 1.0일 때만 가능)
        self.check_height_variation = QCheckBox("Enable Height Variation (Floor)")
        self.check_height_variation.setChecked(False)
        self.check_height_variation.setToolTip("Only available when Wall Thickness is 1.0 (Creates uneven terrain)")
        details_layout.addWidget(self.check_height_variation)

        custom_layout.addWidget(group_maze_details)
        
        custom_layout.addStretch()
        content_layout.addWidget(group_custom)
        
        layout.addLayout(content_layout)
        layout.addStretch()
        
        # 환경 설정 (가로 배치: 날씨 | 테마 | 안개)
        env_layout = QHBoxLayout()
        
        # 1. 날씨
        env_layout.addWidget(QLabel("Weather:"))
        self.combo_weather = QComboBox()
        self.combo_weather.addItems(["Clear", "Rain", "Snow"])
        self.combo_weather.currentTextChanged.connect(self._on_weather_changed)
        env_layout.addWidget(self.combo_weather)
        
        # 2. 테마
        env_layout.addWidget(QLabel("Theme:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["810-Gwan", "Inside Campus", "Path to the Main Gate", "Developer"]) # Developer at the end
        self.combo_theme.setCurrentText("810-Gwan")
        self.combo_theme.currentTextChanged.connect(self._on_theme_changed)
        env_layout.addWidget(self.combo_theme)

        # 3. 안개
        self.check_fog = QCheckBox("Fog")
        self.check_fog.setChecked(True)
        self.check_fog.stateChanged.connect(self._on_fog_changed)
        env_layout.addWidget(self.check_fog)

        env_layout.addStretch() # 우측 여백
        custom_layout.addLayout(env_layout)

        # 초기 상태 업데이트
        self._on_thickness_changed(self.spin_thickness.value())
        self._on_fog_changed(self.check_fog.isChecked())
        # 날씨 초기화는 콤보박스 기본값(Clear)으로 자동 호출되지 않을 수 있으므로 명시적 호출
        self._on_weather_changed(self.combo_weather.currentText())

        # 크레딧 (하단)
        lbl_credits = QLabel("컴퓨터그래픽스 02분반 ∙ 06조 ∙ 김도균(20225525), 오성진(20225534), 권민준(20231389)")
        lbl_credits.setAlignment(Qt.AlignCenter)
        lbl_credits.setStyleSheet("font-weight: bold; color: #666; font-size: 14px; margin-bottom: 20px;")
        layout.addWidget(lbl_credits)

    def _on_weather_changed(self, text):
        """날씨 변경 핸들러"""
        if hasattr(self, 'gl_widget'):
            self.gl_widget.set_weather(text)

    def _on_fog_changed(self, state):
        """안개 설정 변경"""
        # state는 int(0/2) 또는 bool일 수 있음
        is_checked = (state == Qt.Checked) if isinstance(state, int) else state
        if hasattr(self, 'gl_widget'):
            self.gl_widget.set_fog(is_checked)

    def _on_theme_changed(self, theme_text):
        """테마 변경 핸들러"""
        self.gl_widget.set_theme(theme_text)

    def _on_thickness_changed(self, value):
        """벽 두께 변경 시 높낮이 옵션 활성화 여부 제어"""
        # 부동소수점 비교 시 epsilon 사용 또는 근사값 비교
        if abs(value - 1.0) < 0.001:
            self.check_height_variation.setEnabled(True)
            self.check_height_variation.setText("Height Variation (Available)")
        else:
            self.check_height_variation.setEnabled(False)
            self.check_height_variation.setChecked(False)
            self.check_height_variation.setText("Height Variation (Available when Wall Thickness is set to 1.0)")

    def _setup_game_page(self):
        """게임 화면 UI 구성"""
        from PyQt5.QtGui import QFont
        layout = QVBoxLayout(self.page_game)

        # 상단 정보 바
        info_bar = QHBoxLayout()
        self.lbl_game_info = QLabel("Mode: None")
        font = QFont()
        font.setPointSize(10)
        self.lbl_game_info.setFont(font)
        self.lbl_game_info.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # GAHO 스코어 라벨 (Bold)
        self.lbl_gaho = QLabel("Seonbae's GAHO: 0")
        font_gaho = QFont()
        font_gaho.setBold(True)
        font_gaho.setPointSize(12)
        self.lbl_gaho.setFont(font_gaho)
        self.lbl_gaho.setStyleSheet("margin-left: 10px;")
        
        # GAHO 메시지 라벨 (효과 발동 시 표시)
        self.lbl_gaho_message = QLabel("")
        self.lbl_gaho_message.setStyleSheet("color: red; font-weight: bold; margin-left: 10px;")

        # 타이머 라벨 (우측 상단)
        self.lbl_timer = QLabel("00:00")
        # 기본 폰트 사용, 정렬만 설정
        self.lbl_timer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.lbl_timer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        info_bar.addWidget(self.lbl_game_info)
        info_bar.addWidget(self.lbl_gaho) # GAHO 라벨 추가
        info_bar.addWidget(self.lbl_gaho_message) # 메시지 라벨 추가
        info_bar.addStretch()
        info_bar.addWidget(self.lbl_timer)
        
        layout.addLayout(info_bar)

        # 진행률 바 (시간 제한 시각화)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False) # 텍스트 미표시 (타이머가 있으므로)
        # 기본 스타일 유지 (OS Native Look)
        layout.addWidget(self.progress_bar)

        # OpenGL 위젯
        self.gl_widget = MiroOpenGLWidget()
        self.gl_widget.game_won.connect(self._on_game_won)
        self.gl_widget.gameStarted.connect(lambda: self._update_ui_state(True)) # 게임 시작 시 UI 갱신 연결
        self.gl_widget.gamePaused.connect(self._on_game_paused)
        self.gl_widget.gameResumed.connect(self._on_game_resumed)
        # 치트 시그널 연결
        self.gl_widget.cheatPauseTimer.connect(self._on_cheat_pause_timer)
        self.gl_widget.cheatStateChanged.connect(self._on_cheat_state_changed)
        
        # GAHO 시스템 연결
        self.gl_widget.itemCollected.connect(self._on_item_collected)
        self.gl_widget.skillActivated.connect(self._on_skill_activated)
        
        layout.addWidget(self.gl_widget, 1) # Stretch Factor 1 추가

    def _toggle_custom_setup(self):
        """커스텀 설정 패널 표시/숨김 토글 (현재 사용 안 함)"""
        if hasattr(self, 'group_custom'):
            is_visible = self.group_custom.isVisible()
            self.group_custom.setVisible(not is_visible)

    def _start_game(self, mode):
        """게임 시작 처리"""
        print(f"Starting Game: {mode}")

        if mode == "Story Read":
            # 스토리 모드 시작
            self.story_widget.reset_story()
            self.stack.setCurrentWidget(self.story_widget)
            return

        if self.sound_manager:
            self.sound_manager.play_stage_bgm(mode)
            
        self.game_session_id += 1 # 새 세션 시작

        # 아이템 스폰 설정 적용
        active_models = []
        if self.items_spawn_enabled:
            for item in self.items_list:
                if item['checked']:
                    active_models.append(item['path'])
        
        # 선택된 아이템이 없으면 빈 리스트 전달 -> 스폰되지 않음
        self.gl_widget.set_active_item_models(active_models)
        self.gl_widget.set_spawn_count(self.spawn_count) # 설정된 개수 전달

        # Stage별 미로 파일 경로 설정
        maze_file = None
        if mode == "Stage 1":
            self.combo_theme.setCurrentText("810-Gwan")         # Theme: 810관
            self.gl_widget.set_fog(False)                       # Fog: OFF
            self.gl_widget.set_weather("Clear")                 # Weather: Clear
            maze_file = os.path.join(os.path.dirname(__file__), 'datasets', 'maze_01.dat')
            self._start_timer(mode, 60)
            
        elif mode == "Stage 2":
            self.combo_theme.setCurrentText("Inside Campus")    # Theme: 교정 내부
            self.gl_widget.set_fog(True)                        # Fog: ON (분위기 조성)
            self.gl_widget.set_weather("Rain")                  # Weather: Rain
            maze_file = os.path.join(os.path.dirname(__file__), 'datasets', 'maze_02.dat')
            self._start_timer(mode, 90)
            
        elif mode == "Stage 3":
            self.combo_theme.setCurrentText("Path to the Main Gate") # Theme: 정문
            self.gl_widget.set_fog(False)                            # Fog: OFF
            self.gl_widget.set_weather("Snow")                       # Weather: Snow
            maze_file = os.path.join(os.path.dirname(__file__), 'datasets', 'maze_03.dat')
            self._start_timer(mode, 120)
        elif mode == "Custom":
            # 커스텀 모드 설정값 적용
            self.gl_widget.set_fog(self.check_fog.isChecked())
            self.gl_widget.set_weather(self.combo_weather.currentText())

            # 커스텀 모드: 동적으로 미로 생성
            try:
                import maze_generator

                width = self.spin_width.value()
                height = self.spin_height.value()
                wall_thickness = self.spin_thickness.value()
                wall_height = self.spin_wall_height.value()

                # 높이 변화 설정 (두께가 1.0일 때만 유효)
                enable_height_var = (self.check_height_variation.isChecked() and
                                     abs(wall_thickness - 1.0) < 0.001)

                # 미로 생성
                print(f"Generating Custom Maze ({width}x{height}), Height Variation: {enable_height_var}...")
                maze = maze_generator.Maze(width, height, enable_height_variation=enable_height_var)
                maze.generate()
                
                # 저장 경로 설정
                if not os.path.exists('datasets'):
                    os.makedirs('datasets')
                
                custom_maze_file = os.path.join(os.path.dirname(__file__), 'datasets', 'custom_maze.dat')
                
                # .dat 파일로 내보내기
                maze.export_to_dat(custom_maze_file, wall_thickness=wall_thickness, wall_height=wall_height)
                
                maze_file = custom_maze_file
                self._start_timer(mode) # 커스텀 모드 타이머(스톱워치) 시작
                
            except Exception as e:
                QMessageBox.critical(self, "Generation Error", f"Failed to generate maze: {e}")
                return

        # 미로 파일 로드 및 게임 시작
        if maze_file and os.path.exists(maze_file):
            self.gl_widget.load_maze(maze_file)

            # 게임 정보 업데이트
            self.lbl_game_info.setText(f"Current Mode: {mode} | WASD: Move | Mouse: Look | Left Shift: use GAHO | ESC: Quit")
            
            # 커스텀 모드인 경우 추가 정보 표시
            if mode == "Custom":
                 self.lbl_game_info.setText(f"Mode: Custom ({self.spin_width.value()}x{self.spin_height.value()}) | WASD: Move | Mouse: Look")

            # 화면 전환
            self.stack.setCurrentIndex(1)

            # 게임 시작
            self.gl_widget.start_game()
        else:
            QMessageBox.warning(self, "Error", f"Maze file not found: {maze_file}")

    def _start_timer(self, mode, limit_seconds=0):
        """타이머 시작"""
        self.game_mode = mode
        self.lbl_timer.setStyleSheet("") # 스타일 초기화
        
        if mode == "Custom":
            self.is_custom_mode = True
            self.current_time = 0
            self.time_limit = 0
            self.progress_bar.setRange(0, 0) # Indeterminate mode (busy)
        else:
            self.is_custom_mode = False
            self.time_limit = limit_seconds
            self.current_time = limit_seconds
            self.progress_bar.setRange(0, limit_seconds)
            self.progress_bar.setValue(limit_seconds)
        
        self.game_timer.start(1000) # 1초마다 업데이트
        self._update_timer_display()

    def _update_timer(self):
        """타이머 업데이트 (1초마다 호출)"""
        if self.is_custom_mode:
            # 카운트 업 (스톱워치)
            self.current_time += 1
        else:
            # 카운트 다운 (타이머)
            self.current_time -= 1
            self.progress_bar.setValue(self.current_time)
            
            # 색상 변경 (긴박감 조성) - 텍스트 색상만 변경하여 OS 기본 UI 유지
            if self.current_time <= 10:
                self.lbl_timer.setStyleSheet("color: red; font-weight: bold;")
            elif self.current_time <= 30:
                self.lbl_timer.setStyleSheet("color: #FF5722; font-weight: bold;") # Deep Orange
            else:
                self.lbl_timer.setStyleSheet("")
            
            if self.current_time <= 0:
                self._on_game_over()
                return

        self._update_timer_display()

    def _update_timer_display(self):
        """타이머 라벨 업데이트"""
        mins, secs = divmod(self.current_time, 60)
        self.lbl_timer.setText(f"{mins:02d}:{secs:02d}")

    def _reset_skill_state(self):
        """게임 종료/타이틀 복귀 시 스킬/사운드 상태 초기화"""
        # 1. 사운드 초기화
        if self.sound_manager:
            self.sound_manager.stop_sfx_pool() # 효과음 즉시 중지
            self.sound_manager.set_ducking(1.0) # 볼륨 복구

        # 2. 스킬 상태 변수 초기화
        self.active_skill_count = 0
        self.is_cheat_paused = False

        # 3. GLCheats 초기화 (타이머 콜백이 뒤늦게 실행되도 영향 없도록)
        if hasattr(self, 'gl_widget'):
            self.gl_widget.cheat_minimap = False
            self.gl_widget.cheat_noclip = False
            self.gl_widget.cheat_xray = False
            # 이글아이는 메서드로
            self.gl_widget.set_eagle_eye_mode(False)
            
        # 4. UI 메시지 초기화
        if hasattr(self, 'lbl_gaho_message'):
            self.lbl_gaho_message.setText("")

    def _on_game_over(self):
        """게임 오버 (시간 초과) 처리"""
        self.game_timer.stop()
        self.gl_widget.stop_game()
        
        # 스킬 상태 초기화
        self._reset_skill_state()
        
        if self.sound_manager:
            self.sound_manager.stop_stage_bgm() # BGM 중지
            self.sound_manager.play_sfx("gameover")
            
        QMessageBox.critical(self, "Game Over", "Time's up! You failed to escape.")
        self._return_to_title()
 
    def _on_game_won(self):
        """게임 클리어 처리"""
        self.game_timer.stop()

        # 스킬 상태 초기화
        self._reset_skill_state()

        if self.sound_manager:
            self.sound_manager.stop_stage_bgm() # BGM 중지
            self.sound_manager.play_sfx("clear")
 
        QMessageBox.information(self, "Congratulations!", f"You escaped!\nTime: {self.lbl_timer.text()}")
        self._return_to_title()

    def _on_game_paused(self):
        """게임 일시정지 시 UI 타이머도 정지"""
        self.game_timer.stop()

    def _on_game_resumed(self):
        """게임 재개 시 UI 타이머도 재시작 (단, 치트 퍼즈 중이면 시작 안 함)"""
        if not self.is_cheat_paused:
            self.game_timer.start(1000)

    def _return_to_title(self):
        """타이틀 화면으로 복귀"""
        # 게임 중이라면 중지
        if self.gl_widget.game_active:
            self.gl_widget.stop_game()
            
        # 스킬/사운드 상태 초기화
        self._reset_skill_state()
            
        # 게임 타이머 중지
        self.game_timer.stop()
        
        # 타이틀 BGM으로 복귀 (재생 중지 후 처음부터 재생)
        if self.sound_manager:
            self.sound_manager.play_title_bgm() 
            
        self.stack.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)
        self._update_ui_state(False) # 아이템 메뉴 활성화

    # --- Cheats Logic ---
    def _cheat_time_boost(self):
        """치트: 시간 추가/감소 (스토리: +10s / 커스텀: -10s)"""
        # 게임이 활성화 상태라면 타이머가 퍼즈 상태여도 동작하도록 수정
        if not self.gl_widget.game_active:
            return
            
        if self.is_custom_mode:
            # 커스텀 모드: 시간 감소
            self.current_time = max(0, self.current_time - 10)
        else:
            # 스토리 모드: 시간 추가
            self.current_time = min(self.time_limit, self.current_time + 10)
        self._update_timer_display()

    def _on_cheat_pause_timer(self, seconds):
        """치트: 타이머 일시정지 (숫자키 1)"""
        if not self.game_timer.isActive():
            return
        self.game_timer.stop()
        self.is_cheat_paused = True
        # seconds초 후 자동 재개
        QTimer.singleShot(seconds * 1000, self._resume_timer_after_pause)

    def _resume_timer_after_pause(self):
        """퍼즈 종료 후 타이머 재개"""
        self.is_cheat_paused = False
        # 게임이 일시정지(ESC메뉴) 상태가 아니어야 타이머 재개
        if self.stack.currentIndex() == 1 and \
           hasattr(self, 'gl_widget') and \
           self.gl_widget.game_active and \
           not self.gl_widget.game_paused:
            self.game_timer.start(1000)

    def _on_cheat_state_changed(self, cheat_name, enabled):
        """OpenGL 위젯에서 치트 상태 변경 시 UI 동기화"""
        if cheat_name == 'minimap':
            self.action_cheat_minimap.setChecked(enabled)
        elif cheat_name == 'noclip':
            self.action_cheat_ghost.setChecked(enabled)
        elif cheat_name == 'xray':
            self.action_cheat_xray.setChecked(enabled)
        elif cheat_name == 'eagle':
            self.action_cheat_eagle.setChecked(enabled)

    def _cheat_toggle_minimap(self, enabled):
        """치트: 미니맵 토글 (UI 메뉴에서 호출)"""
        if hasattr(self, 'gl_widget'):
            self.gl_widget.cheat_minimap = enabled

    def _cheat_toggle_ghost(self, enabled):
        """치트: 고스트 모드 토글 (UI 메뉴에서 호출)"""
        if hasattr(self, 'gl_widget'):
            self.gl_widget.cheat_noclip = enabled
            # 노클립 해제 시 안전 위치로 이동
            if not enabled:
                self.gl_widget._teleport_to_safe_position()

    def _cheat_toggle_xray(self, enabled):
        """치트: 투시 모드 토글 (UI 메뉴에서 호출)"""
        if hasattr(self, 'gl_widget'):
            self.gl_widget.cheat_xray = enabled

    def _cheat_toggle_eagle(self, enabled):
        """치트: 이글 아이 모드 토글 (UI 메뉴에서 호출)"""
        if hasattr(self, 'gl_widget'):
            # 스마트 안개 로직이 포함된 메서드 호출
            self.gl_widget.set_eagle_eye_mode(enabled)

    # --- Items UI Logic ---
    def _refresh_items_menu(self):
        """아이템 메뉴 동적 재구성"""
        from PyQt5.QtWidgets import QAction
        self.menu_items.clear()
        
        # 1. 마스터 스위치 (Spawn Items)
        action_spawn = QAction("Spawn Items", self)
        action_spawn.setCheckable(True)
        action_spawn.setChecked(self.items_spawn_enabled)
        action_spawn.triggered.connect(self._on_spawn_items_toggled)
        self.menu_items.addAction(action_spawn)

        # 1.5. 스폰 개수 조절 (QSpinBox)
        from PyQt5.QtWidgets import QWidgetAction, QHBoxLayout, QLabel, QSpinBox, QWidget
        
        # 메뉴에 위젯을 넣기 위한 컨테이너 액션
        count_action = QWidgetAction(self.menu_items)
        count_widget = QWidget()
        layout = QHBoxLayout(count_widget)
        layout.setContentsMargins(20, 2, 20, 2) # 여백 조정
        
        lbl_count = QLabel("Count:")
        spin_count = QSpinBox()
        spin_count.setRange(1, 10)
        spin_count.setValue(self.spawn_count)
        spin_count.setFixedWidth(60)
        # 중요: 메뉴가 닫히지 않도록 하려면 focus 정책 등 고려 필요하나, 값 변경은 즉시 반영
        
        # 값 변경 시 self.spawn_count 업데이트
        spin_count.valueChanged.connect(self._on_spawn_count_changed)
        
        # 마스터 스위치와 연동하여 활성/비활성
        spin_count.setEnabled(self.items_spawn_enabled)
        lbl_count.setEnabled(self.items_spawn_enabled)
        self.spin_spawn_count = spin_count # 참조 저장 (활성화 제어용)
        self.lbl_spawn_count = lbl_count   # 참조 저장

        layout.addWidget(lbl_count)
        layout.addWidget(spin_count)
        count_action.setDefaultWidget(count_widget)
        self.menu_items.addAction(count_action)
        
        self.menu_items.addSeparator()
        
        # 2. 아이템 리스트
        # 샘플 아이템과 커스텀 아이템 구분
        has_added_separator = False
        
        for idx, item in enumerate(self.items_list):
            # 커스텀 아이템 시작 시 구분선 추가 (한 번만)
            if not item['is_sample'] and not has_added_separator:
                self.menu_items.addSeparator()
                has_added_separator = True
            
            # 체크박스 액션
            action = QAction(item['name'], self)
            action.setCheckable(True)
            action.setChecked(item['checked'])
            # 마스터 스위치 여부에 따라 활성/비활성 제어
            action.setEnabled(self.items_spawn_enabled)
            
            # 클로저 문제 해결을 위해 기본값 인자 사용
            action.toggled.connect(lambda checked, i=idx: self._on_item_checked(i, checked))
            self.menu_items.addAction(action)
            
            # 커스텀 아이템인 경우 삭제 버튼 추가
            if not item['is_sample']:
                del_action = QAction(f"    ❌ Delete '{item['name']}'", self)
                del_action.setEnabled(self.items_spawn_enabled)
                del_action.triggered.connect(lambda _, i=idx: self._on_remove_item(i))
                self.menu_items.addAction(del_action)

        self.menu_items.addSeparator()

        # 3. 파일 추가
        action_add = QAction("➕ Add File...", self)
        # Spawn이 꺼진 상태에서 추가하는게 의미가 없으므로 비활성화가 자연스러움.
        action_add.setEnabled(self.items_spawn_enabled)
        action_add.triggered.connect(self._on_add_item)
        self.menu_items.addAction(action_add)

    def _on_spawn_items_toggled(self, checked):
        """아이템 스폰 마스터 스위치 토글"""
        self.items_spawn_enabled = checked
        if hasattr(self, 'spin_spawn_count'):
            self.spin_spawn_count.setEnabled(checked)
        if hasattr(self, 'lbl_spawn_count'):
            self.lbl_spawn_count.setEnabled(checked)
        self._refresh_items_menu()
        
    def _on_spawn_count_changed(self, value):
        """아이템 스폰 개수 변경"""
        self.spawn_count = value
        # 즉시 반영은 어렵지만(게임 리셋 필요), 변수에는 저장됨

    def _activate_skill_bgm(self):
        """스킬 발동 시 BGM 줄이기"""
        if self.active_skill_count == 0 and self.sound_manager:
            self.sound_manager.set_ducking(0.7)
        self.active_skill_count += 1
        
    def _deactivate_skill_bgm(self):
        """스킬 종료 시 BGM 복구"""
        self.active_skill_count = max(0, self.active_skill_count - 1)
        if self.active_skill_count == 0 and self.sound_manager:
            self.sound_manager.set_ducking(1.0)

    # --- Seonbae's GAHO Logic ---
    def _on_item_collected(self):
        """아이템 획득 시 처리"""
        # UI 업데이트
        score = self.gl_widget.gaho_score
        self.lbl_gaho.setText(f"Seonbae's GAHO: {score}")
        
        # 사운드 재생
        if self.sound_manager:
            self.sound_manager.play_sfx("item_get")

    def _on_skill_activated(self):
        """GAHO 스킬 발동 시 처리"""
        # UI 업데이트
        score = self.gl_widget.gaho_score
        self.lbl_gaho.setText(f"Seonbae's GAHO: {score}")
        
        # 사운드 재생
        if self.sound_manager:
            self.sound_manager.play_sfx("skill_activate")
            
        # 랜덤 효과 발동
        import random
        effect = random.choice(["time_pause", "time_boost", "minimap", "ghost", "xray", "eagle"])
        self._activate_specific_skill(effect)

    def _activate_specific_skill(self, effect):
        """특정 스킬 효과 강제 발동 (시뮬레이션용)"""
        sid = self.game_session_id
        
        if effect == "time_pause":
            # 10초 정지
            self._on_cheat_pause_timer(10)
            self._play_skill_sound("time_pause_start")
            self._activate_skill_bgm()
            QTimer.singleShot(10000, lambda: self._end_time_pause_skill(sid))
            
            self._show_temp_message("Time Paused (10s)!")
            
        elif effect == "time_boost":
            # 시간 추가/경감
            self._cheat_time_boost()
            self._play_skill_sound("time_boost")
            msg = "-10s Record!" if self.is_custom_mode else "+10s Bonus!"
            self._show_temp_message(msg)
            
        elif effect == "minimap":
            # 10초 미니맵
            self.gl_widget.cheat_minimap = True
            self._play_skill_sound("minimap_start")
            self._activate_skill_bgm()
            QTimer.singleShot(10000, lambda: self._disable_minimap_safe(sid))
            self._show_temp_message("Minimap Revealed (10s)!")
            
        elif effect == "ghost":
            # 3초 고스트
            self.gl_widget.cheat_noclip = True
            self._play_skill_sound("ghost_start")
            self._activate_skill_bgm()
            QTimer.singleShot(3000, lambda: self._disable_ghost_safe(sid))
            self._show_temp_message("Ghost Mode (3s)!")
            
        elif effect == "xray":
            # 5초 엑스레이
            self.gl_widget.cheat_xray = True
            self.gl_widget.cheatStateChanged.emit('xray', True) # UI 동기화
            self._play_skill_sound("xray_start")
            self._activate_skill_bgm()
            QTimer.singleShot(5000, lambda: self._disable_xray_safe(sid))
            self._show_temp_message("X-Ray Vision (5s)!")

        elif effect == "eagle":
            # 10초 이글아이
            self.gl_widget.set_eagle_eye_mode(True)
            self._play_skill_sound("eagle_start")
            self._activate_skill_bgm()
            QTimer.singleShot(10000, lambda: self._disable_eagle_safe(sid))
            self._show_temp_message("Eagle Eye (10s)!")

    def _play_skill_sound(self, name):
        """스킬 사운드 재생 (게임 중일 때만)"""
        # 게임이 종료된 상태에서 타이머 콜백으로 종료음이 재생되는 것 방지
        if not self.gl_widget.game_active:
            return
            
        if self.sound_manager:
            self.sound_manager.play_sfx(name)
            
    def _end_time_pause_skill(self, sid):
        if sid != self.game_session_id: return
        self._play_skill_sound("time_pause_end")
        self._deactivate_skill_bgm()

    def _disable_minimap_safe(self, sid):
        if sid != self.game_session_id: return
        self.gl_widget.cheat_minimap = False
        self._play_skill_sound("minimap_end")
        self._deactivate_skill_bgm()
        
    def _disable_eagle_safe(self, sid):
        if sid != self.game_session_id: return
        self.gl_widget.set_eagle_eye_mode(False)
        self._play_skill_sound("eagle_end")
        self._deactivate_skill_bgm()

    def _disable_ghost_safe(self, sid):
        if sid != self.game_session_id: return
        self.gl_widget.cheat_noclip = False
        self.gl_widget._teleport_to_safe_position()
        self._play_skill_sound("ghost_end")
        self._deactivate_skill_bgm()
        
    def _disable_xray_safe(self, sid):
        if sid != self.game_session_id: return
        self.gl_widget.cheat_xray = False
        self.gl_widget.cheatStateChanged.emit('xray', False)
        self._play_skill_sound("xray_end")
        self._deactivate_skill_bgm()

    def _show_temp_message(self, msg):
        """GAHO 메시지 전용 라벨에 표시"""
        self.lbl_gaho_message.setText(msg)
        QTimer.singleShot(3000, lambda: self.lbl_gaho_message.setText(""))

    def _restore_info_text(self, text):
        pass # 더 이상 사용하지 않음 (메시지 라벨 분리됨)

    def _on_item_checked(self, index, checked):
        """개별 아이템 토글"""
        if 0 <= index < len(self.items_list):
            self.items_list[index]['checked'] = checked
        # UI 업데이트 불필요 (QAction이 스스로 상태 변경)

    def _on_add_item(self):
        """아이템 파일 추가"""
        from PyQt5.QtWidgets import QFileDialog
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Item File", "", "Data Files (*.dat);;All Files (*)", options=options)
        
        if file_path:
            name = os.path.basename(file_path)
            # 중복 체크
            if any(item['path'] == file_path for item in self.items_list):
                 return

            self.items_list.append({
                'name': name,
                'path': file_path,
                'is_sample': False,
                'checked': True
            })
            self._refresh_items_menu()

    def _on_remove_item(self, index):
        """아이템 파일 제거 (리스트에서만)"""
        if 0 <= index < len(self.items_list):
            del self.items_list[index]
            self._refresh_items_menu()
            
    def _update_ui_state(self, game_active):
        """게임 상태에 따라 UI 활성/비활성 제어"""
        # 게임 중이면 아이템 메뉴 비활성화
        ui_enabled = not game_active
        
        if hasattr(self, 'btn_items'):
            self.btn_items.setEnabled(ui_enabled)
