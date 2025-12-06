# -*- coding: utf-8 -*-
"""
PyOpenGL SOR & Sweep Modeler의 메인 윈도우 및 UI 구성 요소

이 파일은 애플리케이션의 메인 윈도우(MainWindow) 클래스를 정의하고,
PyQt5를 사용하여 모든 UI(사용자 인터페이스) 요소를 생성, 배치 및 관리합니다.
툴바, 컨트롤 패널, 버튼 등의 UI 요소와 OpenGL 위젯 간의 상호작용(시그널/슬롯)을 설정합니다.
"""

from PyQt5.QtWidgets import (QMainWindow, QToolBar, QAction, QDockWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox,
                             QGroupBox, QRadioButton, QScrollArea, QSizePolicy, QFileDialog, QMessageBox,
                             QComboBox, QColorDialog, QCheckBox, QSlider)
from PyQt5.QtCore import Qt
from modeler_opengl import OpenGLWidget

class MainWindow(QMainWindow):
    """
    애플리케이션의 메인 윈도우 클래스입니다.
    
    주요 기능:
    - 전체 UI 레이아웃 구성 (Toolbar, Dock Widget, Central Widget)
    - 사용자 입력 컨트롤 생성 (버튼, 슬라이더, 콤보박스 등)
    - UI 이벤트 처리 및 OpenGLWidget과의 데이터 동기화
    """
    
    def __init__(self):
        """생성자: 윈도우 설정 및 UI 초기화"""
        super().__init__()
        self.setWindowTitle('PyOpenGL SOR & Sweep Modeler')
        self.setGeometry(100, 100, 1024, 768)

        self._setup_ui()

    def _setup_ui(self):
        """전체 UI 구성요소를 초기화하고 배치합니다."""
        # 1. Central Widget (OpenGL 렌더링 영역)
        self.glWidget = OpenGLWidget(self)
        self.setCentralWidget(self.glWidget)

        # 2. UI Components (Toolbar, Dock)
        self._create_toolbar()
        self._create_controls_dock()

        # 3. Signal Connections
        self._connect_signals()

        # 4. Initial State Setup
        self._on_view_mode_changed(self.glWidget.view_mode)
        self._update_point_list()

    # =========================================================================
    # UI 생성 메서드 (UI Creation Methods)
    # =========================================================================

    def _create_toolbar(self):
        """상단 툴바 생성: 뷰 모드 전환 및 파일 저장/로드"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # 2D Edit Mode
        action_view_2d = QAction("2D Edit", self)
        action_view_2d.triggered.connect(lambda: self.glWidget.set_view_mode('2D'))
        toolbar.addAction(action_view_2d)

        # 3D View Mode
        action_view_3d = QAction("3D View", self)
        action_view_3d.triggered.connect(lambda: self.glWidget.set_view_mode('3D'))
        toolbar.addAction(action_view_3d)

        toolbar.addSeparator()

        # Save Model
        action_save = QAction("Save Model", self)
        action_save.triggered.connect(self._on_save_model)
        toolbar.addAction(action_save)

        # Load Model
        action_load = QAction("Load Model", self)
        action_load.triggered.connect(self._on_load_model)
        toolbar.addAction(action_load)

    def _create_controls_dock(self):
        """우측 컨트롤 패널(Dock Widget) 생성"""
        dock = QDockWidget("Controls", self)
        dock.setMinimumWidth(260)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Main Container
        dock_widget_content = QWidget()
        dock_layout = QVBoxLayout(dock_widget_content)
        dock_layout.setContentsMargins(10, 10, 10, 10)
        dock_layout.setSpacing(10)

        # --- 1. 공통 컨트롤 (모델링 모드) ---
        layout_shared = QVBoxLayout()
        layout_shared.setContentsMargins(5, 0, 5, 0)
        layout_shared.setSpacing(20)
        self.mode_group_box = self._create_mode_group()
        layout_shared.addWidget(self.mode_group_box)
        dock_layout.addLayout(layout_shared)

        # --- 2. 2D 컨트롤 (SOR 프로파일 편집) ---
        self.widget_2d_controls = QWidget()
        layout_2d = QVBoxLayout(self.widget_2d_controls)
        layout_2d.setContentsMargins(4, 0, 4, 0)
        layout_2d.setSpacing(20)

        self.slices_group_box = self._create_slices_group()
        layout_2d.addWidget(self.slices_group_box)
        
        self.axis_group_box = self._create_axis_group()
        layout_2d.addWidget(self.axis_group_box)
        
        self.points_group_box = self._create_points_group()
        layout_2d.addWidget(self.points_group_box)

        self.btn_clear_points = QPushButton("Clear All Points")
        layout_2d.addWidget(self.btn_clear_points)
        
        dock_layout.addWidget(self.widget_2d_controls)

        # --- 3. 3D 컨트롤 (렌더링 및 Sweep) ---
        self.widget_3d_controls = QWidget()
        layout_3d = QVBoxLayout(self.widget_3d_controls)
        layout_3d.setContentsMargins(6, 0, 6, 0)
        layout_3d.setSpacing(20)
        
        self.sweep_group_box = self._create_sweep_group()
        layout_3d.addWidget(self.sweep_group_box)
        self.sweep_group_box.hide() # 초기 상태: 숨김 (SOR 모드일 경우)

        self.render_group_box = self._create_render_group()
        layout_3d.addWidget(self.render_group_box)
        
        self.color_group_box = self._create_color_group()
        layout_3d.addWidget(self.color_group_box)
        
        self.projection_group_box = self._create_projection_group()
        layout_3d.addWidget(self.projection_group_box)
        
        self.btn_reset_view = QPushButton("Reset View")
        layout_3d.addWidget(self.btn_reset_view)
        
        dock_layout.addWidget(self.widget_3d_controls)
        self.widget_3d_controls.hide() # 초기 상태: 2D 모드이므로 숨김
        
        layout_3d.addStretch() # 하단 여백 채우기

        dock.setWidget(dock_widget_content)

    def _create_mode_group(self):
        """모델링 모드 선택 (SOR / Sweep) 그룹박스"""
        group_box = QGroupBox("Modeling Mode")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.radio_sor = QRadioButton("SOR")
        self.radio_sor.setChecked(True)
        self.radio_sweep = QRadioButton("Sweep")
        
        layout.addWidget(self.radio_sor)
        layout.addWidget(self.radio_sweep)
        layout.addStretch()
        
        group_box.setLayout(layout)
        return group_box

    def _create_sweep_group(self):
        """Sweep 모드 설정 (길이, 비틀림, 캡) 그룹박스"""
        group_box = QGroupBox("Sweep Settings")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 커스텀 슬라이더 스타일
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 4px; background: #CCCCCC; margin: 2px 0; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #E0E0E0; border: 1px solid #5c5c5c;
                width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;
            }
        """

        # 길이 (Length)
        layout.addWidget(QLabel("Length:"))
        self.slider_length = QSlider(Qt.Horizontal)
        self.slider_length.setStyleSheet(slider_style)
        self.slider_length.setRange(1, 50)
        self.slider_length.setValue(10)
        layout.addWidget(self.slider_length)
        
        layout.addSpacing(10)

        # 비틀림 (Twist)
        layout.addWidget(QLabel("Twist:"))
        self.slider_twist = QSlider(Qt.Horizontal)
        self.slider_twist.setStyleSheet(slider_style)
        self.slider_twist.setRange(0, 360)
        self.slider_twist.setValue(0)
        layout.addWidget(self.slider_twist)
        
        layout.addSpacing(10)

        # 캡 닫기 (Cap Ends)
        self.check_caps = QCheckBox("Cap Ends")
        self.check_caps.setChecked(False)
        layout.addWidget(self.check_caps)
        
        group_box.setLayout(layout)
        return group_box

    def _create_slices_group(self):
        """SOR 분할 수 설정 그룹박스"""
        group_box = QGroupBox("Number of Slices")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.spin_slices = QSpinBox()
        self.spin_slices.setRange(3, 100)
        self.spin_slices.setValue(self.glWidget.num_slices)
        
        layout.addWidget(self.spin_slices)
        group_box.setLayout(layout)
        return group_box

    def _create_axis_group(self):
        """SOR 회전축 선택 그룹박스"""
        group_box = QGroupBox("Rotation Axis")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # X축 (X Axis)
        self.radio_x_axis = QRadioButton()
        self.label_x_axis = QLabel()
        self.label_x_axis.setBuddy(self.radio_x_axis)
        hbox_x = QHBoxLayout()
        hbox_x.setSpacing(4)
        hbox_x.addWidget(self.radio_x_axis); hbox_x.addWidget(self.label_x_axis); hbox_x.addStretch()
        layout.addLayout(hbox_x)

        # Y축 (Y Axis)
        self.radio_y_axis = QRadioButton()
        self.radio_y_axis.setChecked(True)
        self.label_y_axis = QLabel()
        self.label_y_axis.setBuddy(self.radio_y_axis)
        hbox_y = QHBoxLayout()
        hbox_y.setSpacing(4)
        hbox_y.addWidget(self.radio_y_axis); hbox_y.addWidget(self.label_y_axis); hbox_y.addStretch()
        layout.addLayout(hbox_y)

        group_box.setLayout(layout)
        return group_box

    def _create_points_group(self):
        """점 목록 표시 및 관리 그룹박스"""
        group_box = QGroupBox("Points List")
        group_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        layout = QVBoxLayout(group_box)
        layout.setContentsMargins(10, 10, 10, 10)

        # 점 목록 스크롤 영역
        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        
        self.list_content_widget = QWidget()
        self.point_list_layout = QVBoxLayout(self.list_content_widget)
        self.point_list_layout.setAlignment(Qt.AlignTop)
        self.point_list_layout.setContentsMargins(8, 4, 8, 4)
        self.point_list_layout.setSpacing(4)
        
        self.list_scroll.setWidget(self.list_content_widget)
        layout.addWidget(self.list_scroll)
        
        # 경로 닫기 버튼
        self.btn_close_path = QPushButton("Close Path")
        layout.addWidget(self.btn_close_path)

        return group_box

    def _create_render_group(self):
        """렌더링 모드 설정 그룹박스"""
        group_box = QGroupBox("Rendering Mode")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.combo_render_mode = QComboBox()
        self.combo_render_mode.addItems(["Wireframe", "Solid", "Flat Shading", "Gouraud Shading"])
        self.combo_render_mode.setCurrentIndex(1)
        layout.addWidget(self.combo_render_mode)
        
        self.check_wireframe = QCheckBox("Show Wireframe")
        self.check_wireframe.setChecked(True)
        layout.addWidget(self.check_wireframe)
        
        group_box.setLayout(layout)
        return group_box

    def _create_color_group(self):
        """모델 색상 설정 그룹박스"""
        group_box = QGroupBox("Model Color")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.btn_color_picker = QPushButton("Change Color")
        self.btn_color_picker.setStyleSheet("background-color: cyan; color: black;")
        layout.addWidget(self.btn_color_picker)
        
        group_box.setLayout(layout)
        return group_box

    def _create_projection_group(self):
        """투영 모드 설정 그룹박스"""
        group_box = QGroupBox("Projection Mode")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.combo_projection = QComboBox()
        self.combo_projection.addItems(["Perspective", "Orthographic"])
        layout.addWidget(self.combo_projection)
        
        group_box.setLayout(layout)
        return group_box

    # =========================================================================
    # 시그널 연결 (Signal Connections)
    # =========================================================================

    def _connect_signals(self):
        """UI 요소와 로직 간의 시그널-슬롯 연결"""
        # OpenGLWidget에서 오는 시그널
        self.glWidget.viewModeChanged.connect(self._on_view_mode_changed)
        self.glWidget.pointsChanged.connect(self._update_point_list)
        
        # 2D 컨트롤
        self.btn_clear_points.clicked.connect(self.glWidget.clear_points)
        self.btn_close_path.clicked.connect(self.glWidget.close_current_path)
        self.spin_slices.valueChanged.connect(self.glWidget.set_num_slices)
        self.radio_x_axis.toggled.connect(lambda: self.glWidget.set_rotation_axis('X'))
        self.radio_y_axis.toggled.connect(lambda: self.glWidget.set_rotation_axis('Y'))
        
        # 공통 컨트롤
        self.radio_sor.toggled.connect(self._on_modeling_mode_changed)
        
        # 3D 컨트롤 (Sweep)
        self.slider_length.valueChanged.connect(lambda v: self.glWidget.set_sweep_length(float(v)))
        self.slider_twist.valueChanged.connect(lambda v: self.glWidget.set_sweep_twist(float(v)))
        self.check_caps.toggled.connect(self.glWidget.set_sweep_caps)
        
        # 3D 컨트롤 (렌더링)
        self.combo_render_mode.currentIndexChanged.connect(self._on_render_mode_changed)
        self.check_wireframe.toggled.connect(self._on_wireframe_toggled)
        self.btn_color_picker.clicked.connect(self._on_color_changed)
        self.combo_projection.currentTextChanged.connect(self._on_projection_changed)
        self.btn_reset_view.clicked.connect(self.glWidget.reset_view)

    # =========================================================================
    # 이벤트 핸들러 및 슬롯 (Event Handlers & Slots)
    # =========================================================================

    def _on_view_mode_changed(self, mode):
        """뷰 모드 변경 시 UI 상태 업데이트"""
        is_2d = (mode == '2D')
        
        # 패널 전환
        if is_2d:
            self.widget_2d_controls.show()
            self.widget_3d_controls.hide()
            # 2D 모드 텍스트 강조
            self.label_x_axis.setText("Rotate around <font color='red'><u>X-axis</u></font>")
            self.label_y_axis.setText("Rotate around <font color='green'><u>Y-axis</u></font>")
        else:
            self.widget_2d_controls.hide()
            self.widget_3d_controls.show()
            # 3D 모드 텍스트 복구
            self.label_x_axis.setText("Rotate around X-axis")
            self.label_y_axis.setText("Rotate around Y-axis")

    def _on_modeling_mode_changed(self):
        """모델링 모드 변경 시 UI 및 데이터 업데이트"""
        is_sor = self.radio_sor.isChecked()
        self.glWidget.set_modeling_mode(0 if is_sor else 1)
        
        # 관련 컨트롤 표시/숨김
        self.slices_group_box.setVisible(is_sor)
        self.axis_group_box.setVisible(is_sor)
        self.sweep_group_box.setVisible(not is_sor)

    def _on_render_mode_changed(self, index):
        """렌더링 모드 변경 처리"""
        self.glWidget.render_mode = index
        # Wireframe 모드일 때 'Show Wireframe' 강제 활성화
        if index == 0:
            self.check_wireframe.setChecked(True)
            self.check_wireframe.setEnabled(False)
        else:
            self.check_wireframe.setEnabled(True)
        self.glWidget.update()

    def _on_wireframe_toggled(self, checked):
        """와이어프레임 토글 처리"""
        self.glWidget.show_wireframe = checked
        self.glWidget.update()

    def _on_color_changed(self):
        """색상 변경 다이얼로그 처리"""
        color = QColorDialog.getColor()
        if color.isValid():
            rgb = (color.redF(), color.greenF(), color.blueF())
            self.glWidget.model_color = rgb
            self.btn_color_picker.setStyleSheet(f"background-color: {color.name()}; color: black;")
            self.glWidget.update()

    def _on_projection_changed(self, text):
        """투영 모드 변경 처리"""
        self.glWidget.projection_mode = text
        self.glWidget.update()

    def _update_point_list(self):
        """점 목록 UI 갱신"""
        self.list_content_widget.hide()
        self._clear_layout(self.point_list_layout)

        # 역순으로 순회 (최신 점이 위로)
        for path_idx in range(len(self.glWidget.paths) - 1, -1, -1):
            path_data = self.glWidget.paths[path_idx]
            path = path_data['points']
            is_closed = path_data['closed']
            
            if not path: continue
                
            # Path Header
            status = "[Closed]" if is_closed else "[Open]"
            header = QLabel(f"--- Path {path_idx + 1} {status} ---")
            header.setStyleSheet("font-weight: bold; color: #555;")
            self.point_list_layout.addWidget(header)

            # Points
            for pt_idx in range(len(path) - 1, -1, -1):
                point = path[pt_idx]
                row = QHBoxLayout()
                row.setAlignment(Qt.AlignVCenter)
                
                label = QLabel(f"P{pt_idx+1}: ({point[0]:.2f}, {point[1]:.2f})")
                btn_del = QPushButton("×")
                btn_del.setFixedSize(24, 24)
                btn_del.setStyleSheet("QPushButton { border-radius: 4px; }")
                # Lambda Capture 주의
                btn_del.clicked.connect(lambda _, p=path_idx, i=pt_idx: self.glWidget.delete_point(p, i))
                
                row.addWidget(label)
                row.addStretch()
                row.addWidget(btn_del)
                self.point_list_layout.addLayout(row)
        
        self.list_content_widget.show()

    def _clear_layout(self, layout):
        """레이아웃 내부 위젯 재귀 삭제"""
        if layout is None: return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self._clear_layout(item.layout())

    # =========================================================================
    # 파일 입출력 핸들러 (File I/O Handlers)
    # =========================================================================

    def _on_save_model(self):
        """모델 저장 핸들러"""
        if not self.glWidget.sor_vertices:
            QMessageBox.warning(self, "Warning", "저장할 3D 모델이 없습니다.")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Model", "", "DAT Files (*.dat);;All Files (*)", options=options)
        
        if file_path:
            self.glWidget.save_model(file_path)
            QMessageBox.information(self, "Success", f"저장 완료:\n{file_path}")

    def _on_load_model(self):
        """모델 로드 핸들러"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Model", "", "DAT Files (*.dat);;All Files (*)", options=options)
        
        if file_path:
            self.glWidget.load_model(file_path)
            
            # UI Sync (Block Signals to prevent loops)
            self.spin_slices.blockSignals(True)
            self.spin_slices.setValue(self.glWidget.num_slices)
            self.spin_slices.blockSignals(False)
            
            self.radio_x_axis.blockSignals(True); self.radio_y_axis.blockSignals(True)
            if self.glWidget.rotation_axis == 'Y': self.radio_y_axis.setChecked(True)
            else: self.radio_x_axis.setChecked(True)
            self.radio_x_axis.blockSignals(False); self.radio_y_axis.blockSignals(False)
            
            self.combo_render_mode.blockSignals(True)
            self.combo_render_mode.setCurrentIndex(self.glWidget.render_mode)
            self.combo_render_mode.blockSignals(False)
            
            r, g, b = self.glWidget.model_color
            self.btn_color_picker.setStyleSheet(f"background-color: rgb({int(r*255)}, {int(g*255)}, {int(b*255)}); color: black;")
            
            # Sync Modeling Mode & Sweep Settings
            self.radio_sor.blockSignals(True); self.radio_sweep.blockSignals(True)
            is_sor = (self.glWidget.modeling_mode == 0)
            if is_sor: self.radio_sor.setChecked(True)
            else: self.radio_sweep.setChecked(True)
            self.radio_sor.blockSignals(False); self.radio_sweep.blockSignals(False)
            
            # Update UI Visibility without triggering generation
            self.slices_group_box.setVisible(is_sor)
            self.axis_group_box.setVisible(is_sor)
            self.sweep_group_box.setVisible(not is_sor)
            
            self.slider_length.blockSignals(True); self.slider_twist.blockSignals(True); self.check_caps.blockSignals(True)
            self.slider_length.setValue(int(self.glWidget.sweep_length))
            self.slider_twist.setValue(int(self.glWidget.sweep_twist))
            self.check_caps.setChecked(self.glWidget.sweep_caps)
            self.slider_length.blockSignals(False); self.slider_twist.blockSignals(False); self.check_caps.blockSignals(False)
            
            QMessageBox.information(self, "Success", f"로드 완료:\n{file_path}")