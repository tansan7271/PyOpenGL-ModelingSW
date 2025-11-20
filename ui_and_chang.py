# -*- coding: utf-8 -*-
"""
PyOpenGL SOR Modeler의 메인 윈도우 및 UI 구성 요소 정의

이 파일은 애플리케이션의 메인 윈도우(MainWindow) 클래스를 정의하고,
PyQt5를 사용하여 모든 UI(사용자 인터페이스) 요소를 생성, 배치 및 관리합니다.
툴바, 컨트롤 패널, 버튼 등의 UI 요소와 OpenGL 위젯 간의 상호작용(시그널/슬롯)을 설정합니다.
"""
from PyQt5.QtWidgets import (QMainWindow, QToolBar, QAction, QDockWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox,
                             QGroupBox, QRadioButton, QScrollArea, QSizePolicy)
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

        # 각 컨트롤 그룹박스를 생성하여 레이아웃에 추가
        self.slices_group_box = self._create_slices_group()
        dock_layout.addWidget(self.slices_group_box)

        self.axis_group_box = self._create_axis_group()
        dock_layout.addWidget(self.axis_group_box)
        
        self.points_group_box = self._create_points_group()
        dock_layout.addWidget(self.points_group_box)

        # '모든 점 지우기' 버튼 추가
        self.btn_clear_points = QPushButton("Clear All Points")
        dock_layout.addWidget(self.btn_clear_points)

        # dock 위젯에 최종 레이아웃이 적용된 컨테이너를 설정
        dock.setWidget(dock_widget_content)

    def _create_slices_group(self):
        """'Number of Slices' 그룹박스를 생성합니다."""
        group_box = QGroupBox("Number of Slices")
        layout = QVBoxLayout()
        
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
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 점 목록이 실제로 표시될 위젯과 레이아웃
        self.list_content_widget = QWidget()
        self.point_list_layout = QVBoxLayout(self.list_content_widget)
        self.point_list_layout.setAlignment(Qt.AlignTop)
        self.point_list_layout.setContentsMargins(8, 4, 8, 4)
        self.point_list_layout.setSpacing(4)
        
        scroll_area.setWidget(self.list_content_widget)
        
        # 그룹박스에 스크롤 영역 추가
        points_group_layout = QVBoxLayout(group_box)
        points_group_layout.setContentsMargins(6, 6, 6, 6)
        points_group_layout.addWidget(scroll_area)

        return group_box

    def _connect_signals(self):
        """애플리케이션의 모든 시그널과 슬롯을 연결합니다."""
        # 뷰 모드가 변경될 때 UI 활성화 상태를 업데이트
        self.glWidget.viewModeChanged.connect(self._on_view_mode_changed)
        # 점 목록이 변경될 때 UI의 점 목록을 업데이트
        self.glWidget.pointsChanged.connect(self._update_point_list)
        # 'Clear All Points' 버튼 클릭 시 모든 점 삭제
        self.btn_clear_points.clicked.connect(self.glWidget.clear_points)
        # 슬라이스 개수 스핀박스 값 변경 시 데이터 업데이트
        self.spin_slices.valueChanged.connect(self.glWidget.set_num_slices)
        # 회전축 라디오 버튼 선택 변경 시 데이터 업데이트
        self.radio_y_axis.toggled.connect(self._on_rotation_axis_changed)

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
        점이 추가/삭제될 때마다 호출되어 'Points List' UI를 다시 그립니다.
        Flickering(깜빡임)을 방지하기 위해 위젯을 숨겼다가 업데이트 후 다시 표시합니다.
        """
        self.list_content_widget.hide()
        
        # 기존에 표시된 점 목록 UI를 모두 삭제
        self._clear_layout(self.point_list_layout)

        # 점 목록을 역순으로 순회하여 최신 점이 위쪽(목록 상단)에 표시되도록 합니다.
        for i in range(len(self.glWidget.points) - 1, -1, -1):
            point = self.glWidget.points[i]
            
            # 한 줄의 UI (라벨, 삭제 버튼)를 담을 레이아웃
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignVCenter)
            
            # 좌표를 표시하는 라벨
            label = QLabel(f"P{i+1}: ({point[0]:.2f}, {point[1]:.2f})")
            
            # 해당 점을 삭제하는 버튼
            delete_btn = QPushButton("×")
            delete_btn.setFixedSize(24, 24)
            delete_btn.setStyleSheet("QPushButton { border-radius: 4px; }")
            
            # lambda 함수를 사용하여 버튼 클릭 시 삭제할 점의 '인덱스'를 전달합니다.
            # 'checked' 인자는 button.clicked 시그널에서 오지만 사용하지 않습니다.
            delete_btn.clicked.connect(lambda checked, index=i: self.glWidget.delete_point(index))
            
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
        self.slices_group_box.setEnabled(is_2d_mode)
        self.axis_group_box.setEnabled(is_2d_mode)
        self.points_group_box.setEnabled(is_2d_mode)
        self.btn_clear_points.setEnabled(is_2d_mode)

        # 2D 모드일 때, 축 선택 라벨에 색상과 밑줄을 추가하여 직관성을 높입니다.
        if is_2d_mode:
            # HTML 서식을 사용하여 텍스트 스타일을 지정합니다.
            self.label_x_axis.setText("Rotate around <font color='red'><u>X-axis</u></font>")
            self.label_y_axis.setText("Rotate around <font color='green'><u>Y-axis</u></font>")
        else:
            # 3D 모드에서는 기본 텍스트로 되돌립니다.
            self.label_x_axis.setText("Rotate around X-axis")
            self.label_y_axis.setText("Rotate around Y-axis")