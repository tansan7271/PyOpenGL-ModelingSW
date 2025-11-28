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
        #--- 3D 모델 데이터 ---
        # self.paths: 각 경로는 {'points': [(x,y), ...], 'closed': True/False} 형태의 딕셔너리
        self.paths = [{'points': [], 'closed': False}]
        self.current_path_idx = 0 # 현재 편집 중인 경로의 인덱스
        self.dragging_point = None # 현재 드래그 중인 점의 정보 (path_idx, point_idx)
        
        self.sor_vertices = []  # 생성된 SOR 모델의 정점(vertex) 리스트
        self.sor_normals = []   # 생성된 SOR 모델의 법선(normal) 리스트 (조명용)
        self.sor_faces = []  # 생성된 SOR 모델의 면(face) 리스트
        
        #--- 3D 렌더링 설정 ---
        self.render_mode = 1 # 0: Wireframe, 1: Solid, 2: Flat, 3: Gouraud
        self.model_color = (0.0, 0.8, 0.8) # 기본 색상 (Cyan)
        self.projection_mode = 'Perspective' # 'Perspective' or 'Ortho'
        self.show_wireframe = True # 와이어프레임 토글 상태 (기본값 True)

    # === OpenGL Lifecycle Methods ===

    def initializeGL(self):
        """
        OpenGL이 처음 초기화될 때 한 번 호출됩니다.
        전역적인 OpenGL 상태(배경색, 깊이 테스트 등)를 설정합니다.
        """
        glClearColor(0.1, 0.1, 0.1, 1.0)  # 배경색을 어두운 회색으로 설정
        glEnable(GL_DEPTH_TEST)  # 깊이 테스트 활성화 (3D에서 앞뒤 구분)
        glPointSize(5.0)  # 2D 편집 시 점의 크기를 설정
        
        # 조명 및 재질 설정
        glEnable(GL_NORMALIZE) # 법선 벡터 정규화 (조명 계산 정확도 향상)
        glEnable(GL_COLOR_MATERIAL) # glColor가 재질 색상에 반영되도록 설정
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE) # 앞면의 Ambient와 Diffuse에 적용
        
        # 조명 설정은 paintGL에서 매 프레임 설정하거나, 
        # 뷰 변환 후에 설정해야 카메라/월드 기준이 명확해짐.
        # 여기서는 초기화만 수행.
        # Key Light (주 조명) - 우측 상단
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1.0))
        
        # Fill Light (보조 조명) - 좌측 상단, 약하게
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.4, 0.4, 0.4, 1.0))

    def resizeGL(self, w, h):
        """위젯의 크기가 조절될 때마다 호출됩니다. 뷰포트와 투영을 재설정합니다."""
        glViewport(0, 0, w, h)  # 뷰포트를 위젯 전체 크기로 설정
        self.setupProjection()  # 크기 변경에 맞춰 투영 행렬을 다시 계산

    def paintGL(self):
        """
        화면을 다시 그려야 할 때마다 호출되는 메인 렌더링 함수입니다.
        뷰 모드에 따라 적절한 그리기 함수들을 호출합니다.
        """
        try:
            # 1. 투영 행렬 설정
            self.setupProjection()
            
            # 2. 버퍼 초기화
            # 깊이 버퍼 쓰기를 활성화해야 깊이 버퍼가 제대로 지워짐 (Ghosting 방지)
            glDepthMask(GL_TRUE)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # 3. 모델뷰 행렬 초기화
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # 4. 뷰 모드에 따른 분기 렌더링
            # 4. 뷰 모드에 따른 분기 렌더링
            if self.view_mode == '2D':
                # 2D 렌더링에 필요한 상태 강제 설정 (Explicit State Setup)
                glDisable(GL_LIGHTING)
                glDisable(GL_CULL_FACE)
                glDisable(GL_DEPTH_TEST) # 2D에서는 깊이 테스트 불필요 (순서대로 그림)
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                
                self.draw_grid()
                self.draw_points()
                
            else:  # '3D'
                # 3D 렌더링에 필요한 상태 강제 설정
                glEnable(GL_DEPTH_TEST)
                
                # 3D 뷰의 카메라 위치와 방향 설정
                gluLookAt(10, 10, 20, 0, 0, 0, 0, 1, 0)
                
                # 조명 위치 설정 (카메라 변환 후, 모델 변환 전 = 월드 좌표계 고정)
                # Key Light: 우측 상단 전면 (100, 100, 100)
                glLightfv(GL_LIGHT0, GL_POSITION, (100, 100, 100, 1.0))
                
                # Fill Light: 좌측 상단 후면 (-100, 100, -100)
                glLightfv(GL_LIGHT1, GL_POSITION, (-100, 100, -100, 1.0))
                
                # SOR 모델 데이터가 있으면 모델을 그리고, 없으면 좌표축을 그림
                if self.sor_vertices:
                    self.draw_sor_model()
                else:
                    self.draw_axes()
        except Exception as e:
            print(f"paintGL Error: {e}")
            import traceback
            traceback.print_exc()

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
            # 3D 모드: 원근 투영(Perspective) 또는 직교 투영(Ortho)
            if self.projection_mode == 'Perspective':
                gluPerspective(45, aspect_ratio, 0.1, 100.0)
            else:
                # 3D Ortho 모드: 2D와 비슷하지만 Z축 깊이가 있음
                # 적절한 범위를 설정해야 함 (예: -10 ~ 10)
                scale = 10
                glOrtho(-scale * aspect_ratio, scale * aspect_ratio, -scale, scale, -100, 100)

    def mousePressEvent(self, event):
        """
        마우스 클릭 이벤트를 처리합니다.
        1. 점 드래그 시작 (기존 점 클릭 시)
        2. 새로운 점 추가
        """
        if self.view_mode == '2D':
            screen_x, screen_y = event.x(), event.y()
            gl_y = self.height() - screen_y
            
            world_x = self.ortho_left + (screen_x / self.width()) * (self.ortho_right - self.ortho_left)
            world_y = self.ortho_bottom + (gl_y / self.height()) * (self.ortho_top - self.ortho_bottom)
            
            snap_threshold = 0.3
            clicked_point = (world_x, world_y)
            
            # 1. 히트 테스트 (Hit Test) - 기존 점을 클릭했는지 확인
            for p_idx, path_data in enumerate(self.paths):
                path_points = path_data['points']
                for pt_idx, pt in enumerate(path_points):
                    dist = math.sqrt((pt[0] - world_x)**2 + (pt[1] - world_y)**2)
                    if dist < snap_threshold:
                        # 기존 점 클릭 -> 드래그 모드 시작
                        self.dragging_point = (p_idx, pt_idx)
                        return

            # 2. 새로운 점 추가
            # 드래그가 아니라면 현재 경로에 점 추가
            # 단, 현재 경로가 이미 닫혀있다면(closed=True), 새로운 경로를 시작해야 함 (close_current_path에서 처리됨)
            # 하지만 여기서는 close_current_path를 호출하지 않고 점만 추가함.
            # 사용자가 'Close Path' 버튼을 누르지 않았다면 계속 점을 추가할 수 있음.
            self.paths[self.current_path_idx]['points'].append(clicked_point)
            
            self.update()
            self.pointsChanged.emit()

    def mouseMoveEvent(self, event):
        """마우스 드래그 시 점의 위치를 실시간으로 업데이트합니다."""
        if self.view_mode == '2D' and self.dragging_point:
            screen_x, screen_y = event.x(), event.y()
            gl_y = self.height() - screen_y
            
            world_x = self.ortho_left + (screen_x / self.width()) * (self.ortho_right - self.ortho_left)
            world_y = self.ortho_bottom + (gl_y / self.height()) * (self.ortho_top - self.ortho_bottom)
            
            # 드래그 중인 점의 좌표 업데이트
            path_idx, pt_idx = self.dragging_point
            self.paths[path_idx]['points'][pt_idx] = (world_x, world_y)
            
            self.update()
            self.pointsChanged.emit()

    def mouseReleaseEvent(self, event):
        """마우스 버튼을 떼면 드래그 모드를 종료합니다."""
        if self.view_mode == '2D':
            self.dragging_point = None

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
        # 점과 선을 격자보다 앞에 그리기 위해 z값을 양수로 설정 (Z-fighting 방지)
        z_points = 0.1
        
        for path_data in self.paths:
            path = path_data['points']
            is_closed = path_data['closed']
            
            if not path:
                continue
                
            # 점이 2개 이상일 때, 점들을 잇는 흰색 선(프로파일 곡선)을 그립니다.
            if len(path) > 1:
                glColor3f(1.0, 1.0, 1.0) # 흰색
                if is_closed:
                    glBegin(GL_LINE_LOOP) # 닫힌 도형
                else:
                    glBegin(GL_LINE_STRIP) # 열린 도형
                    
                for p in path:
                    glVertex3f(p[0], p[1], z_points)
                glEnd()
                
            # 각 점을 노란색으로 그립니다.
            glColor3f(1.0, 1.0, 0.0) # 노란색
            glBegin(GL_POINTS)
            for p in path:
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
        """
        생성된 SOR 모델의 정점과 면 데이터를 사용하여 3D 모델을 그립니다.
        GL_QUADS를 사용하여 면을 구성하고, 기본적인 조명을 위한 법선 벡터(Normal Vector) 계산은
        추후 고도화 단계에서 고려합니다. 현재는 기하학적 형태를 확인하는 데 집중합니다.
        """
        if not self.sor_vertices or not self.sor_faces:
            self.draw_axes()
            return



        # 모델의 윤곽선을 더 잘 보이게 하기 위해 와이어프레임을 덧그립니다. (선택 사항)
        # 렌더링 모드에 따라 다르게 그림
        
        # 조명/재질 설정 초기화 (Explicit Reset)
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glShadeModel(GL_FLAT)

        # --- 1. 기본 모델 그리기 ---
        if self.render_mode == 0: # Wireframe
            # Wireframe 모드에서는 흰색 선으로 그림
            glColor3f(1.0, 1.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            self._draw_faces()
            
        elif self.render_mode == 1: # Solid (No Lighting)
            glColor3f(*self.model_color)
            self._draw_faces()
            
        elif self.render_mode == 2: # Flat Shading
            glEnable(GL_LIGHTING)
            glShadeModel(GL_FLAT)
            # 재질 설정은 GL_COLOR_MATERIAL 덕분에 glColor로 처리됨
            glColor3f(*self.model_color)
            self._draw_faces()
            
        elif self.render_mode == 3: # Gouraud Shading
            glEnable(GL_LIGHTING)
            glShadeModel(GL_SMOOTH)
            # 재질 설정은 GL_COLOR_MATERIAL 덕분에 glColor로 처리됨
            glColor3f(*self.model_color)
            self._draw_faces()

        # --- 2. 와이어프레임 오버레이 (옵션) ---
        # Wireframe 모드가 아니고, show_wireframe이 켜져있을 때만 덧그림
        if self.render_mode != 0 and self.show_wireframe:
            glDisable(GL_LIGHTING) # 조명 끄고
            glColor3f(1.0, 1.0, 1.0) # 흰색
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE) # 라인 모드
            
            # Z-fighting 방지를 위한 Polygon Offset
            glEnable(GL_POLYGON_OFFSET_LINE)
            glPolygonOffset(-1.0, -1.0)
            
            self._draw_faces()
            
            glDisable(GL_POLYGON_OFFSET_LINE)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL) # 다시 채우기 모드로 복구

    def _draw_faces(self):
        """실제 면을 그리는 내부 함수"""
        glBegin(GL_QUADS)
        for face in self.sor_faces:
            for vertex_idx in face:
                # 법선 벡터가 있으면 설정 (조명용)
                if vertex_idx < len(self.sor_normals):
                    nx, ny, nz = self.sor_normals[vertex_idx]
                    glNormal3f(nx, ny, nz)
                    
                v = self.sor_vertices[vertex_idx]
                glVertex3f(v[0], v[1], v[2])
        glEnd()

    # === Data Generation and Manipulation ===

    def generate_sor_model(self):
        """
        모든 2D 프로파일 경로(self.paths)를 기반으로 SOR 모델 데이터를 생성합니다.
        여러 개의 떨어진 도형도 모두 처리하여 하나의 모델로 합칩니다.
        """
        try:
            self.sor_vertices = []
            self.sor_normals = []
            self.sor_faces = []
            
            # 회전 각도 계산
            angle_step = 360.0 / self.num_slices
            
            # 현재까지 생성된 정점의 개수 (인덱스 오프셋용)
            vertex_offset = 0

            for path_data in self.paths:
                path = path_data['points']
                is_closed = path_data['closed']
                
                if len(path) < 2:
                    continue

                # --- 1. 정점 생성 (Vertices Generation) ---
                # 현재 경로(path)에 대한 정점 생성
                current_path_vertices_count = 0
                for i in range(self.num_slices):
                    theta = math.radians(i * angle_step)
                    cos_theta = math.cos(theta)
                    sin_theta = math.sin(theta)

                    for p in path:
                        x, y = p
                        if self.rotation_axis == 'Y':
                            nx, ny, nz = x * cos_theta, y, -x * sin_theta
                        else: # 'X'
                            nx, ny, nz = x, y * cos_theta, y * sin_theta
                        
                        self.sor_vertices.append((nx, ny, nz))
                        
                        # 법선 벡터 계산 (중심축에서 바깥쪽으로 향하는 벡터)
                        # 간단하게 (nx, ny, nz) 자체가 원점(또는 축)에서의 방향이므로 정규화하여 사용
                        # Y축 회전일 경우 (nx, 0, nz)가 법선 방향 (수평)
                        # X축 회전일 경우 (0, ny, nz)가 법선 방향
                        length = math.sqrt(nx*nx + ny*ny + nz*nz)
                        if length > 0:
                            if self.rotation_axis == 'Y':
                                # Y축 회전체: 법선은 XZ 평면상에서 바깥을 향함 + Y성분은 곡선의 기울기에 따라 달라짐
                                # 하지만 여기서는 간단히 구형/원통형 근사로 중심에서 뻗어나가는 방향 사용
                                # 좀 더 정확히 하려면 곡선의 접선 벡터와 회전 방향 벡터의 외적을 구해야 함.
                                # 일단은 간단한 쉐이딩을 위해 정점 위치 자체를 법선으로 사용 (구체 등에서는 정확함)
                                self.sor_normals.append((nx/length, ny/length, nz/length))
                            else:
                                self.sor_normals.append((nx/length, ny/length, nz/length))
                        else:
                            self.sor_normals.append((0, 1, 0)) # 기본값

                        current_path_vertices_count += 1

                # --- 2. 면 생성 (Faces Generation) ---
                num_points_in_path = len(path)
                
                # 연결해야 할 세그먼트 수: 닫힌 도형이면 점 개수만큼, 열린 도형이면 점 개수 - 1
                num_segments = num_points_in_path if is_closed else num_points_in_path - 1
                
                for i in range(self.num_slices):
                    for j in range(num_segments):
                        # 현재 단면(i)의 점 인덱스 (전체 정점 리스트 기준)
                        base_idx = vertex_offset
                        
                        p1 = base_idx + i * num_points_in_path + j
                        # j+1이 마지막 점을 넘어가면 0번 점으로 연결 (닫힌 도형의 경우)
                        p2_local_idx = (j + 1) % num_points_in_path
                        p2 = base_idx + i * num_points_in_path + p2_local_idx
                        
                        # 다음 단면(next_i)의 점 인덱스
                        next_i = (i + 1) % self.num_slices
                        p3 = base_idx + next_i * num_points_in_path + p2_local_idx
                        p4 = base_idx + next_i * num_points_in_path + j

                        self.sor_faces.append((p1, p4, p3, p2))
                
                # 다음 경로를 위해 정점 오프셋 업데이트
                vertex_offset += current_path_vertices_count
            
            self.update()
        except Exception as e:
            print(f"generate_sor_model Error: {e}")
            import traceback
            traceback.print_exc()

    def save_model(self, file_path):
        """
        현재 생성된 SOR 모델과 설정을 지정된 경로의 .dat 파일로 저장합니다.
        형식 v5 (Multi-path + Closed state + Render Settings):
        <단면 개수>
        <회전축 (0:X, 1:Y)>
        <렌더링 모드 (0~3)>
        <모델 색상 R G B>
        <경로 개수>
        <경로 0 점 개수>
        <경로 0 닫힘 여부 (0:Open, 1:Closed)>
        x y
        ...
        <3D 정점 개수>
        x y z
        ...
        <면 개수>
        <한 면의 점 개수> v1 v2 v3 ...
        ...
        """
        if not self.sor_vertices:
            return

        try:
            with open(file_path, 'w') as f:
                # 1. 설정 저장
                f.write(f"{self.num_slices}\n")
                f.write(f"{1 if self.rotation_axis == 'Y' else 0}\n") # Y=1, X=0
                
                # v5 추가: 렌더링 모드 및 색상
                f.write(f"{self.render_mode}\n")
                f.write(f"{self.model_color[0]:.6f} {self.model_color[1]:.6f} {self.model_color[2]:.6f}\n")
                
                # 2. 2D 경로 데이터 저장
                # 빈 경로는 저장하지 않음
                valid_paths = [p for p in self.paths if p['points']]
                f.write(f"{len(valid_paths)}\n")
                
                for path_data in valid_paths:
                    points = path_data['points']
                    is_closed = 1 if path_data['closed'] else 0
                    
                    f.write(f"{len(points)}\n")
                    f.write(f"{is_closed}\n") # 닫힘 여부 저장
                    
                    for p in points:
                        f.write(f"{p[0]:.6f} {p[1]:.6f}\n")

                # 3. 3D 정점 데이터 저장
                f.write(f"{len(self.sor_vertices)}\n")
                for v in self.sor_vertices:
                    f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                
                # 4. 면 데이터 저장
                f.write(f"{len(self.sor_faces)}\n")
                for face in self.sor_faces:
                    f.write(f"4 {face[0]} {face[1]} {face[2]} {face[3]}\n")
            print(f"모델 저장 완료: {file_path}")
        except Exception as e:
            print(f"모델 저장 실패: {e}")

    def load_model(self, file_path):
        """
        .dat 파일에서 설정, 2D 경로, 3D 모델 데이터를 모두 읽어와 복원합니다.
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
                idx = 0
                
                # 1. 설정 읽기
                self.num_slices = int(lines[idx].strip())
                idx += 1
                
                axis_val = int(lines[idx].strip())
                self.rotation_axis = 'Y' if axis_val == 1 else 'X'
                idx += 1
                
                # v5 추가: 렌더링 모드 및 색상 읽기 (하위 호환성 처리)
                # 다음 줄이 렌더링 모드(0~3)인지, 아니면 바로 경로 개수인지 확인해야 함.
                # v4 이하는 바로 경로 개수(정수)가 나옴.
                # 하지만 경로 개수도 정수이고 렌더링 모드도 정수라 구분이 모호할 수 있음.
                # 다행히 v4까지는 회전축 다음이 바로 경로 개수였음.
                # v5는 회전축 다음에 렌더링 모드, 그 다음에 색상(실수 3개)이 나옴.
                # 따라서 다음 줄을 읽고, 그 다음 줄이 실수 3개인지 확인하면 v5인지 알 수 있음.
                
                next_line = lines[idx].strip()
                next_next_line = lines[idx+1].strip() if idx+1 < len(lines) else ""
                
                is_v5 = False
                try:
                    parts = next_next_line.split()
                    if len(parts) == 3 and all('.' in p for p in parts):
                        is_v5 = True
                except:
                    pass
                    
                if is_v5:
                    self.render_mode = int(next_line)
                    idx += 1
                    color_parts = list(map(float, lines[idx].strip().split()))
                    self.model_color = tuple(color_parts)
                    idx += 1
                    
                    # 그 다음이 경로 개수
                    num_paths = int(lines[idx].strip())
                    idx += 1
                else:
                    # v4 이하: 렌더링 모드/색상 없음 (기본값 사용)
                    self.render_mode = 1 # Solid
                    self.model_color = (0.0, 0.8, 0.8)
                    num_paths = int(next_line)
                    idx += 1
                
                self.paths = []
                for _ in range(num_paths):
                    num_points = int(lines[idx].strip())
                    idx += 1
                    
                    # v4 포맷: 닫힘 여부 확인 (하위 호환성 고려)
                    is_closed = False
                    try:
                        line = lines[idx].strip()
                        parts = line.split()
                        if len(parts) == 1 and parts[0] in ['0', '1']:
                            is_closed = True if int(parts[0]) == 1 else False
                            idx += 1
                        else:
                            # v3 파일 (closed flag 없음)
                            pass
                    except:
                        pass

                    path_points = []
                    for _ in range(num_points):
                        coords = list(map(float, lines[idx].strip().split()))
                        path_points.append(tuple(coords))
                        idx += 1
                    
                    self.paths.append({'points': path_points, 'closed': is_closed})
                
                # 마지막에 빈 경로 하나 추가 (편집 편의성)
                self.paths.append({'points': [], 'closed': False})
                self.current_path_idx = len(self.paths) - 1
                
                # 3. 3D 정점 데이터 읽기
                num_vertices = int(lines[idx].strip())
                idx += 1
                
                new_vertices = []
                for _ in range(num_vertices):
                    coords = list(map(float, lines[idx].strip().split()))
                    new_vertices.append(tuple(coords))
                    idx += 1
                
                # 4. 면 데이터 읽기
                num_faces = int(lines[idx].strip())
                idx += 1
                
                new_faces = []
                for _ in range(num_faces):
                    data = list(map(int, lines[idx].strip().split()))
                    new_faces.append(tuple(data[1:]))
                    idx += 1
                
                # 데이터 교체
                self.sor_vertices = new_vertices
                self.sor_faces = new_faces
                
                # UI 및 화면 갱신 알림
                self.pointsChanged.emit()
                
                # 뷰 모드를 3D로 전환
                if self.view_mode == '2D':
                    self.view_mode = '3D'
                    self.viewModeChanged.emit('3D')
                
                self.update()
                print(f"모델 로드 완료: {file_path}")
                
        except Exception as e:
            print(f"모델 로드 실패: {e}")

    def clear_points(self):
        """모든 경로와 모델 데이터를 초기화합니다."""
        self.paths = [{'points': [], 'closed': False}]
        self.current_path_idx = 0
        self.dragging_point = None
        self.sor_vertices = []
        self.sor_faces = []
        self.update()
        self.pointsChanged.emit()

    def delete_point(self, path_idx, point_idx):
        """지정된 경로의 특정 점을 삭제합니다."""
        if 0 <= path_idx < len(self.paths):
            path_data = self.paths[path_idx]
            path_points = path_data['points']
            if 0 <= point_idx < len(path_points):
                del path_points[point_idx]
                
                # 점이 2개 미만이면 닫힘 상태 해제 (최소한 선분은 되어야 하므로)
                if len(path_points) < 2:
                    path_data['closed'] = False
                    
                self.update()
                self.pointsChanged.emit()

    def close_current_path(self):
        """현재 편집 중인 경로를 닫힌 도형으로 만들고, 새로운 경로를 시작합니다."""
        current_path = self.paths[self.current_path_idx]
        if len(current_path['points']) < 2:
            # 점이 2개 미만이면 닫을 수 없음 (최소한 선분은 되어야 함)
            return
            
        current_path['closed'] = True
        
        # 새로운 경로 시작
        self.paths.append({'points': [], 'closed': False})
        self.current_path_idx += 1
        
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
            # self.paths에 유효한 경로가 있는지 확인
            has_points = any(len(p['points']) > 1 for p in self.paths)
            if self.view_mode == '3D' and has_points:
                self.generate_sor_model()

            self.update() # 화면 갱신
            self.viewModeChanged.emit(self.view_mode) # 모드 변경 시그널 발생