# -*- coding: utf-8 -*-
"""
PyOpenGL SOR & Sweep Modeler의 핵심 OpenGL 렌더링 위젯

이 파일은 PyQt5의 QOpenGLWidget을 상속받아 실제 그래픽 렌더링을 담당하는
OpenGLWidget 클래스를 정의합니다. 2D 프로파일 곡선 편집, 3D SOR/Sweep 모델 생성,
사용자 입력(마우스/키보드) 처리, 데이터 관리 및 파일 입출력을 담당합니다.
"""

import math
import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPainter, QColor, QFont
from OpenGL.GL import *
from OpenGL.GLU import *

class OpenGLWidget(QOpenGLWidget):
    """
    OpenGL 렌더링 및 모델링 로직을 담당하는 핵심 위젯 클래스입니다.
    
    주요 기능:
    - 2D 프로파일 편집 (점 추가, 이동, 삭제)
    - 3D 모델 생성 (SOR: 회전체, Sweep: 스윕 곡면)
    - 3D 뷰 네비게이션 (Orbit, Zoom)
    - 파일 입출력 (.dat 포맷 v6)
    """
    
    # --- 시그널 (Signals) ---
    # 뷰 모드가 변경될 때 ('2D' 또는 '3D') MainWindow에 알림
    viewModeChanged = pyqtSignal(str)
    # 점 데이터가 변경될 때 (추가/삭제/이동/로드) MainWindow에 알림 (UI 갱신용)
    pointsChanged = pyqtSignal()

    def __init__(self, parent=None):
        """생성자: 초기 상태 변수 및 데이터 구조 초기화"""
        super().__init__(parent)
        
        # --- 뷰 상태 (View State) ---
        self.view_mode = '2D'  # 현재 뷰 모드 ('2D' 또는 '3D')
        
        # --- 2D 투영 설정 (2D Projection Settings) ---
        self.ortho_left = -10
        self.ortho_right = 10
        self.ortho_bottom = -10
        self.ortho_top = 10
        
        # --- 3D 카메라 상태 (3D Camera State) ---
        self.cam_radius = 20.0 # 카메라 거리 (Zoom)
        self.cam_theta = 45.0  # 방위각 (Azimuth)
        self.cam_phi = 45.0    # 고도각 (Elevation)
        self.last_mouse_pos = None # 마우스 드래그 처리를 위한 이전 위치 저장
        
        # --- 모델링 데이터 (Modeling Data - Input) ---
        # 다중 경로 지원: [{'points': [(x,y), ...], 'closed': bool}, ...]
        self.paths = [{'points': [], 'closed': False}]
        self.current_path_idx = 0 # 현재 편집 중인 경로 인덱스
        self.dragging_point = None # 드래그 중인 점 정보 (path_idx, point_idx)
        
        # --- 모델링 파라미터 (Modeling Parameters) ---
        # 1. SOR (Surface of Revolution)
        self.rotation_axis = 'Y' # 회전 축 ('X' 또는 'Y')
        self.num_slices = 30     # 회전 분할 수
        
        # 2. Sweep Surface
        self.modeling_mode = 0   # 0: SOR, 1: Sweep
        self.sweep_length = 10.0 # 스윕 길이
        self.sweep_twist = 0.0   # 스윕 비틀림 각도 (도)
        self.sweep_caps = False  # 양 끝 닫기 여부
        
        # --- 생성된 3D 모델 데이터 (Generated 3D Model Data) ---
        self.sor_vertices = [] # 3D 정점 리스트 [(x,y,z), ...]
        self.sor_normals = []  # 정점 법선 리스트 [(nx,ny,nz), ...]
        self.sor_faces = []    # 면 리스트 [[v1, v2, v3, ...], ...]
        
        # --- 렌더링 설정 (Rendering Settings) ---
        self.render_mode = 1         # 0: Wireframe, 1: Solid, 2: Flat, 3: Gouraud
        self.model_color = (0.0, 0.8, 0.8) # 모델 색상 (Cyan)
        self.projection_mode = 'Perspective' # 'Perspective' or 'Ortho'
        self.show_wireframe = True   # 와이어프레임 오버레이 여부

        # --- GPU 가속 설정 (GPU Acceleration / VBO) ---
        self.use_gpu_acceleration = True  # GPU 가속 사용 여부
        self.vbo_initialized = False      # VBO 초기화 여부
        self.vbo_quad_vertices = None     # Quad 정점 VBO
        self.vbo_quad_normals = None      # Quad 법선 VBO (Gouraud)
        self.vbo_quad_flat_normals = None # Quad 법선 VBO (Flat)
        self.quad_vertex_count = 0        # Quad 정점 수
        self.vbo_tri_vertices = None      # Triangle 정점 VBO
        self.vbo_tri_normals = None       # Triangle 법선 VBO (Gouraud)
        self.vbo_tri_flat_normals = None  # Triangle 법선 VBO (Flat)
        self.tri_vertex_count = 0         # Triangle 정점 수

    # =========================================================================
    # OpenGL 생명주기 메서드 (OpenGL Lifecycle Methods)
    # =========================================================================

    def initializeGL(self):
        """OpenGL 초기화: 최초 1회 호출되어 기본 상태를 설정합니다."""
        glClearColor(0.1, 0.1, 0.1, 1.0) # 배경색: 어두운 회색
        glEnable(GL_DEPTH_TEST)          # 깊이 테스트 활성화
        glPointSize(5.0)                 # 점 크기 설정 (2D 편집용)
        
        # 조명 및 재질 기본 설정
        glEnable(GL_NORMALIZE) # 법선 정규화 (스케일 변환 시 조명 유지)
        glEnable(GL_COLOR_MATERIAL) # glColor로 재질 색상 제어
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
        
        # 조명 활성화 (Light0: Key, Light1: Fill)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        
        # 조명 속성 설정 (위치는 paintGL에서 설정)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1.0))
        
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.4, 0.4, 0.4, 1.0))

    def resizeGL(self, w, h):
        """위젯 크기 변경 시 호출: 뷰포트 및 투영 행렬 재설정"""
        glViewport(0, 0, w, h)
        self.setupProjection()

    def paintGL(self):
        """렌더링 루프: 매 프레임 화면을 그립니다."""
        try:
            # 1. 투영 행렬 설정
            self.setupProjection()
            
            # 2. 버퍼 초기화
            glDepthMask(GL_TRUE)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # 3. 모델뷰 행렬 초기화
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # 4. 모드별 렌더링
            if self.view_mode == '2D':
                self._render_2d_scene()
            else:
                self._render_3d_scene()
                
                # 5. 3D 안내 텍스트 오버레이 (QPainter 사용)
                # QPainter는 OpenGL 렌더링이 끝난 후 호출해야 함
                painter = QPainter(self)
                painter.setRenderHint(QPainter.TextAntialiasing)
                
                # 스타일 설정 (Maze Game 타이틀 힌트와 유사한 스타일)
                painter.setPen(QColor(200, 200, 200)) # 밝은 회색
                font = QFont("Arial", 10)
                font.setItalic(True)
                painter.setFont(font)
                
                # 텍스트 배치 (우측 상단, 여백 20px)
                # 줄바꿈(\n)을 사용하여 한 번에 그리기
                rect = self.rect().adjusted(0, 20, -20, 0) # 상단 20px, 우측 20px 여백
                text = "Drag to Look Around\nScroll to Zoom In/Out"
                painter.drawText(rect, Qt.AlignTop | Qt.AlignRight, text)
                
                painter.end()
                
        except Exception as e:
            print(f"paintGL Error: {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # 렌더링 로직 (Rendering Logic)
    # =========================================================================

    def setupProjection(self):
        """현재 뷰 모드와 창 크기에 맞춰 투영 행렬을 설정합니다."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        w, h = self.width(), self.height()
        if h == 0: h = 1
        aspect_ratio = w / h

        if self.view_mode == '2D':
            # 2D: 직교 투영 (Orthographic) - 종횡비 유지
            self.ortho_left = -10 * aspect_ratio
            self.ortho_right = 10 * aspect_ratio
            self.ortho_bottom = -10
            self.ortho_top = 10
            glOrtho(self.ortho_left, self.ortho_right, self.ortho_bottom, self.ortho_top, -1, 1)
        else:
            # 3D: 원근(Perspective) 또는 직교(Ortho) 투영
            if self.projection_mode == 'Perspective':
                gluPerspective(45, aspect_ratio, 0.1, 100.0)
            else:
                scale = self.cam_radius * 0.5
                glOrtho(-scale * aspect_ratio, scale * aspect_ratio, -scale, scale, -100, 100)

    def _render_2d_scene(self):
        """2D 편집 모드 렌더링"""
        # 2D용 상태 설정
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glDisable(GL_DEPTH_TEST)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        
        self.draw_grid()   # 배경 격자
        self.draw_points() # 프로파일 점 및 선

    def _render_3d_scene(self):
        """3D 뷰 모드 렌더링"""
        # 3D용 상태 설정
        glEnable(GL_DEPTH_TEST)
        
        # 카메라 설정 (Orbit Control)
        rad_theta = math.radians(self.cam_theta)
        rad_phi = math.radians(self.cam_phi)
        
        eye_x = self.cam_radius * math.sin(rad_phi) * math.cos(rad_theta)
        eye_y = self.cam_radius * math.cos(rad_phi)
        eye_z = self.cam_radius * math.sin(rad_phi) * math.sin(rad_theta)
        
        gluLookAt(eye_x, eye_y, eye_z, 0, 0, 0, 0, 1, 0)
        
        # 조명 위치 설정 (View Matrix 적용 후 = World Space 고정)
        glLightfv(GL_LIGHT0, GL_POSITION, (100, 100, 100, 1.0))   # Key Light
        glLightfv(GL_LIGHT1, GL_POSITION, (-100, -100, -100, 1.0)) # Fill Light
        
        self.draw_world_grid() # 바닥 그리드
        
        if self.sor_vertices:
            self.draw_model() # 생성된 모델
        else:
            self.draw_axes()  # 모델 없으면 축만 표시

    def draw_grid(self):
        """2D 배경 격자 그리기"""
        z_grid = -0.1
        x_start, x_end = math.floor(self.ortho_left), math.ceil(self.ortho_right)
        y_start, y_end = math.floor(self.ortho_bottom), math.ceil(self.ortho_top)
        
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for i in range(x_start, x_end + 1):
            if i == 0: continue
            glVertex3f(i, y_start, z_grid); glVertex3f(i, y_end, z_grid)
        for i in range(y_start, y_end + 1):
            if i == 0: continue
            glVertex3f(x_start, i, z_grid); glVertex3f(x_end, i, z_grid)
        glEnd()

        # 축 그리기
        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0); glVertex3f(x_start, 0, z_grid); glVertex3f(x_end, 0, z_grid) # X축
        glColor3f(0.0, 1.0, 0.0); glVertex3f(0, y_start, z_grid); glVertex3f(0, y_end, z_grid) # Y축
        glEnd()

    def draw_points(self):
        """2D 프로파일 점과 선 그리기"""
        z_points = 0.1
        
        for path_data in self.paths:
            path = path_data['points']
            is_closed = path_data['closed']
            if not path: continue
                
            # 선 그리기
            if len(path) > 1:
                glColor3f(1.0, 1.0, 1.0)
                glBegin(GL_LINE_LOOP if is_closed else GL_LINE_STRIP)
                for p in path: glVertex3f(p[0], p[1], z_points)
                glEnd()
                
            # 점 그리기
            glColor3f(1.0, 1.0, 0.0)
            glBegin(GL_POINTS)
            for p in path: glVertex3f(p[0], p[1], z_points)
            glEnd()

    def draw_axes(self):
        """3D 좌표축 그리기 (R,G,B)"""
        glBegin(GL_LINES)
        glColor3f(1, 0, 0); glVertex3f(0,0,0); glVertex3f(1,0,0) # X
        glColor3f(0, 1, 0); glVertex3f(0,0,0); glVertex3f(0,1,0) # Y
        glColor3f(0, 0, 1); glVertex3f(0,0,0); glVertex3f(0,0,1) # Z
        glEnd()

    def draw_world_grid(self):
        """3D 바닥 격자 그리기"""
        y_floor = -10.0
        grid_size = 20
        step = 2
        
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for i in range(-grid_size, grid_size + 1, step):
            glVertex3f(-grid_size, y_floor, i); glVertex3f(grid_size, y_floor, i) # X방향
            glVertex3f(i, y_floor, -grid_size); glVertex3f(i, y_floor, grid_size) # Z방향
        glEnd()

    def draw_model(self):
        """3D 모델 렌더링 (Solid, Wireframe, Shading)"""
        if not self.sor_vertices: return

        # VBO 또는 레거시 렌더링 선택
        use_vbo = self.use_gpu_acceleration and self.vbo_initialized
        draw_func = self._draw_faces_vbo if use_vbo else self._draw_faces

        # 렌더링 모드 설정
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glShadeModel(GL_FLAT)

        if self.render_mode == 0: # Wireframe
            glColor3f(1.0, 1.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            draw_func()

        elif self.render_mode == 1: # Solid
            glColor3f(*self.model_color)
            draw_func()

        elif self.render_mode == 2: # Flat Shading
            glEnable(GL_LIGHTING)
            glShadeModel(GL_FLAT)
            glColor3f(*self.model_color)
            draw_func()

        elif self.render_mode == 3: # Gouraud Shading
            glEnable(GL_LIGHTING)
            glShadeModel(GL_SMOOTH)
            glColor3f(*self.model_color)
            draw_func()

        # Wireframe Overlay
        if self.render_mode != 0 and self.show_wireframe:
            glDisable(GL_LIGHTING)
            glColor3f(1.0, 1.0, 1.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glEnable(GL_POLYGON_OFFSET_LINE)
            glPolygonOffset(-1.0, -1.0)
            draw_func()
            glDisable(GL_POLYGON_OFFSET_LINE)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        

    def _draw_faces(self):
        """면 그리기 (Quads/Triangles 분리)"""
        # 1. Quads (사각형 면)
        glBegin(GL_QUADS)
        for face in self.sor_faces:
            if len(face) == 4:
                # 인덱스 유효성 검사
                if any(idx >= len(self.sor_vertices) for idx in face): continue
                
                for idx in face:
                    if idx < len(self.sor_normals):
                        nx, ny, nz = self.sor_normals[idx]
                        # NaN/Inf 검사
                        if not (math.isnan(nx) or math.isinf(nx)):
                            glNormal3f(nx, ny, nz)
                    
                    vx, vy, vz = self.sor_vertices[idx]
                    # NaN/Inf 검사
                    if not (math.isnan(vx) or math.isinf(vx)):
                        glVertex3f(vx, vy, vz)
        glEnd()

        # 2. Triangles (삼각형 면 - Caps 등)
        glBegin(GL_TRIANGLES)
        for face in self.sor_faces:
            if len(face) == 3:
                # 인덱스 유효성 검사
                if any(idx >= len(self.sor_vertices) for idx in face): continue

                for idx in face:
                    if idx < len(self.sor_normals):
                        nx, ny, nz = self.sor_normals[idx]
                        if not (math.isnan(nx) or math.isinf(nx)):
                            glNormal3f(nx, ny, nz)
                    
                    vx, vy, vz = self.sor_vertices[idx]
                    if not (math.isnan(vx) or math.isinf(vx)):
                        glVertex3f(vx, vy, vz)
        glEnd()

    # =========================================================================
    # VBO 기반 렌더링 (GPU Acceleration)
    # =========================================================================

    def _create_buffer(self, data):
        """numpy 배열로부터 VBO 생성"""
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        return vbo

    def _cleanup_vbos(self):
        """기존 VBO 삭제하여 GPU 메모리 해제"""
        buffers = [
            self.vbo_quad_vertices, self.vbo_quad_normals, self.vbo_quad_flat_normals,
            self.vbo_tri_vertices, self.vbo_tri_normals, self.vbo_tri_flat_normals
        ]
        valid_buffers = [b for b in buffers if b is not None]
        if valid_buffers:
            glDeleteBuffers(len(valid_buffers), valid_buffers)

        self.vbo_quad_vertices = None
        self.vbo_quad_normals = None
        self.vbo_quad_flat_normals = None
        self.quad_vertex_count = 0
        self.vbo_tri_vertices = None
        self.vbo_tri_normals = None
        self.vbo_tri_flat_normals = None
        self.tri_vertex_count = 0
        self.vbo_initialized = False

    def _create_vbos(self):
        """현재 지오메트리 데이터로부터 VBO 생성"""
        if not self.sor_vertices or not self.sor_faces:
            return

        self._cleanup_vbos()

        vertices = np.array(self.sor_vertices, dtype=np.float32)
        normals = np.array(self.sor_normals, dtype=np.float32) if self.sor_normals else None

        # 면을 Quad/Triangle로 분리
        quad_faces = [f for f in self.sor_faces if len(f) == 4]
        tri_faces = [f for f in self.sor_faces if len(f) == 3]

        # === Quad VBO 생성 ===
        if quad_faces:
            quad_v_list = []
            quad_n_smooth = []
            quad_n_flat = []

            for face in quad_faces:
                if any(idx >= len(vertices) for idx in face):
                    continue

                # 면 법선 계산 (Flat 셰이딩용)
                v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
                u = v1 - v0
                v = v2 - v0
                face_normal = np.cross(u, v)
                length = np.linalg.norm(face_normal)
                if length > 1e-6:
                    face_normal = face_normal / length
                else:
                    face_normal = np.array([0.0, 1.0, 0.0], dtype=np.float32)

                for idx in face:
                    quad_v_list.extend(vertices[idx])
                    if normals is not None and idx < len(normals):
                        quad_n_smooth.extend(normals[idx])
                    else:
                        quad_n_smooth.extend([0.0, 1.0, 0.0])
                    quad_n_flat.extend(face_normal)

            if quad_v_list:
                v_data = np.array(quad_v_list, dtype=np.float32)
                n_smooth_data = np.array(quad_n_smooth, dtype=np.float32)
                n_flat_data = np.array(quad_n_flat, dtype=np.float32)

                self.vbo_quad_vertices = self._create_buffer(v_data)
                self.vbo_quad_normals = self._create_buffer(n_smooth_data)
                self.vbo_quad_flat_normals = self._create_buffer(n_flat_data)
                self.quad_vertex_count = len(quad_v_list) // 3

        # === Triangle VBO 생성 ===
        if tri_faces:
            tri_v_list = []
            tri_n_smooth = []
            tri_n_flat = []

            for face in tri_faces:
                if any(idx >= len(vertices) for idx in face):
                    continue

                v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
                u = v1 - v0
                v = v2 - v0
                face_normal = np.cross(u, v)
                length = np.linalg.norm(face_normal)
                if length > 1e-6:
                    face_normal = face_normal / length
                else:
                    face_normal = np.array([0.0, 1.0, 0.0], dtype=np.float32)

                for idx in face:
                    tri_v_list.extend(vertices[idx])
                    if normals is not None and idx < len(normals):
                        tri_n_smooth.extend(normals[idx])
                    else:
                        tri_n_smooth.extend([0.0, 1.0, 0.0])
                    tri_n_flat.extend(face_normal)

            if tri_v_list:
                v_data = np.array(tri_v_list, dtype=np.float32)
                n_smooth_data = np.array(tri_n_smooth, dtype=np.float32)
                n_flat_data = np.array(tri_n_flat, dtype=np.float32)

                self.vbo_tri_vertices = self._create_buffer(v_data)
                self.vbo_tri_normals = self._create_buffer(n_smooth_data)
                self.vbo_tri_flat_normals = self._create_buffer(n_flat_data)
                self.tri_vertex_count = len(tri_v_list) // 3

        self.vbo_initialized = True

    def _draw_faces_vbo(self):
        """VBO를 사용한 면 렌더링"""
        if not self.vbo_initialized:
            return

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        use_flat = (self.render_mode == 2)

        # Quad 렌더링
        if self.quad_vertex_count > 0 and self.vbo_quad_vertices is not None:
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_quad_vertices)
            glVertexPointer(3, GL_FLOAT, 0, None)

            normal_vbo = self.vbo_quad_flat_normals if use_flat else self.vbo_quad_normals
            if normal_vbo is not None:
                glBindBuffer(GL_ARRAY_BUFFER, normal_vbo)
                glNormalPointer(GL_FLOAT, 0, None)

            glDrawArrays(GL_QUADS, 0, self.quad_vertex_count)

        # Triangle 렌더링
        if self.tri_vertex_count > 0 and self.vbo_tri_vertices is not None:
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_tri_vertices)
            glVertexPointer(3, GL_FLOAT, 0, None)

            normal_vbo = self.vbo_tri_flat_normals if use_flat else self.vbo_tri_normals
            if normal_vbo is not None:
                glBindBuffer(GL_ARRAY_BUFFER, normal_vbo)
                glNormalPointer(GL_FLOAT, 0, None)

            glDrawArrays(GL_TRIANGLES, 0, self.tri_vertex_count)

        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def set_gpu_acceleration(self, enabled):
        """GPU 가속 사용 여부 설정"""
        self.use_gpu_acceleration = enabled
        self.update()

    # =========================================================================
    # 사용자 입력 처리 (User Input Handling)
    # =========================================================================

    def mousePressEvent(self, event):
        """마우스 클릭: 2D 점 추가/선택 또는 3D 회전 시작"""
        if self.view_mode == '2D':
            # 좌표 변환 (Screen -> World)
            wx, wy = self._screen_to_world(event.x(), event.y())
            
            # Hit Test (기존 점 선택)
            snap_threshold = 0.3
            for p_idx, path_data in enumerate(self.paths):
                for pt_idx, pt in enumerate(path_data['points']):
                    if math.hypot(pt[0]-wx, pt[1]-wy) < snap_threshold:
                        self.dragging_point = (p_idx, pt_idx)
                        return

            # 새 점 추가
            self.paths[self.current_path_idx]['points'].append((wx, wy))
            self.update()
            self.pointsChanged.emit()
            
        elif self.view_mode == '3D':
            self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        """마우스 드래그: 2D 점 이동 또는 3D 카메라 회전"""
        if self.view_mode == '2D' and self.dragging_point:
            wx, wy = self._screen_to_world(event.x(), event.y())
            p_idx, pt_idx = self.dragging_point
            self.paths[p_idx]['points'][pt_idx] = (wx, wy)
            self.update()
            self.pointsChanged.emit()
            
        elif self.view_mode == '3D' and self.last_mouse_pos:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            
            self.cam_theta += dx * 0.5
            self.cam_phi -= dy * 0.5
            self.cam_phi = max(0.1, min(179.9, self.cam_phi)) # 짐벌락 방지
            
            self.last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """드래그 종료"""
        self.dragging_point = None
        self.last_mouse_pos = None

    def wheelEvent(self, event):
        """마우스 휠: 3D 줌 인/아웃"""
        if self.view_mode == '3D':
            delta = event.angleDelta().y()
            self.cam_radius -= (1.0 if delta > 0 else -1.0)
            self.cam_radius = max(5.0, min(100.0, self.cam_radius))
            self.update()

    def _screen_to_world(self, sx, sy):
        """화면 좌표(px)를 2D 월드 좌표로 변환"""
        gl_y = self.height() - sy
        wx = self.ortho_left + (sx / self.width()) * (self.ortho_right - self.ortho_left)
        wy = self.ortho_bottom + (gl_y / self.height()) * (self.ortho_top - self.ortho_bottom)
        return wx, wy

    def reset_view(self):
        """카메라 뷰 초기화"""
        self.cam_radius = 20.0
        self.cam_theta = 45.0
        self.cam_phi = 45.0
        self.update()

    # =========================================================================
    # 모델 생성 로직 (Model Generation Logic)
    # =========================================================================

    def generate_model(self):
        """현재 모드(SOR/Sweep)에 따라 3D 모델 데이터 생성"""
        try:
            self.sor_vertices = []
            self.sor_normals = []
            self.sor_faces = []

            if self.modeling_mode == 0:
                self._generate_sor()
            else:
                self._generate_sweep()

            self.calculate_normals()

            # VBO 생성 (GPU 가속용)
            if self.use_gpu_acceleration:
                self._create_vbos()

        except Exception as e:
            print(f"generate_model Error: {e}")
            import traceback
            traceback.print_exc()

    def calculate_normals(self):
        """정점 법선 벡터 계산 (Gouraud Shading용)"""
        try:
            self.sor_normals = [(0.0, 0.0, 0.0) for _ in range(len(self.sor_vertices))]
            
            # Face Normal 계산 및 정점에 누적
            for i, face in enumerate(self.sor_faces):
                if len(face) < 3: continue
                # 인덱스 유효성 검사
                if any(idx >= len(self.sor_vertices) for idx in face): continue
                
                v1 = self.sor_vertices[face[0]]
                v2 = self.sor_vertices[face[1]]
                v3 = self.sor_vertices[face[2]]
                
                # Cross Product
                ux, uy, uz = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
                vx, vy, vz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
                nx, ny, nz = uy*vz - uz*vy, uz*vx - ux*vz, ux*vy - uy*vx
                
                for idx in face:
                    ox, oy, oz = self.sor_normals[idx]
                    self.sor_normals[idx] = (ox + nx, oy + ny, oz + nz)
            
            # Normalize
            for i in range(len(self.sor_normals)):
                nx, ny, nz = self.sor_normals[i]
                length = math.sqrt(nx*nx + ny*ny + nz*nz)
                if length > 1e-6: # 0으로 나누기 방지
                    self.sor_normals[i] = (nx/length, ny/length, nz/length)
                else:
                    self.sor_normals[i] = (0.0, 1.0, 0.0) # 기본값 (Y축)
                    
        except Exception as e:
            print(f"calculate_normals Error: {e}")

    def _generate_sor(self):
        """SOR (Surface of Revolution) 모델 생성 로직"""
        angle_step = 360.0 / self.num_slices
        vertex_offset = 0

        for path_data in self.paths:
            path = path_data['points']
            is_closed = path_data['closed']
            if len(path) < 2: continue

            # 1. 정점 생성 (회전)
            current_path_v_count = 0
            for i in range(self.num_slices):
                theta = math.radians(i * angle_step)
                cos_t, sin_t = math.cos(theta), math.sin(theta)

                for x, y in path:
                    # Windows 호환성을 위해 명시적 float 변환
                    if self.rotation_axis == 'Y':
                        self.sor_vertices.append((float(x * cos_t), float(y), float(-x * sin_t)))
                    else:
                        self.sor_vertices.append((float(x), float(y * cos_t), float(y * sin_t)))
                    current_path_v_count += 1

            # 2. 면 생성 (Quad Strip)
            num_pts = len(path)
            num_segs = num_pts if is_closed else num_pts - 1
            
            for i in range(self.num_slices):
                next_i = (i + 1) % self.num_slices
                for j in range(num_segs):
                    base = vertex_offset
                    p1 = base + i * num_pts + j
                    p2 = base + i * num_pts + ((j + 1) % num_pts)
                    p3 = base + next_i * num_pts + ((j + 1) % num_pts)
                    p4 = base + next_i * num_pts + j
                    self.sor_faces.append([p1, p4, p3, p2])
            
            vertex_offset += current_path_v_count

    def _generate_sweep(self):
        """Sweep Surface 모델 생성 로직 (Extrusion + Twist + Caps)"""
        steps = 30
        
        for path_data in self.paths:
            path = path_data['points']
            is_closed = path_data['closed']
            if len(path) < 2: continue
            
            start_v_idx = len(self.sor_vertices)
            
            # 1. 정점 생성 (Extrusion & Twist)
            for k in range(steps + 1):
                t = k / steps
                z = (t - 0.5) * self.sweep_length
                angle = math.radians(t * self.sweep_twist)
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                
                for x, y in path:
                    rx = x * cos_a - y * sin_a
                    ry = x * sin_a + y * cos_a
                    # Windows 호환성을 위해 명시적 float 변환
                    self.sor_vertices.append((float(rx), float(ry), float(z)))
            
            # 2. 옆면 생성
            num_pts = len(path)
            for k in range(steps):
                for i in range(num_pts - 1):
                    p1 = start_v_idx + k * num_pts + i
                    p2 = start_v_idx + k * num_pts + (i + 1)
                    p3 = start_v_idx + (k + 1) * num_pts + (i + 1)
                    p4 = start_v_idx + (k + 1) * num_pts + i
                    self.sor_faces.append([p1, p2, p3, p4])
                    
                if is_closed: # 닫힌 프로파일 연결
                    p1 = start_v_idx + k * num_pts + (num_pts - 1)
                    p2 = start_v_idx + k * num_pts + 0
                    p3 = start_v_idx + (k + 1) * num_pts + 0
                    p4 = start_v_idx + (k + 1) * num_pts + (num_pts - 1)
                    self.sor_faces.append([p1, p2, p3, p4])

            # 3. 캡(뚜껑) 생성
            if self.sweep_caps and len(path) > 2:
                # 중심점 계산
                cx = sum(p[0] for p in path) / len(path)
                cy = sum(p[1] for p in path) / len(path)
                
                # Start Cap (Z = -Length/2)
                c_idx = len(self.sor_vertices)
                self.sor_vertices.append((float(cx), float(cy), float(-0.5 * self.sweep_length)))
                
                first_layer = start_v_idx
                for i in range(num_pts):
                    curr = first_layer + i
                    next_p = first_layer + ((i + 1) % num_pts)
                    if not is_closed and i == num_pts - 1: break
                    self.sor_faces.append([c_idx, next_p, curr]) # 역순 (Normal Out)

                # End Cap (Z = +Length/2)
                c_idx = len(self.sor_vertices)
                end_angle = math.radians(self.sweep_twist)
                rcx = cx * math.cos(end_angle) - cy * math.sin(end_angle)
                rcy = cx * math.sin(end_angle) + cy * math.cos(end_angle)
                self.sor_vertices.append((float(rcx), float(rcy), float(0.5 * self.sweep_length)))
                
                last_layer = start_v_idx + steps * num_pts
                for i in range(num_pts):
                    curr = last_layer + i
                    next_p = last_layer + ((i + 1) % num_pts)
                    if not is_closed and i == num_pts - 1: break
                    self.sor_faces.append([c_idx, curr, next_p]) # 정순

    # =========================================================================
    # 파일 입출력 (File I/O)
    # =========================================================================

    def save_model(self, file_path):
        """모델 데이터를 .dat 파일(v6)로 저장"""
        if not self.sor_vertices: return
        try:
            with open(file_path, 'w') as f:
                # Header
                f.write(f"v6 {self.num_slices} {self.rotation_axis} {self.render_mode} "
                        f"{self.model_color[0]:.6f} {self.model_color[1]:.6f} {self.model_color[2]:.6f} "
                        f"{self.modeling_mode} {self.sweep_length:.6f} {self.sweep_twist:.6f} {1 if self.sweep_caps else 0}\n")
                
                # Paths
                valid_paths = [p for p in self.paths if p['points']]
                f.write(f"{len(valid_paths)}\n")
                for p_data in valid_paths:
                    f.write(f"{len(p_data['points'])}\n")
                    f.write(f"{1 if p_data['closed'] else 0}\n")
                    for p in p_data['points']:
                        f.write(f"{p[0]:.6f} {p[1]:.6f}\n")
                
                # Vertices
                f.write(f"{len(self.sor_vertices)}\n")
                for v in self.sor_vertices:
                    f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                
                # Faces
                f.write(f"{len(self.sor_faces)}\n")
                for face in self.sor_faces:
                    f.write(f"{len(face)} " + " ".join(map(str, face)) + "\n")
                    
            print(f"저장 완료: {file_path}")
        except Exception as e:
            print(f"저장 실패: {e}")

    def load_model(self, file_path):
        """모델 데이터를 .dat 파일에서 로드"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                idx = 0
                
                # Header Parsing
                parts = lines[idx].strip().split()
                if parts[0] == 'v6':
                    self.num_slices = int(parts[1])
                    self.rotation_axis = parts[2]
                    self.render_mode = int(parts[3])
                    self.model_color = (float(parts[4]), float(parts[5]), float(parts[6]))
                    self.modeling_mode = int(parts[7])
                    self.sweep_length = float(parts[8])
                    self.sweep_twist = float(parts[9])
                    self.sweep_caps = bool(int(parts[10])) if len(parts) >= 11 else False
                    idx += 1
                else:
                    # 구버전 호환성 로직은 생략하거나 필요시 추가
                    idx += 1
                
                # Paths Parsing
                num_paths = int(lines[idx].strip()); idx += 1
                self.paths = []
                for _ in range(num_paths):
                    num_pts = int(lines[idx].strip()); idx += 1
                    is_closed = False
                    # Check Closed Flag
                    try:
                        p = lines[idx].strip().split()
                        if len(p) == 1 and p[0] in ['0', '1']:
                            is_closed = bool(int(p[0]))
                            idx += 1
                    except: pass
                    
                    pts = []
                    for _ in range(num_pts):
                        pts.append(tuple(map(float, lines[idx].strip().split())))
                        idx += 1
                    self.paths.append({'points': pts, 'closed': is_closed})
                
                self.paths.append({'points': [], 'closed': False})
                self.current_path_idx = len(self.paths) - 1
                
                # Vertices Parsing
                num_v = int(lines[idx].strip()); idx += 1
                self.sor_vertices = []
                for _ in range(num_v):
                    self.sor_vertices.append(tuple(map(float, lines[idx].strip().split())))
                    idx += 1
                    
                # Faces Parsing
                num_f = int(lines[idx].strip()); idx += 1
                self.sor_faces = []
                for _ in range(num_f):
                    parts = list(map(int, lines[idx].strip().split()))
                    self.sor_faces.append(parts[1:])
                    idx += 1
                    
                self.calculate_normals() # 법선 재계산

                # VBO 생성 (GPU 가속용)
                if self.use_gpu_acceleration:
                    self._create_vbos()

                self.update()
                self.pointsChanged.emit()

                if self.view_mode == '2D':
                    self.view_mode = '3D'
                    self.viewModeChanged.emit('3D')

            print(f"로드 완료: {file_path}")
        except Exception as e:
            print(f"로드 실패: {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # 설정자 및 UI 상호작용 (Setters & UI Interaction)
    # =========================================================================

    def set_rotation_axis(self, axis):
        self.rotation_axis = axis
        if self.view_mode == '3D': self.generate_model()
        self.update()

    def set_num_slices(self, slices):
        self.num_slices = slices
        if self.view_mode == '3D': self.generate_model()
        self.update()

    def set_modeling_mode(self, mode):
        self.modeling_mode = mode
        if self.view_mode == '3D': self.generate_model()
        self.update()

    def set_sweep_length(self, length):
        self.sweep_length = length
        if self.view_mode == '3D': self.generate_model()
        self.update()

    def set_sweep_twist(self, angle):
        self.sweep_twist = angle
        if self.view_mode == '3D': self.generate_model()
        self.update()

    def set_sweep_caps(self, enabled):
        self.sweep_caps = enabled
        if self.view_mode == '3D': self.generate_model()
        self.update()

    def set_view_mode(self, mode):
        if self.view_mode != mode:
            self.view_mode = mode
            if mode == '3D' and any(p['points'] for p in self.paths):
                self.generate_model()
            self.update()
            self.viewModeChanged.emit(mode)

    def clear_points(self):
        self.paths = [{'points': [], 'closed': False}]
        self.current_path_idx = 0
        self.sor_vertices = []
        self.sor_faces = []
        self._cleanup_vbos()  # VBO 정리
        self.update()
        self.pointsChanged.emit()

    def delete_point(self, path_idx, point_idx):
        if 0 <= path_idx < len(self.paths):
            points = self.paths[path_idx]['points']
            if 0 <= point_idx < len(points):
                del points[point_idx]
                if not points and len(self.paths) > 1:
                    del self.paths[path_idx]
                    self.current_path_idx = max(0, len(self.paths) - 1)
                self.update()
                self.pointsChanged.emit()

    def close_current_path(self):
        if self.paths[self.current_path_idx]['points']:
            self.paths[self.current_path_idx]['closed'] = True
            self.paths.append({'points': [], 'closed': False})
            self.current_path_idx += 1
            self.update()
            self.pointsChanged.emit()