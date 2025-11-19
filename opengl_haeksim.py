import math
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import pyqtSignal
from OpenGL.GL import *
from OpenGL.GLU import *

class OpenGLWidget(QOpenGLWidget):
    """
    PyQt5의 QOpenGLWidget을 상속받아 OpenGL 렌더링을 수행하는 핵심 위젯입니다.
    2D 프로파일 편집 모드와 3D 모델 뷰 모드를 가지며, 모든 그래픽 처리 및 사용자 입력을 담당합니다.
    """
    viewModeChanged = pyqtSignal(str)
    pointsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_mode = '2D'
        self.points = []
        self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top = -10, 10, -10, 10
        self.num_slices = 30
        self.rotation_axis = 'Y'
        self.sor_vertices = []
        self.sor_faces = []

    def initializeGL(self):
        """OpenGL 초기화를 수행합니다. 배경색, 깊이 테스트, 포인트 크기 등을 설정합니다."""
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        glPointSize(5.0)

    def setupProjection(self):
        """
        현재 뷰 모드에 따라 투영(Projection) 행렬을 설정합니다.
        이는 3D 공간을 2D 화면에 어떻게 보여줄지 결정하는 단계입니다.
        """
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        w, h = self.width(), self.height()
        if h == 0: h = 1
        aspect_ratio = w / h

        if self.view_mode == '2D':
            # 2D 모드에서는 직교 투영(Orthographic Projection)을 사용합니다.
            # 원근감이 없으며, 모든 객체는 크기 그대로 화면에 표시됩니다.
            self.ortho_left = -10 * aspect_ratio
            self.ortho_right = 10 * aspect_ratio
            self.ortho_bottom = -10
            self.ortho_top = 10
            glOrtho(self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top, -1, 1)
        else: # '3D'
            # 3D 모드에서는 원근 투영(Perspective Projection)을 사용합니다.
            # 멀리 있는 것은 작게, 가까이 있는 것은 크게 보여 현실감을 더합니다.
            gluPerspective(45, aspect_ratio, 0.1, 100.0)

    def paintGL(self):
        """화면을 다시 그려야 할 때마다 호출되는 메인 렌더링 함수입니다."""
        self.setupProjection()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if self.view_mode == '2D':
            self.draw_grid()
            self.draw_points()
        else: # '3D'
            gluLookAt(3, 3, 5, 0, 0, 0, 0, 1, 0)
            if self.sor_vertices:
                self.draw_sor_model()
            else:
                self.draw_axes()

    def resizeGL(self, w, h):
        """위젯의 크기가 조절될 때 호출됩니다."""
        glViewport(0, 0, w, h)
        self.setupProjection()
        
    def mousePressEvent(self, event):
        """2D 모드에서 마우스 클릭 시, 화면 좌표를 월드 좌표로 변환하여 점을 추가합니다."""
        if self.view_mode == '2D':
            screen_x, screen_y = event.x(), event.y()
            gl_y = self.height() - screen_y
            world_x = self.ortho_left + (screen_x / self.width()) * (self.ortho_right - self.ortho_left)
            world_y = self.ortho_bottom + (gl_y / self.height()) * (self.ortho_top - self.ortho_bottom)
            self.points.append((world_x, world_y))
            self.update()
            self.pointsChanged.emit()

    def draw_grid(self):
        """2D 편집 모드에서 배경에 격자와 기준 축을 그립니다."""
        x_start, x_end = math.floor(self.ortho_left), math.ceil(self.ortho_right)
        y_start, y_end = math.floor(self.ortho_bottom), math.ceil(self.ortho_top)
        z_grid = -0.1
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for i in range(x_start, x_end + 1):
            if i == 0: continue
            glVertex3f(i, y_start, z_grid)
            glVertex3f(i, y_end, z_grid)
        for i in range(y_start, y_end + 1):
            if i == 0: continue
            glVertex3f(x_start, i, z_grid)
            glVertex3f(x_end, i, z_grid)
        glEnd()
        glColor3f(1.0, 0.0, 0.0) 
        glBegin(GL_LINES)
        glVertex3f(x_start, 0, z_grid)
        glVertex3f(x_end, 0, z_grid)
        glEnd()
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, y_start, z_grid)
        glVertex3f(0, y_end, z_grid)
        glEnd()

    def draw_points(self):
        """사용자가 추가한 점들과 프로파일 곡선을 그립니다."""
        z_points = 0.1
        if len(self.points) > 1:
            glColor3f(1.0, 1.0, 1.0)
            glBegin(GL_LINE_STRIP)
            for p in self.points:
                glVertex3f(p[0], p[1], z_points)
            glEnd()
        glColor3f(1.0, 1.0, 0.0)
        glBegin(GL_POINTS)
        for p in self.points:
            glVertex3f(p[0], p[1], z_points)
        glEnd()

    def draw_axes(self):
        """3D 뷰에서 좌표축을 그립니다."""
        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0); glVertex3fv((0,0,0)); glVertex3fv((1,0,0))
        glColor3f(0.0, 1.0, 0.0); glVertex3fv((0,0,0)); glVertex3fv((0,1,0))
        glColor3f(0.0, 0.0, 1.0); glVertex3fv((0,0,0)); glVertex3fv((0,0,1))
        glEnd()

    def set_rotation_axis(self, axis):
        """회전 축을 설정합니다."""
        if axis in ['X', 'Y'] and self.rotation_axis != axis:
            self.rotation_axis = axis
            self.update()

    def set_num_slices(self, value):
        """단면 개수를 설정합니다."""
        if self.num_slices != value:
            self.num_slices = value
            self.update()

    def generate_sor_model(self):
        """SOR 모델 데이터를 생성합니다."""
        if not self.points or len(self.points) < 2:
            self.sor_vertices = []
            self.sor_faces = []
            return
        # TODO: 로직 구현
        self.update()

    def draw_sor_model(self):
        """생성된 SOR 모델을 그립니다."""
        if not self.sor_vertices:
            self.draw_axes()
            return
        # TODO: 로직 구현

    def set_view_mode(self, mode):
        """뷰 모드를 변경합니다."""
        if self.view_mode != mode:
            self.view_mode = mode
            self.update()
            self.viewModeChanged.emit(self.view_mode)
            if self.view_mode == '3D' and self.points:
                self.generate_sor_model()

    def clear_points(self):
        """모든 점을 지웁니다."""
        self.points.clear()
        self.sor_vertices = []
        self.sor_faces = []
        self.update()
        self.pointsChanged.emit()

    def delete_point(self, index):
        """지정된 인덱스의 점을 삭제합니다."""
        if 0 <= index < len(self.points):
            del self.points[index]
            self.update()
            self.pointsChanged.emit()