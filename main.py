import sys
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QOpenGLWidget, QToolBar, QAction, 
                             QDockWidget, QWidget, QVBoxLayout, QPushButton, QLabel, QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal
from OpenGL.GL import *
from OpenGL.GLU import *

class OpenGLWidget(QOpenGLWidget):
    """
    PyQt5의 QOpenGLWidget을 상속받아 OpenGL 렌더링을 수행하는 위젯.
    2D 편집 모드와 3D 뷰 모드를 가집니다.
    """
    viewModeChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_mode = '2D'
        self.points = []
        self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top = -10, 10, -10, 10
        
        # SOR 모델 관련 데이터
        self.num_slices = 30 # 회전체의 단면 개수
        self.sor_vertices = [] # 생성된 SOR 모델의 정점 데이터
        self.sor_faces = []    # 생성된 SOR 모델의 면 데이터

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        glPointSize(5.0)

    def setupProjection(self):
        """
        현재 뷰 모드에 따라 투영 행렬을 설정합니다.
        """
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        w, h = self.width(), self.height()
        if h == 0: h = 1
        aspect_ratio = w / h

        if self.view_mode == '2D':
            self.ortho_left = -10 * aspect_ratio
            self.ortho_right = 10 * aspect_ratio
            self.ortho_bottom = -10
            self.ortho_top = 10
            glOrtho(self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top, -1, 1)
        else: # '3D'
            gluPerspective(45, aspect_ratio, 0.1, 100.0)

    def paintGL(self):
        """
        위젯을 다시 그려야 할 때마다 호출되는 메인 렌더링 함수입니다.
        """
        self.setupProjection()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        if self.view_mode == '2D':
            self.draw_grid()
            self.draw_points()
        else: # '3D'
            gluLookAt(3, 3, 5, 0, 0, 0, 0, 1, 0)
            # SOR 모델이 있으면 모델을 그리고, 없으면 좌표축을 그립니다.
            if self.sor_vertices:
                self.draw_sor_model()
            else:
                self.draw_axes()

    def resizeGL(self, w, h):
        """
        위젯의 크기가 조절될 때 호출됩니다.
        """
        glViewport(0, 0, w, h)
        self.setupProjection()
        
    def mousePressEvent(self, event):
        if self.view_mode == '2D':
            screen_x, screen_y = event.x(), event.y()
            gl_y = self.height() - screen_y
            world_x = self.ortho_left + (screen_x / self.width()) * (self.ortho_right - self.ortho_left)
            world_y = self.ortho_bottom + (gl_y / self.height()) * (self.ortho_top - self.ortho_bottom)
            self.points.append((world_x, world_y))
            print(f"Point added: ({world_x:.2f}, {world_y:.2f})")
            self.update()

    def draw_grid(self):
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        x_start, x_end = math.floor(self.ortho_left), math.ceil(self.ortho_right)
        y_start, y_end = math.floor(self.ortho_bottom), math.ceil(self.ortho_top)
        for i in range(x_start, x_end + 1):
            glVertex2f(i, y_start); glVertex2f(i, y_end)
        for i in range(y_start, y_end + 1):
            glVertex2f(x_start, i); glVertex2f(x_end, i)
        glEnd()

    def draw_points(self):
        """
        사용자가 추가한 점과 그 점들을 잇는 선(프로파일 곡선)을 그립니다.
        """
        if len(self.points) > 1:
            glColor3f(1.0, 1.0, 1.0)
            glBegin(GL_LINE_STRIP)
            for p in self.points:
                glVertex2fv(p)
            glEnd()

        glColor3f(1.0, 1.0, 0.0)
        glBegin(GL_POINTS)
        for p in self.points:
            glVertex2fv(p)
        glEnd()


    def draw_axes(self):
        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0); glVertex3fv((0,0,0)); glVertex3fv((1,0,0))
        glColor3f(0.0, 1.0, 0.0); glVertex3fv((0,0,0)); glVertex3fv((0,1,0))
        glColor3f(0.0, 0.0, 1.0); glVertex3fv((0,0,0)); glVertex3fv((0,0,1))
        glEnd()

    def set_num_slices(self, value):
        """
        SOR 모델의 단면 개수를 설정합니다.
        """
        if self.num_slices != value:
            self.num_slices = value
            print(f"Number of slices set to: {self.num_slices}")
            # 3D 모드일 경우, 단면 개수 변경 시 모델을 다시 생성해야 함
            if self.view_mode == '3D' and self.points:
                self.generate_sor_model()
            else:
                self.update() # 2D 모드에서는 UI만 업데이트

    def generate_sor_model(self):
        """
        self.points를 기반으로 SOR 모델의 정점과 면 데이터를 생성합니다.
        """
        if not self.points or len(self.points) < 2:
            self.sor_vertices = []
            self.sor_faces = []
            print("Not enough points to generate SOR model.")
            return

        self.sor_vertices = []
        self.sor_faces = []
        print(f"Generating SOR model with {self.num_slices} slices from {len(self.points)} profile points.")
        
        # 여기에 SOR 모델 생성 로직이 들어갈 예정
        # 현재는 플레이스홀더로, 3D 뷰에서 아무것도 그리지 않음
        # 나중에 이 함수가 실제 정점과 면 데이터를 sor_vertices, sor_faces에 채울 것임

        self.update() # 모델 생성 후 화면 갱신

    def draw_sor_model(self):
        """
        생성된 SOR 모델을 그립니다. (현재는 플레이스홀더)
        """
        if not self.sor_vertices:
            self.draw_axes() # 모델이 없으면 좌표축을 그림
            return
        
        # 여기에 SOR 모델 렌더링 로직이 들어갈 예정
        # 현재는 아무것도 그리지 않음 (나중에 glBegin(GL_QUADS) 등으로 그릴 것임)
        print("Drawing SOR model (placeholder).")


    def set_view_mode(self, mode):
        if self.view_mode != mode:
            self.view_mode = mode
            self.update()
            print(f"View mode changed to: {mode}")
            self.viewModeChanged.emit(self.view_mode)
            
            if self.view_mode == '3D' and self.points:
                self.generate_sor_model() # 3D 모드 진입 시 모델 생성 시도

    def clear_points(self):
        self.points.clear()
        self.sor_vertices = [] # 점 지우면 SOR 모델도 초기화
        self.sor_faces = []
        print("Points cleared. SOR model reset.")
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SOR Modeler')
        self.setGeometry(100, 100, 1024, 768)
        self.setupUI()

    def setupUI(self):
        self.glWidget = OpenGLWidget(self)
        self.setCentralWidget(self.glWidget)

        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        action_view_2d = QAction("2D Edit", self)
        action_view_2d.triggered.connect(lambda: self.glWidget.set_view_mode('2D'))
        toolbar.addAction(action_view_2d)

        action_view_3d = QAction("3D View", self)
        action_view_3d.triggered.connect(lambda: self.glWidget.set_view_mode('3D'))
        toolbar.addAction(action_view_3d)

        dock = QDockWidget("Controls", self)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        dock_widget_content = QWidget()
        dock_layout = QVBoxLayout(dock_widget_content)

        # 단면 개수 설정 UI
        dock_layout.addWidget(QLabel("Number of Slices:"))
        self.spin_slices = QSpinBox()
        self.spin_slices.setRange(3, 100) # 최소 3개 단면, 최대 100개
        self.spin_slices.setValue(self.glWidget.num_slices) # OpenGLWidget의 초기값으로 설정
        self.spin_slices.valueChanged.connect(self.glWidget.set_num_slices) # 값 변경 시 연결
        dock_layout.addWidget(self.spin_slices)

        self.btn_clear_points = QPushButton("Clear Points")
        self.btn_clear_points.clicked.connect(self.glWidget.clear_points)
        dock_layout.addWidget(self.btn_clear_points)
        
        dock_layout.addStretch(1)
        dock.setWidget(dock_widget_content)

        self.glWidget.viewModeChanged.connect(self.on_view_mode_changed)
        self.on_view_mode_changed(self.glWidget.view_mode)

    def on_view_mode_changed(self, mode):
        if mode == '2D':
            self.btn_clear_points.setEnabled(True)
            self.spin_slices.setEnabled(True) # 2D 모드에서만 단면 개수 조절 가능
        elif mode == '3D':
            self.btn_clear_points.setEnabled(False)
            self.spin_slices.setEnabled(False) # 3D 모드에서는 단면 개수 조절 불가

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())