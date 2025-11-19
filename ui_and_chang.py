import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QToolBar, QAction, 
                             QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox,
                             QGroupBox, QRadioButton)
from PyQt5.QtCore import Qt
from opengl_haeksim import OpenGLWidget

class MainWindow(QMainWindow):
    """
    애플리케이션의 메인 윈도우(창) 클래스입니다.
    UI의 전체적인 구조(툴바, 독 위젯 등)를 설정하고, 각 UI 요소들의 시그널과 슬롯을 연결합니다.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SOR Modeler')
        self.setGeometry(100, 100, 1024, 768)
        self.setupUI()

    def setupUI(self):
        """UI의 모든 구성요소를 초기화하고 배치합니다."""
        self.glWidget = OpenGLWidget(self)
        self.setCentralWidget(self.glWidget)

        # ---- 툴바 설정 ----
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        action_view_2d = QAction("2D Edit", self)
        action_view_2d.triggered.connect(lambda: self.glWidget.set_view_mode('2D'))
        toolbar.addAction(action_view_2d)

        action_view_3d = QAction("3D View", self)
        action_view_3d.triggered.connect(lambda: self.glWidget.set_view_mode('3D'))
        toolbar.addAction(action_view_3d)

        # ---- 우측 컨트롤 패널 설정 ----
        dock = QDockWidget("Controls", self)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        dock_widget_content = QWidget()
        dock_layout = QVBoxLayout(dock_widget_content)

        # ---- 단면 개수 설정 UI ----
        dock_layout.addSpacing(10)
        self.slices_group_box = QGroupBox("Number of Slices")
        slices_layout = QVBoxLayout()
        self.spin_slices = QSpinBox()
        self.spin_slices.setRange(3, 100)
        self.spin_slices.setValue(self.glWidget.num_slices)
        self.spin_slices.valueChanged.connect(self.glWidget.set_num_slices)
        slices_layout.addWidget(self.spin_slices)
        self.slices_group_box.setLayout(slices_layout)
        dock_layout.addWidget(self.slices_group_box)

        # ---- 회전 축 설정 UI ----
        dock_layout.addSpacing(10)
        self.axis_group_box = QGroupBox("Rotation Axis")
        axis_layout = QVBoxLayout()
        
        # X축 라디오 버튼과 라벨
        # 라벨에 서식(색, 밑줄)을 적용하기 위해 라디오 버튼과 라벨을 분리하고 'buddy'로 연결합니다.
        self.radio_x_axis = QRadioButton()
        self.label_x_axis = QLabel()
        self.label_x_axis.setBuddy(self.radio_x_axis)
        
        hbox_x = QHBoxLayout()
        hbox_x.setSpacing(4) # 버튼과 라벨 사이의 간격을 조절합니다.
        hbox_x.addWidget(self.radio_x_axis)
        hbox_x.addWidget(self.label_x_axis)
        hbox_x.addStretch() # 위젯들을 왼쪽으로 정렬시킵니다.
        axis_layout.addLayout(hbox_x)

        # Y축 라디오 버튼과 라벨
        self.radio_y_axis = QRadioButton()
        self.radio_y_axis.setChecked(True)
        self.radio_y_axis.toggled.connect(self._on_rotation_axis_changed)
        self.label_y_axis = QLabel()
        self.label_y_axis.setBuddy(self.radio_y_axis)

        hbox_y = QHBoxLayout()
        hbox_y.setSpacing(4)
        hbox_y.addWidget(self.radio_y_axis)
        hbox_y.addWidget(self.label_y_axis)
        hbox_y.addStretch()
        axis_layout.addLayout(hbox_y)

        self.axis_group_box.setLayout(axis_layout)
        dock_layout.addWidget(self.axis_group_box)
        dock_layout.addSpacing(10)

        # ---- 점 초기화 버튼 ----
        self.btn_clear_points = QPushButton("Clear Points")
        self.btn_clear_points.clicked.connect(self.glWidget.clear_points)
        dock_layout.addWidget(self.btn_clear_points)
        
        dock_layout.addStretch(1) # 모든 위젯을 위쪽으로 정렬
        dock.setWidget(dock_widget_content)

        # ---- 시그널-슬롯 연결 및 초기 상태 설정 ----
        self.glWidget.viewModeChanged.connect(self.on_view_mode_changed)
        self.on_view_mode_changed(self.glWidget.view_mode) # 초기 상태 강제 설정

    def _on_rotation_axis_changed(self):
        """라디오 버튼 선택이 변경될 때 호출되어 회전 축 상태를 업데이트합니다."""
        if self.radio_y_axis.isChecked():
            self.glWidget.set_rotation_axis('Y')
        else:
            self.glWidget.set_rotation_axis('X')

    def on_view_mode_changed(self, mode):
        """
        뷰 모드 변경에 따라 UI 컨트롤들의 활성화 상태를 동기화합니다.
        2D 편집 모드에서만 컨트롤들이 활성화됩니다.
        """
        is_2d_mode = (mode == '2D')
        
        # 그룹박스 전체를 활성화/비활성화하여 내부 위젯들을 한 번에 제어합니다.
        self.slices_group_box.setEnabled(is_2d_mode)
        self.axis_group_box.setEnabled(is_2d_mode)
        self.btn_clear_points.setEnabled(is_2d_mode)

        if is_2d_mode:
            # 활성화 상태: HTML을 사용하여 텍스트에 색상과 밑줄을 적용합니다.
            self.label_x_axis.setText("Rotate around <font color='red'><u>X-axis</u></font>")
            self.label_y_axis.setText("Rotate around <font color='green'><u>Y-axis</u></font>")
        else:
            # 비활성화 상태: 스타일이 없는 일반 텍스트로 설정하여, 시스템의 비활성화 색상(회색)이 적용되도록 합니다.
            self.label_x_axis.setText("Rotate around X-axis")
            self.label_y_axis.setText("Rotate around Y-axis")
