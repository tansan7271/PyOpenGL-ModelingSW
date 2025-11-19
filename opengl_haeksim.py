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
    # 뷰 모드가 변경될 때 MainWindow에 알리기 위한 시그널
    viewModeChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- 위젯 상태 변수 ---
        self.view_mode = '2D'       # 현재 뷰 모드 ('2D' 또는 '3D')
        self.points = []            # 사용자가 찍은 2D 프로파일 점들의 리스트

        # --- 2D 뷰포트 관련 변수 ---
        self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top = -10, 10, -10, 10
        
        # --- SOR 모델 데이터 ---
        self.num_slices = 30        # 회전체의 단면 개수
        self.rotation_axis = 'Y'    # 회전 축 ('X' 또는 'Y')
        self.sor_vertices = []      # 생성된 SOR 모델의 3D 정점(vertex) 데이터
        self.sor_faces = []         # 생성된 SOR 모델의 면(face) 데이터

    def initializeGL(self):
        """
        OpenGL 환경이 처음 생성될 때 한 번 호출되어 기본 상태를 설정합니다.
        - 배경색, 깊이 테스트 활성화, 2D 점의 크기 등을 설정합니다.
        """
        glClearColor(0.1, 0.1, 0.1, 1.0)  # 검은색에 가까운 회색 배경
        glEnable(GL_DEPTH_TEST)           # 깊이 테스트를 활성화하여 3D 객체의 앞뒤 관계를 올바르게 처리
        glPointSize(5.0)                  # 2D 편집 시 점 크기를 5px로 설정

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
        """
        화면을 다시 그려야 할 때마다 호출되는 메인 렌더링 함수입니다.
        화면을 지우고, 현재 뷰 모드에 맞는 그리기 함수들을 호출합니다.
        """
        self.setupProjection() # 매번 그릴 때마다 현재 모드에 맞는 투영을 다시 설정

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        if self.view_mode == '2D':
            self.draw_grid()
            self.draw_points()
        else: # '3D'
            # 3D 뷰의 기본 카메라 위치와 바라보는 지점, 상향 벡터를 설정합니다.
            gluLookAt(3, 3, 5, 0, 0, 0, 0, 1, 0)
            
            # SOR 모델 데이터가 있으면 모델을 그리고, 없으면 3D 좌표축을 그립니다.
            if self.sor_vertices:
                self.draw_sor_model()
            else:
                self.draw_axes()

    def resizeGL(self, w, h):
        """위젯의 크기가 변경될 때 호출되며, OpenGL 뷰포트를 위젯 크기에 맞게 재설정합니다."""
        glViewport(0, 0, w, h)
        self.setupProjection()
        
    def mousePressEvent(self, event):
        """2D 모드에서 마우스 클릭 시, 화면 좌표를 월드 좌표로 변환하여 점을 추가합니다."""
        if self.view_mode == '2D':
            screen_x, screen_y = event.x(), event.y()
            # PyQt의 y좌표(위->아래)를 OpenGL의 y좌표(아래->위)로 변환합니다.
            gl_y = self.height() - screen_y
            
            # 화면 좌표를 glOrtho로 설정된 월드 좌표계로 변환합니다.
            world_x = self.ortho_left + (screen_x / self.width()) * (self.ortho_right - self.ortho_left)
            world_y = self.ortho_bottom + (gl_y / self.height()) * (self.ortho_top - self.ortho_bottom)
            
            self.points.append((world_x, world_y))
            print(f"점 추가됨: ({world_x:.2f}, {world_y:.2f})")
            self.update() # QOpenGLWidget에 다시 그리기를 요청합니다.

    def draw_grid(self):
        """2D 편집 모드에서 배경에 격자와 기준 축을 그립니다."""
        x_start, x_end = math.floor(self.ortho_left), math.ceil(self.ortho_right)
        y_start, y_end = math.floor(self.ortho_bottom), math.ceil(self.ortho_top)
        
        # Z-Fighting 현상(깊이가 같은 두 객체가 번갈아 그려지는 문제)을 피하기 위해
        # 격자는 점/선보다 뒤쪽(z = -0.1)에 그립니다.
        z_grid = -0.1

        # 일반 격자선 (회색)
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for i in range(x_start, x_end + 1):
            if i == 0: continue # 축은 별도로 강조하여 그립니다.
            glVertex3f(i, y_start, z_grid)
            glVertex3f(i, y_end, z_grid)
        for i in range(y_start, y_end + 1):
            if i == 0: continue # 축은 별도로 강조하여 그립니다.
            glVertex3f(x_start, i, z_grid)
            glVertex3f(x_end, i, z_grid)
        glEnd()

        # 강조된 기준 축 (X:빨강, Y:초록)
        glColor3f(1.0, 0.0, 0.0) # X축 (y=0)
        glBegin(GL_LINES)
        glVertex3f(x_start, 0, z_grid)
        glVertex3f(x_end, 0, z_grid)
        glEnd()

        glColor3f(0.0, 1.0, 0.0) # Y축 (x=0)
        glBegin(GL_LINES)
        glVertex3f(0, y_start, z_grid)
        glVertex3f(0, y_end, z_grid)
        glEnd()

    def draw_points(self):
        """
        사용자가 추가한 점들과 그 점들을 잇는 프로파일 곡선을 그립니다.
        격자보다 앞에 보이도록 z값을 0.1로 설정하여 Z-Fighting을 방지합니다.
        """
        z_points = 0.1

        if len(self.points) > 1:
            glColor3f(1.0, 1.0, 1.0) # 프로파일 곡선 (흰색)
            glBegin(GL_LINE_STRIP)
            for p in self.points:
                glVertex3f(p[0], p[1], z_points)
            glEnd()

        glColor3f(1.0, 1.0, 0.0) # 점 (노란색)
        glBegin(GL_POINTS)
        for p in self.points:
            glVertex3f(p[0], p[1], z_points)
        glEnd()


    def draw_axes(self):
        """3D 뷰에서 R,G,B 색상의 X,Y,Z 좌표축을 그립니다."""
        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0); glVertex3fv((0,0,0)); glVertex3fv((1,0,0)) # X축 (빨간색)
        glColor3f(0.0, 1.0, 0.0); glVertex3fv((0,0,0)); glVertex3fv((0,1,0)) # Y축 (초록색)
        glColor3f(0.0, 0.0, 1.0); glVertex3fv((0,0,0)); glVertex3fv((0,0,1)) # Z축 (파란색)
        glEnd()

    def set_rotation_axis(self, axis):
        """SOR 모델의 회전 축('X' 또는 'Y')을 설정하고, 필요시 모델을 다시 생성합니다."""
        if axis in ['X', 'Y'] and self.rotation_axis != axis:
            self.rotation_axis = axis
            print(f"회전 축 변경: {self.rotation_axis}")
            if self.view_mode == '3D' and self.points:
                self.generate_sor_model()
            else:
                self.update()

    def set_num_slices(self, value):
        """SOR 모델의 단면 개수를 설정하고, 필요시 모델을 다시 생성합니다."""
        if self.num_slices != value:
            self.num_slices = value
            print(f"단면 개수 변경: {self.num_slices}")
            if self.view_mode == '3D' and self.points:
                self.generate_sor_model()
            else:
                self.update()

    def generate_sor_model(self):
        """self.points를 기반으로 SOR 모델의 정점과 면 데이터를 생성합니다. (현재는 플레이스홀더)"""
        if not self.points or len(self.points) < 2:
            self.sor_vertices = []
            self.sor_faces = []
            return

        self.sor_vertices = []
        self.sor_faces = []
        print(f"{len(self.points)}개의 점과 {self.num_slices}개의 단면으로 SOR 모델 생성 중...")
        # TODO: 실제 SOR 모델 생성 로직 구현
        self.update()

    def draw_sor_model(self):
        """생성된 SOR 모델을 그립니다. (현재는 플레이스홀더)"""
        if not self.sor_vertices:
            self.draw_axes()
            return
        # TODO: 실제 SOR 모델 렌더링 로직 구현 (glBegin/glEnd 또는 VBO 사용)
        print("SOR 모델 그리기 (플레이스홀더)...")

    def set_view_mode(self, mode):
        """뷰 모드를 '2D' 또는 '3D'로 변경하고, 3D 전환 시 모델 생성을 시도합니다."""
        if self.view_mode != mode:
            self.view_mode = mode
            self.update()
            print(f"뷰 모드 변경: {mode}")
            self.viewModeChanged.emit(self.view_mode)
            
            if self.view_mode == '3D' and self.points:
                self.generate_sor_model()

    def clear_points(self):
        """사용자가 찍은 모든 점과 관련 모델 데이터를 초기화합니다."""
        self.points.clear()
        self.sor_vertices = []
        self.sor_faces = []
        print("모든 점과 SOR 모델이 초기화되었습니다.")
        self.update()