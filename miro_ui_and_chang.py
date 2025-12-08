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


    def _create_toolbar(self):
        """툴바 설정 (뷰 모드 드롭다운, 미니맵 토글)"""
        from PyQt5.QtWidgets import QToolBar, QAction
        
        toolbar = QToolBar("Maze Toolbar")
        # toolbar.setMovable(True) # 기본값이 True
        self.addToolBar(toolbar)
        
        # 0. 중단 및 타이틀 복귀 버튼
        action_abort = QAction("Return to Title", self)
        action_abort.triggered.connect(self._return_to_title)
        toolbar.addAction(action_abort)
        

        
        # 2. 미니맵 (토글 액션)
        self.action_minimap = QAction("Show Minimap", self)
        self.action_minimap.setCheckable(True)
        self.action_minimap.setChecked(False) # 기본값
        toolbar.addAction(self.action_minimap)

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
        self.combo_theme.addItems(["810-Gwan", "Inside Campus", "Path to the Main Gate"]) # Shortened names for better layout
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
        
        # 타이머 라벨 (우측 상단)
        self.lbl_timer = QLabel("00:00")
        # 기본 폰트 사용, 정렬만 설정
        self.lbl_timer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        info_bar.addWidget(self.lbl_game_info)
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

        # 스테이지 BGM 재생
        if self.sound_manager:
            self.sound_manager.play_stage_bgm(mode)

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
                
                # 미로 생성
                print(f"Generating Custom Maze ({width}x{height})...")
                maze = maze_generator.Maze(width, height)
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
            self.lbl_game_info.setText(f"Current Mode: {mode} | WASD: Move | Mouse: Look | ESC: Quit")
            
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

    def _on_game_over(self):
        """게임 오버 (시간 초과) 처리"""
        self.game_timer.stop()
        self.gl_widget.stop_game()
        
        if self.sound_manager:
            self.sound_manager.stop_stage_bgm() # BGM 중지
            self.sound_manager.play_sfx("gameover")
            
        QMessageBox.critical(self, "Game Over", "Time's up! You failed to escape.")
        self._return_to_title()

    def _on_game_won(self):
        """게임 클리어 처리"""
        self.game_timer.stop()
        
        if self.sound_manager:
            self.sound_manager.stop_stage_bgm() # BGM 중지
            self.sound_manager.play_sfx("clear")
            
        QMessageBox.information(self, "Congratulations!", f"You escaped!\nTime: {self.lbl_timer.text()}")
        self._return_to_title()

    def _return_to_title(self):
        """타이틀 화면으로 복귀"""
        # 게임 중지 및 타이머 정지
        self.game_timer.stop()
        if hasattr(self, 'gl_widget') and self.gl_widget.game_active:
            self.gl_widget.stop_game()
            
        # 타이틀 BGM으로 복귀
        if self.sound_manager:
            self.sound_manager.play_title_bgm()
            
        self.stack.setCurrentIndex(0)

