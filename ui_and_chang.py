import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QToolBar, QAction, 
                             QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox,
                             QGroupBox, QRadioButton, QScrollArea, QSizePolicy, QStyle)
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
        dock.setMinimumWidth(240) # 컨트롤 패널의 최소 너비를 조정합니다.
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
        
        self.radio_x_axis = QRadioButton()
        self.label_x_axis = QLabel()
        self.label_x_axis.setBuddy(self.radio_x_axis)
        
        hbox_x = QHBoxLayout()
        hbox_x.setSpacing(4)
        hbox_x.addWidget(self.radio_x_axis)
        hbox_x.addWidget(self.label_x_axis)
        hbox_x.addStretch()
        axis_layout.addLayout(hbox_x)

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

        # ---- 점 목록 UI ----
        self.points_group_box = QGroupBox("Points List")
        self.points_group_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 점 목록이 실제로 표시될 위젯을 QScrollArea의 위젯으로 직접 설정 (불필요한 컨테이너 제거)
        self.list_content_widget = QWidget()
        self.point_list_layout = QVBoxLayout(self.list_content_widget)
        self.point_list_layout.setAlignment(Qt.AlignTop)
        self.point_list_layout.setContentsMargins(8, 4, 8, 4) # QScrollArea가 스크롤바 공간을 관리하므로 오른쪽 여백은 원래대로 8로 유지
        self.point_list_layout.setSpacing(2)
        
        scroll_area.setWidget(self.list_content_widget) # list_content_widget을 직접 scroll_area의 위젯으로 설정
        
        points_group_layout = QVBoxLayout(self.points_group_box)
        points_group_layout.setContentsMargins(6, 6, 6, 6)
        points_group_layout.addWidget(scroll_area)

        
        dock_layout.addWidget(self.points_group_box)

        # ---- 컨트롤 버튼 ----
        dock_layout.addSpacing(10)
        self.btn_clear_points = QPushButton("Clear All Points")
        self.btn_clear_points.clicked.connect(self.glWidget.clear_points)
        dock_layout.addWidget(self.btn_clear_points)
        
        dock.setWidget(dock_widget_content)

        # ---- 시그널-슬롯 연결 및 초기 상태 설정 ----
        self.glWidget.viewModeChanged.connect(self.on_view_mode_changed)
        self.glWidget.pointsChanged.connect(self._update_point_list)
        self.on_view_mode_changed(self.glWidget.view_mode) 
        self._update_point_list()

    def _update_point_list(self):
        """점 목록이 변경될 때 호출되어 UI를 다시 그립니다."""
        # 업데이트 중 위젯이 깜빡이는 것을 방지하기 위해 컨테이너를 숨깁니다.
        self.list_content_widget.hide()

        # 기존에 있던 위젯들을 모두 삭제
        while self.point_list_layout.count():
            child = self.point_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                layout = child.layout()
                while layout.count():
                    sub_child = layout.takeAt(0)
                    if sub_child.widget():
                        sub_child.widget().deleteLater()
                layout.deleteLater()

        # 점 목록을 역순으로 순회하여 최신 점이 위로 오게 합니다.
        for i in range(len(self.glWidget.points) - 1, -1, -1):
            point = self.glWidget.points[i]
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignVCenter) # 수직 중앙 정렬
            
            label = QLabel(f"P{i+1}: ({point[0]:.2f}, {point[1]:.2f})")
            

            delete_btn = QPushButton("×")
            delete_btn.setFixedSize(24, 24) # Set fixed width and height for a square button
            delete_btn.setStyleSheet("QPushButton { border-radius: 4px; }") # Optional: subtle rounding
            delete_btn.clicked.connect(lambda checked, index=i: self.glWidget.delete_point(index))
            
            row_layout.addWidget(label)
            # Stretch를 추가하여 버튼을 항상 오른쪽으로 밀어 정렬시킵니다.
            # 이렇게 하면 스크롤바 유무에 상관없이 버튼 위치가 고정됩니다.
            row_layout.addStretch()
            row_layout.addWidget(delete_btn)
            
            self.point_list_layout.addLayout(row_layout)
        
        # 업데이트가 완료된 후 컨테이너를 다시 표시합니다.
        self.list_content_widget.show()

    def _on_rotation_axis_changed(self):
        """라디오 버튼 선택이 변경될 때 호출되어 회전 축 상태를 업데이트합니다."""
        if self.radio_y_axis.isChecked():
            self.glWidget.set_rotation_axis('Y')
        else:
            self.glWidget.set_rotation_axis('X')

    def on_view_mode_changed(self, mode):
        """뷰 모드 변경에 따라 UI 컨트롤들의 활성화 상태를 동기화합니다."""
        is_2d_mode = (mode == '2D')
        
        self.slices_group_box.setEnabled(is_2d_mode)
        self.axis_group_box.setEnabled(is_2d_mode)
        self.points_group_box.setEnabled(is_2d_mode)
        self.btn_clear_points.setEnabled(is_2d_mode)

        if is_2d_mode:
            self.label_x_axis.setText("Rotate around <font color='red'><u>X-axis</u></font>")
            self.label_y_axis.setText("Rotate around <font color='green'><u>Y-axis</u></font>")
        else:
            self.label_x_axis.setText("Rotate around X-axis")
            self.label_y_axis.setText("Rotate around Y-axis")