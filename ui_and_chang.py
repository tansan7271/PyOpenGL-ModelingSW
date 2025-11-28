# -*- coding: utf-8 -*-
"""
PyOpenGL SOR Modeler의 메인 윈도우 및 UI 구성 요소 정의

이 파일은 애플리케이션의 메인 윈도우(MainWindow) 클래스를 정의하고,
PyQt5를 사용하여 모든 UI(사용자 인터페이스) 요소를 생성, 배치 및 관리합니다.
툴바, 컨트롤 패널, 버튼 등의 UI 요소와 OpenGL 위젯 간의 상호작용(시그널/슬롯)을 설정합니다.
"""
from PyQt5.QtWidgets import (QMainWindow, QToolBar, QAction, QDockWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox,
                             QGroupBox, QRadioButton, QScrollArea, QSizePolicy, QFileDialog, QMessageBox,
                             QComboBox, QColorDialog, QCheckBox)
from PyQt5.QtCore import Qt
from opengl_haeksim import OpenGLWidget


class MainWindow(QMainWindow):
    """
    애플리케이션의 메인 윈도우(창) 클래스입니다.
    UI의 전체적인 구조(툴바, 독 위젯 등)를 설정하고, 각 UI 요소들의 시그널과 슬롯을 연결합니다.
    """
    def __init__(self):
        """MainWindow의 생성자입니다."""
        super().__init__()
        self.setWindowTitle('PyOpenGL SOR Modeler')
        self.setGeometry(100, 100, 1024, 768)

        self._setup_ui()

    def _setup_ui(self):
        """
        UI의 모든 구성요소를 초기화하고 배치합니다.
        메서드들을 호출하여 UI를 체계적으로 구성합니다.
        """
        # 중앙 위젯으로 OpenGL 렌더링 영역을 설정합니다.
        self.glWidget = OpenGLWidget(self)
        self.setCentralWidget(self.glWidget)

        # UI의 각 부분을 생성합니다.
        self._create_toolbar()
        self._create_controls_dock()

        # 시그널-슬롯을 연결하여 UI와 데이터 로직을 동기화합니다.
        self._connect_signals()

        # 초기 UI 상태를 설정합니다.
        self._on_view_mode_changed(self.glWidget.view_mode)
        self._update_point_list()

    def _create_toolbar(self):
        """상단 툴바를 생성하고 액션(버튼)을 추가합니다."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # 2D 편집 모드로 전환하는 액션
        action_view_2d = QAction("2D Edit", self)
        action_view_2d.triggered.connect(lambda: self.glWidget.set_view_mode('2D'))
        toolbar.addAction(action_view_2d)

        # 3D 뷰 모드로 전환하는 액션
        action_view_3d = QAction("3D View", self)
        action_view_3d.triggered.connect(lambda: self.glWidget.set_view_mode('3D'))
        toolbar.addAction(action_view_3d)

        toolbar.addSeparator()

        # 모델 저장 액션
        action_save = QAction("Save Model", self)
        action_save.triggered.connect(self._on_save_model)
        toolbar.addAction(action_save)

        # 모델 불러오기 액션
        action_load = QAction("Load Model", self)
        action_load.triggered.connect(self._on_load_model)
        toolbar.addAction(action_load)

    def _create_controls_dock(self):
        """우측에 도킹되는 컨트롤 패널을 생성합니다."""
        dock = QDockWidget("Controls", self)
        dock.setMinimumWidth(260)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # 컨트롤 패널의 모든 위젯을 담을 컨테이너 위젯과 레이아웃
        dock_widget_content = QWidget()
        dock_layout = QVBoxLayout(dock_widget_content)
        dock_layout.setContentsMargins(10, 10, 10, 10)
        dock_layout.setSpacing(10)

        # --- 2D Controls Widget ---
        self.widget_2d_controls = QWidget()
        layout_2d = QVBoxLayout(self.widget_2d_controls)
        layout_2d.setContentsMargins(4, 0, 4, 0)
        layout_2d.setSpacing(20)

        # 각 컨트롤 그룹박스를 생성하여 2D 레이아웃에 추가
        self.slices_group_box = self._create_slices_group()
        layout_2d.addWidget(self.slices_group_box)

        self.axis_group_box = self._create_axis_group()
        layout_2d.addWidget(self.axis_group_box)
        
        self.points_group_box = self._create_points_group()
        layout_2d.addWidget(self.points_group_box)

        # '모든 점 지우기' 버튼 추가
        self.btn_clear_points = QPushButton("Clear All Points")
        layout_2d.addWidget(self.btn_clear_points)
        
        # 2D 위젯을 메인 독 레이아웃에 추가
        dock_layout.addWidget(self.widget_2d_controls)

        # --- 3D Controls Widget ---
        self.widget_3d_controls = QWidget()
        layout_3d = QVBoxLayout(self.widget_3d_controls)
        layout_3d.setContentsMargins(6, 0, 6, 0)
        layout_3d.setSpacing(20)
        
        # 3D 컨트롤 그룹박스 생성 및 추가
        self.render_group_box = self._create_render_group()
        layout_3d.addWidget(self.render_group_box)
        
        self.color_group_box = self._create_color_group()
        layout_3d.addWidget(self.color_group_box)
        
        self.projection_group_box = self._create_projection_group()
        layout_3d.addWidget(self.projection_group_box)
        
        # 3D 위젯을 메인 독 레이아웃에 추가 (초기에는 숨김)
        dock_layout.addWidget(self.widget_3d_controls)
        self.widget_3d_controls.hide()
        
        # 상단 정렬을 위해 빈 공간 추가 (2D, 3D 모두 적용됨)
        # 2D 모드에서는 points_group_box가 늘어나야 하므로 addStretch를 제거하거나 
        # points_group_box의 sizePolicy를 활용해야 함.
        # 여기서는 3D 모드일 때만 하단 여백이 필요하므로, 3D 레이아웃에만 stretch 추가.
        layout_3d.addStretch()

        # dock 위젯에 최종 레이아웃이 적용된 컨테이너를 설정
        dock.setWidget(dock_widget_content)

    def _create_slices_group(self):
        """'Number of Slices' 그룹박스를 생성합니다."""
        group_box = QGroupBox("Number of Slices")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.spin_slices = QSpinBox()
        self.spin_slices.setRange(3, 100)
        self.spin_slices.setValue(self.glWidget.num_slices) # 초기값 설정
        
        layout.addWidget(self.spin_slices)
        group_box.setLayout(layout)
        return group_box

    def _create_axis_group(self):
        """'Rotation Axis' 그룹박스와 라디오 버튼들을 생성합니다."""
        group_box = QGroupBox("Rotation Axis")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # X축 라디오 버튼과 레이블
        self.radio_x_axis = QRadioButton()
        self.label_x_axis = QLabel()
        self.label_x_axis.setBuddy(self.radio_x_axis)
        
        hbox_x = QHBoxLayout()
        hbox_x.setSpacing(4)
        hbox_x.addWidget(self.radio_x_axis)
        hbox_x.addWidget(self.label_x_axis)
        hbox_x.addStretch()
        layout.addLayout(hbox_x)

        # Y축 라디오 버튼과 레이블
        self.radio_y_axis = QRadioButton()
        self.radio_y_axis.setChecked(True) # Y축을 기본 선택으로 설정
        self.label_y_axis = QLabel()
        self.label_y_axis.setBuddy(self.radio_y_axis)

        hbox_y = QHBoxLayout()
        hbox_y.setSpacing(4)
        hbox_y.addWidget(self.radio_y_axis)
        hbox_y.addWidget(self.label_y_axis)
        hbox_y.addStretch()
        layout.addLayout(hbox_y)

        group_box.setLayout(layout)
        return group_box

    def _create_points_group(self):
        """'Points List' 그룹박스와 스크롤 가능한 점 목록 영역을 생성합니다."""
        group_box = QGroupBox("Points List")
        group_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # 그룹박스 내부 레이아웃
        points_group_layout = QVBoxLayout(group_box)
        points_group_layout.setContentsMargins(10, 10, 10, 10)

        # 점 리스트 (스크롤 영역)
        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        
        self.list_content_widget = QWidget()
        self.point_list_layout = QVBoxLayout(self.list_content_widget)
        self.point_list_layout.setAlignment(Qt.AlignTop)
        self.point_list_layout.setContentsMargins(8, 4, 8, 4)
        self.point_list_layout.setSpacing(4)
        
        self.list_scroll.setWidget(self.list_content_widget)
        points_group_layout.addWidget(self.list_scroll)
        
        # Close Path 버튼 (명시적 닫기)
        self.btn_close_path = QPushButton("Close Path")
        points_group_layout.addWidget(self.btn_close_path)

        return group_box

    def _create_render_group(self):
        """3D 렌더링 모드 설정 그룹박스"""
        group_box = QGroupBox("Rendering Mode")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.combo_render_mode = QComboBox()
        self.combo_render_mode.addItems(["Wireframe", "Solid", "Flat Shading", "Gouraud Shading"])
        self.combo_render_mode.setCurrentIndex(1) # Default: Solid
        
        layout.addWidget(self.combo_render_mode)
        
        # Wireframe Toggle Checkbox
        self.check_wireframe = QCheckBox("Show Wireframe")
        self.check_wireframe.setChecked(True)
        layout.addWidget(self.check_wireframe)
        
        group_box.setLayout(layout)
        return group_box

    def _create_color_group(self):
        """모델 색상 변경 그룹박스"""
        group_box = QGroupBox("Model Color")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.btn_color_picker = QPushButton("Change Color")
        # 버튼 배경색을 현재 모델 색상으로 설정
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

    def _connect_signals(self):
        """애플리케이션의 모든 시그널과 슬롯을 연결합니다."""
        # 뷰 모드가 변경될 때 UI 활성화 상태를 업데이트
        self.glWidget.viewModeChanged.connect(self._on_view_mode_changed)
        # 점 목록이 변경될 때 UI의 점 목록을 업데이트
        self.glWidget.pointsChanged.connect(self._update_point_list)
        
        # 컨트롤 패널 시그널 연결
        # 'Clear All Points' 버튼 클릭 시 모든 점 삭제
        self.btn_clear_points.clicked.connect(self.glWidget.clear_points)
        # 'Close Path' 버튼 클릭 시 현재 경로 닫기
        self.btn_close_path.clicked.connect(self.glWidget.close_current_path)
        # 슬라이스 개수 스핀박스 값 변경 시 데이터 업데이트
        self.spin_slices.valueChanged.connect(self.glWidget.set_num_slices)
        # 회전축 라디오 버튼 선택 변경 시 데이터 업데이트
        self.radio_x_axis.toggled.connect(lambda: self.glWidget.set_rotation_axis('X'))
        self.radio_y_axis.toggled.connect(lambda: self.glWidget.set_rotation_axis('Y'))
        
        # 3D 컨트롤 시그널 연결
        self.combo_render_mode.currentIndexChanged.connect(self._on_render_mode_changed)
        self.check_wireframe.toggled.connect(self._on_wireframe_toggled)
        self.btn_color_picker.clicked.connect(self._on_color_changed)
        self.combo_projection.currentTextChanged.connect(self._on_projection_changed)

    def _clear_layout(self, layout):
        """
        레이아웃 안의 모든 아이템(위젯, 하위 레이아웃)을 재귀적으로 안전하게 삭제하는 헬퍼 함수입니다.
        """
        if layout is None:
            return
        # 레이아웃의 모든 아이템을 제거할 때까지 반복
        while layout.count():
            item = layout.takeAt(0) # 레이아웃에서 첫 번째 아이템을 가져옴 (그리고 제거)
            widget = item.widget()
            
            if widget is not None:
                # 아이템이 위젯이면, 나중에 안전하게 삭제하도록 deleteLater() 호출
                widget.deleteLater()
            else:
                # 아이템이 위젯이 아니면, 하위 레이아웃일 수 있음
                sub_layout = item.layout()
                if sub_layout is not None:
                    # 하위 레이아웃의 내용물을 재귀적으로 삭제
                    self._clear_layout(sub_layout)

    def _update_point_list(self):
        """
        점이 추가/삭제/이동될 때마다 호출되어 'Points List' UI를 다시 그립니다.
        다중 경로(Multi-path)를 지원하도록 중첩 루프를 사용하여 모든 경로의 점을 표시합니다.
        """
        self.list_content_widget.hide()
        
        # 기존에 표시된 점 목록 UI를 모두 삭제
        self._clear_layout(self.point_list_layout)

        # 모든 경로를 순회
        # 역순으로 보여줄지 정순으로 보여줄지 결정해야 함.
        # 여기서는 최신 경로, 최신 점이 위로 오도록 역순 순회.
        for path_idx in range(len(self.glWidget.paths) - 1, -1, -1):
            path_data = self.glWidget.paths[path_idx]
            path = path_data['points']
            is_closed = path_data['closed']
            
            if not path:
                continue
                
            # 경로 헤더 표시 (선택 사항)
            # 닫힌 경로인지 표시
            status = "[Closed]" if is_closed else "[Open]"
            header = QLabel(f"--- Path {path_idx + 1} {status} ---")
            header.setStyleSheet("font-weight: bold; color: #555;")
            self.point_list_layout.addWidget(header)

            for pt_idx in range(len(path) - 1, -1, -1):
                point = path[pt_idx]
                
                # 한 줄의 UI (라벨, 삭제 버튼)를 담을 레이아웃
                row_layout = QHBoxLayout()
                row_layout.setAlignment(Qt.AlignVCenter)
                
                # 좌표를 표시하는 라벨 (Path 번호도 같이 표시)
                label = QLabel(f"P{pt_idx+1}: ({point[0]:.2f}, {point[1]:.2f})")
                
                # 해당 점을 삭제하는 버튼
                delete_btn = QPushButton("×")
                delete_btn.setFixedSize(24, 24)
                delete_btn.setStyleSheet("QPushButton { border-radius: 4px; }")
                
                # lambda 함수를 사용하여 버튼 클릭 시 삭제할 점의 '경로 인덱스'와 '점 인덱스'를 전달합니다.
                delete_btn.clicked.connect(lambda checked, p_i=path_idx, pt_i=pt_idx: self.glWidget.delete_point(p_i, pt_i))
                
                row_layout.addWidget(label)
                row_layout.addStretch() # 가변 공간을 추가하여 버튼을 오른쪽 끝으로 밀어냅니다.
                row_layout.addWidget(delete_btn)
                
                self.point_list_layout.addLayout(row_layout)
        
        self.list_content_widget.show()

    def _on_rotation_axis_changed(self):
        """라디오 버튼 선택이 변경될 때 호출되어 회전 축 상태를 업데이트합니다."""
        # Y축 라디오 버튼이 선택되면 'Y', 아니면 'X'를 glWidget에 전달합니다.
        axis = 'Y' if self.radio_y_axis.isChecked() else 'X'
        self.glWidget.set_rotation_axis(axis)

    def _on_view_mode_changed(self, mode):
        """뷰 모드 변경에 따라 UI 컨트롤들의 활성화 상태와 텍스트를 동기화합니다."""
        is_2d_mode = (mode == '2D')
        
        # 2D 편집 모드일 때만 컨트롤들을 활성화합니다.
        # self.slices_group_box.setEnabled(is_2d_mode)
        # self.axis_group_box.setEnabled(is_2d_mode)
        # self.points_group_box.setEnabled(is_2d_mode)
        # self.btn_clear_points.setEnabled(is_2d_mode)
        
        # 뷰 모드에 따라 해당 컨트롤 위젯만 표시
        if is_2d_mode:
            self.widget_2d_controls.show()
            self.widget_3d_controls.hide()
        else:
            self.widget_2d_controls.hide()
            self.widget_3d_controls.show()

        # 2D 모드일 때, 축 선택 라벨에 색상과 밑줄을 추가하여 직관성을 높입니다.
        if is_2d_mode:
            # HTML 서식을 사용하여 텍스트 스타일을 지정합니다.
            self.label_x_axis.setText("Rotate around <font color='red'><u>X-axis</u></font>")
            self.label_y_axis.setText("Rotate around <font color='green'><u>Y-axis</u></font>")
        else:
            # 3D 모드에서는 기본 텍스트로 되돌립니다.
            self.label_x_axis.setText("Rotate around X-axis")
            self.label_y_axis.setText("Rotate around Y-axis")

    def _on_render_mode_changed(self, index):
        """렌더링 모드 콤보박스 변경 시 호출"""
        self.glWidget.render_mode = index
        
        # Wireframe 모드(0)일 때는 'Show Wireframe' 체크박스를 강제로 켜고 비활성화
        if index == 0:
            self.check_wireframe.setChecked(True)
            self.check_wireframe.setEnabled(False)
        else:
            self.check_wireframe.setEnabled(True)
            # 이전 상태 복구는 복잡하므로 일단 사용자가 다시 설정하도록 둠
            
        self.glWidget.update()

    def _on_wireframe_toggled(self, checked):
        """와이어프레임 토글 변경 시 호출"""
        self.glWidget.show_wireframe = checked
        self.glWidget.update()

    def _on_color_changed(self):
        """색상 변경 버튼 클릭 시 호출"""
        color = QColorDialog.getColor()
        if color.isValid():
            rgb = (color.redF(), color.greenF(), color.blueF())
            self.glWidget.model_color = rgb
            self.btn_color_picker.setStyleSheet(f"background-color: {color.name()}; color: black;")
            self.glWidget.update()

    def _on_projection_changed(self, text):
        """투영 모드 콤보박스 변경 시 호출"""
        self.glWidget.projection_mode = text
        self.glWidget.update()

    def _on_save_model(self):
        """
        'Save Model' 버튼 클릭 시 호출됩니다.
        파일 저장 대화상자를 띄워 사용자가 지정한 경로에 현재 모델을 .dat 파일로 저장합니다.
        """
        # 3D 모델 데이터가 없으면 경고 메시지 표시
        if not self.glWidget.sor_vertices:
            QMessageBox.warning(self, "Warning", "생성된 3D 모델이 없습니다.\n먼저 2D 프로파일을 그리고 3D 뷰로 전환하여 모델을 생성해주세요.")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Model", "", "DAT Files (*.dat);;All Files (*)", options=options)
        
        if file_path:
            self.glWidget.save_model(file_path)
            QMessageBox.information(self, "Success", f"모델이 성공적으로 저장되었습니다:\n{file_path}")

    def _on_load_model(self):
        """
        'Load Model' 버튼 클릭 시 호출됩니다.
        파일 열기 대화상자를 띄워 .dat 파일을 선택하고 모델을 불러옵니다.
        """
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Model", "", "DAT Files (*.dat);;All Files (*)", options=options)
        
        if file_path:
            self.glWidget.load_model(file_path)
            
            # 모델 로드 후 UI 상태 동기화
            # 1. 단면 개수 스핀박스 업데이트
            self.spin_slices.blockSignals(True) # 시그널 루프 방지
            self.spin_slices.setValue(self.glWidget.num_slices)
            self.spin_slices.blockSignals(False)
            
            # 2. 회전축 라디오 버튼 업데이트
            self.radio_x_axis.blockSignals(True)
            self.radio_y_axis.blockSignals(True)
            if self.glWidget.rotation_axis == 'Y':
                self.radio_y_axis.setChecked(True)
            else:
                self.radio_x_axis.setChecked(True)
            self.radio_x_axis.blockSignals(False)
            self.radio_y_axis.blockSignals(False)
            
            # 3. 렌더링 모드 및 색상 업데이트 (v5 지원)
            self.combo_render_mode.blockSignals(True)
            self.combo_render_mode.setCurrentIndex(self.glWidget.render_mode)
            self.combo_render_mode.blockSignals(False)
            
            # 색상 버튼 스타일 업데이트
            r, g, b = self.glWidget.model_color
            color_style = f"background-color: rgb({int(r*255)}, {int(g*255)}, {int(b*255)}); color: black;"
            self.btn_color_picker.setStyleSheet(color_style)
            
            QMessageBox.information(self, "Success", f"모델을 성공적으로 불러왔습니다:\n{file_path}")