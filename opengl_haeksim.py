# -*- coding: utf-8 -*-
"""
PyOpenGL SOR Modeler의 핵심 OpenGL 렌더링 위젯

이 파일은 PyQt5의 QOpenGLWidget을 상속받아 실제 그래픽 렌더링을 담당하는
OpenGLWidget 클래스를 정의합니다. 2D 프로파일 곡선 편집과 3D SOR 모델 뷰를
위한 모든 그래픽 처리, 사용자 입력(마우스), 3D 데이터 관리 및 생성을 담당합니다.
"""

import math
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import pyqtSignal

# PyOpenGL에서 OpenGL 함수들을 직접 사용하기 위해 import 합니다.
# 'import *'는 일반적으로 권장되지 않지만, PyOpenGL에서는 gl* 형태의 함수를
# 간결하게 사용하기 위한 관례적인 방법입니다.
from OpenGL.GL import *
from OpenGL.GLU import *

class OpenGLWidget(QOpenGLWidget):
    """
    PyQt5의 QOpenGLWidget을 상속받아 OpenGL 렌더링을 수행하는 핵심 위젯입니다.
    2D 프로파일 편집 모드와 3D 모델 뷰 모드를 가지며, 모든 그래픽 처리 및 사용자 입력을 담당합니다.
    """
    #--- 시그널 정의 ---
    # 뷰 모드가 변경될 때 ('2D' 또는 '3D') MainWindow에 알리는 시그널
    viewModeChanged = pyqtSignal(str)
    # 점 목록이 추가, 삭제, 초기화될 때 MainWindow에 알려 UI를 갱신하게 하는 시그널
    pointsChanged = pyqtSignal()

    def __init__(self, parent=None):
        """OpenGLWidget의 생성자입니다. 각종 상태 변수와 모델 데이터를 초기화합니다."""
        super().__init__(parent)
        
        #--- 상태 변수 ---
        self.view_mode = '2D'  # 현재 뷰 모드 ('2D' 또는 '3D')
        self.rotation_axis = 'Y'  # SOR 모델 생성 시 사용할 회전 축 ('X' 또는 'Y')
        self.num_slices = 30  # SOR 모델의 단면 개수
        
        #--- 2D/3D 투영 관련 변수 ---
        # 2D 직교 투영(Orthographic projection)의 좌우상하 경계
        self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top = -10, 10, -10, 10
        
        #--- 3D 모델 데이터 ---
        self.points = []  # 사용자가 찍은 2D 프로파일 점 (x, y) 튜플의 리스트
        self.sor_vertices = []  # 생성된 SOR 모델의 정점(vertex) 리스트
        self.sor_faces = []  # 생성된 SOR 모델의 면(face) 리스트

    # === OpenGL Lifecycle Methods ===

    def initializeGL(self):
        """
        OpenGL이 처음 초기화될 때 한 번 호출됩니다.
        전역적인 OpenGL 상태(배경색, 깊이 테스트 등)를 설정합니다.
        """
        glClearColor(0.1, 0.1, 0.1, 1.0)  # 배경색을 어두운 회색으로 설정
        glEnable(GL_DEPTH_TEST)  # 깊이 테스트 활성화 (3D에서 앞뒤 구분)
        glPointSize(5.0)  # 2D 편집 시 점의 크기를 설정

    def resizeGL(self, w, h):
        """위젯의 크기가 조절될 때마다 호출됩니다. 뷰포트와 투영을 재설정합니다."""
        glViewport(0, 0, w, h)  # 뷰포트를 위젯 전체 크기로 설정
        self.setupProjection()  # 크기 변경에 맞춰 투영 행렬을 다시 계산

    def paintGL(self):
        """
        화면을 다시 그려야 할 때마다 호출되는 메인 렌더링 함수입니다.
        뷰 모드에 따라 적절한 그리기 함수들을 호출합니다.
        """
        # 1. 투영 행렬 설정
        self.setupProjection()
        
        # 2. 버퍼 초기화
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # 3. 모델뷰 행렬 초기화
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # 4. 뷰 모드에 따른 분기 렌더링
        if self.view_mode == '2D':
            self.draw_grid()
            self.draw_points()
        else:  # '3D'
            # 3D 뷰의 카메라 위치와 방향 설정 (원점을 바라봄)
            gluLookAt(3, 3, 5, 0, 0, 0, 0, 1, 0)
            
            # SOR 모델 데이터가 있으면 모델을 그리고, 없으면 좌표축을 그림
            if self.sor_vertices:
                self.draw_sor_model()
            else:
                self.draw_axes()

    # === Core Logic Methods ===

    def setupProjection(self):
        """
        현재 뷰 모드에 따라 투영(Projection) 행렬을 설정합니다.
        이는 3D 공간의 객체들을 2D 화면에 어떻게 보여줄지 결정하는 중요한 단계입니다.
        """
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        w, h = self.width(), self.height()
        if h == 0: h = 1
        aspect_ratio = w / h  # 화면의 종횡비

        if self.view_mode == '2D':
            # 2D 모드: 직교 투영(Orthographic Projection) 사용.
            # 원근감이 없어 모든 객체가 크기 그대로 평평하게 보입니다. 2D 편집에 적합합니다.
            # 창 크기 변경 시 종횡비가 유지되도록 좌우 경계를 조정합니다.
            self.ortho_left = -10 * aspect_ratio
            self.ortho_right = 10 * aspect_ratio
            self.ortho_bottom = -10
            self.ortho_top = 10
            glOrtho(self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top, -1, 1)
        else:  # '3D'
            # 3D 모드: 원근 투영(Perspective Projection) 사용.
            # 멀리 있는 것은 작게, 가까이 있는 것은 크게 보여 현실감을 더합니다.
            # (시야각 45도, 종횡비, 근접 클리핑 평면, 원거리 클리핑 평면)
            gluPerspective(45, aspect_ratio, 0.1, 100.0)

    def mousePressEvent(self, event):
        """2D 모드에서 마우스 클릭 시, 화면 좌표를 OpenGL 월드 좌표로 변환하여 점을 추가합니다."""
        if self.view_mode == '2D':
            # 1. Qt의 화면 좌표(좌상단 0,0)를 가져옵니다.
            screen_x, screen_y = event.x(), event.y()
            
            # 2. OpenGL의 좌표계(좌하단 0,0)에 맞게 y값을 뒤집어줍니다.
            gl_y = self.height() - screen_y
            
            # 3. 화면상의 비율을 이용해 현재 ortho 범위 내의 월드 좌표로 변환합니다. (선형 보간)
            world_x = self.ortho_left + (screen_x / self.width()) * (self.ortho_right - self.ortho_left)
            world_y = self.ortho_bottom + (gl_y / self.height()) * (self.ortho_top - self.ortho_bottom)
            
            self.points.append((world_x, world_y))
            
            # 4. 위젯을 다시 그리도록 요청하고, 점 목록 변경 시그널을 보냅니다.
            self.update()
            self.pointsChanged.emit()

    # === Drawing Helper Methods ===

    def draw_grid(self):
        """2D 편집 모드에서 배경에 격자와 기준 축을 그립니다."""
        # 격자 선을 프로파일 곡선보다 뒤에 그리기 위해 z값을 약간 음수로 설정 (Z-fighting 방지)
        z_grid = -0.1
        
        # 현재 뷰포트 크기에 맞춰 격자의 범위를 동적으로 계산
        x_start, x_end = math.floor(self.ortho_left), math.ceil(self.ortho_right)
        y_start, y_end = math.floor(self.ortho_bottom), math.ceil(self.ortho_top)
        
        # 회색 격자선 그리기
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for i in range(x_start, x_end + 1):
            if i == 0: continue # 축선은 따로 그리므로 건너뜀
            glVertex3f(i, y_start, z_grid)
            glVertex3f(i, y_end, z_grid)
        for i in range(y_start, y_end + 1):
            if i == 0: continue
            glVertex3f(x_start, i, z_grid)
            glVertex3f(x_end, i, z_grid)
        glEnd()

        # X축(빨강), Y축(초록) 그리기
        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(x_start, 0, z_grid)
        glVertex3f(x_end, 0, z_grid)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, y_start, z_grid)
        glVertex3f(0, y_end, z_grid)
        glEnd()

    def draw_points(self):
        """사용자가 추가한 점들과 그 점들을 잇는 프로파일 곡선을 그립니다."""
        if not self.points:
            return
            
        # 점과 선을 격자보다 앞에 그리기 위해 z값을 양수로 설정 (Z-fighting 방지)
        z_points = 0.1
        
        # 점이 2개 이상일 때, 점들을 잇는 흰색 선(프로파일 곡선)을 그립니다.
        if len(self.points) > 1:
            glColor3f(1.0, 1.0, 1.0) # 흰색
            glBegin(GL_LINE_STRIP)
            for p in self.points:
                glVertex3f(p[0], p[1], z_points)
            glEnd()
            
        # 각 점을 노란색으로 그립니다.
        glColor3f(1.0, 1.0, 0.0) # 노란색
        glBegin(GL_POINTS)
        for p in self.points:
            glVertex3f(p[0], p[1], z_points)
        glEnd()

    def draw_axes(self):
        """3D 뷰에서 원점에 R,G,B 색상의 X,Y,Z 좌표축을 그립니다."""
        glBegin(GL_LINES)
        # X축 (빨강)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(1, 0, 0)
        # Y축 (초록)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 1, 0)
        # Z축 (파랑)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 1)
        glEnd()

    def draw_sor_model(self):
        """생성된 SOR 모델의 정점과 면 데이터를 사용하여 3D 모델을 그립니다."""
        if not self.sor_vertices:
            self.draw_axes()
            return
        # TODO: [구현 필요] self.sor_vertices와 self.sor_faces를 사용하여
        # glBegin(GL_TRIANGLES) 또는 glBegin(GL_QUADS)로 모델을 렌더링하는 로직.

    # === Data Generation and Manipulation ===

    def generate_sor_model(self):
        """2D 프로파일 곡선(self.points)을 기반으로 SOR 모델 데이터를 생성합니다."""
        if not self.points or len(self.points) < 2:
            self.sor_vertices = []
            self.sor_faces = []
            return
        # TODO: [구현 필요] self.points를 self.rotation_axis를 기준으로 회전시켜
        # self.sor_vertices와 self.sor_faces를 채우는 핵심 로직.
        
        self.update()

    def clear_points(self):
        """모든 점과 생성된 SOR 모델 데이터를 초기화합니다."""
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

    # === Public Setters / Slots ===

    def set_rotation_axis(self, axis):
        """UI로부터 호출되어 회전 축('X' 또는 'Y')을 설정합니다."""
        if axis in ['X', 'Y'] and self.rotation_axis != axis:
            self.rotation_axis = axis
            # 축이 변경되면 3D 모델을 다시 생성해야 할 수 있으므로 업데이트
            if self.view_mode == '3D':
                self.generate_sor_model()
            self.update()

    def set_num_slices(self, value):
        """UI로부터 호출되어 단면 개수를 설정합니다."""
        if self.num_slices != value:
            self.num_slices = value
            # 단면 개수가 변경되면 3D 모델을 다시 생성해야 할 수 있으므로 업데이트
            if self.view_mode == '3D':
                self.generate_sor_model()
            self.update()

    def set_view_mode(self, mode):
        """UI로부터 호출되어 뷰 모드('2D' 또는 '3D')를 변경합니다."""
        if self.view_mode != mode:
            self.view_mode = mode
            
            # 3D 모드로 전환될 때, 점 데이터가 있으면 SOR 모델 생성을 시도합니다.
            if self.view_mode == '3D' and self.points:
                self.generate_sor_model()

            self.update() # 화면 갱신
            self.viewModeChanged.emit(self.view_mode) # 모드 변경 시그널 발생