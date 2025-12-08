# -*- coding: utf-8 -*-
"""
Miro Game OpenGL Widget - 1인칭 미로 게임
"""

import math
import os
import glob
import random
import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QCursor, QImage

from OpenGL.GL import *
from OpenGL.GLU import *
from miro_weather import WeatherSystem

# 게임 상수
PLAYER_HEIGHT = 0.8       # 눈높이
PLAYER_RADIUS = 0.25      # 충돌 반경
MOVE_SPEED = 0.08         # 이동 속도
MOUSE_SENSITIVITY = 0.15  # 마우스 감도
GAME_TICK_MS = 16         # ~60 FPS

# 테마 설정
THEMES = {
    "810-Gwan": "theme_810",
    "Inside Campus": "theme_campus",
    "Path to the Main Gate": "theme_gate"
}

class MiroOpenGLWidget(QOpenGLWidget):
    """
    1인칭 미로 게임을 위한 OpenGL 위젯.
    WASD로 이동, 마우스로 시점 회전.
    """

    # 시그널: 게임 클리어 시 발생
    game_won = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 플레이어 상태 (기존 유지)
        self.player_pos = [0.0, PLAYER_HEIGHT, 0.0]  # x, y, z
        self.player_yaw = 0.0      # 좌우 회전 (라디안)
        self.player_pitch = 0.0    # 상하 회전 (라디안)

        # 키 입력 상태
        self.keys_pressed = set()

        # 미로 데이터 (기존 유지)
        self.maze_vertices = []
        self.maze_faces = []
        self.wall_faces = []   # 벽 면 데이터 보관
        self.floor_faces = []  # 바닥 면 데이터 보관
        self.maze_normals = []
        self.maze_width = 0
        self.maze_height = 0
        self.maze_grid = []
        self.grid_min_x = 0.0
        self.grid_min_z = 0.0
        self.grid_scale = 1.0

        # 시작/목표 위치 (기존 유지)
        self.start_pos = [0.0, 0.0]
        self.goal_pos = [0.0, 0.0]
        self.goal_radius = 0.5

        # 게임 상태
        self.game_active = False
        self.mouse_captured = False
        self.last_mouse_pos = None
        self.current_theme = "810-Gwan" # 기본 테마

        # 게임 루프 타이머
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self._update_game)

        # 키보드 포커스 설정
        self.setFocusPolicy(Qt.StrongFocus)

        # VBO IDs (Batch Rendering용 리스트 구조로 변경 예정 - 초기화는 None)
        self.wall_batches = []  # [{'texture_id': id, 'vbo_v': v, 'vbo_uv': uv, 'vbo_n': n, 'count': c}, ...]
        self.floor_batches = []
        
        # 텍스처 ID 관리 (리스트)
        self.theme_textures = {
            'walls': [],
            'floors': []
        }
        
        # Wireframe VBO (Cleanup 시 필요)
        self.vbo_wireframe_indices = None

        # VBO 메타데이터
        self.vbo_initialized = False
        self.use_gpu_acceleration = True  # GPU 가속 사용 여부

        # 환경 설정 (안개)
        self.fog_enabled = True
        self.fog_density = 0.5 # 안개 밀도 (값이 클수록 안개가 짙어지고 가까이서 시작됨)
        self.fog_color = [0.1, 0.1, 0.15, 1.0]

        # 날씨 시스템
        self.weather = WeatherSystem()

        # 캐싱된 Quadric (목표 지점 렌더링용)
        self.goal_quadric = None

    def set_theme(self, theme_name):
        """
        테마를 변경하고 관련 텍스처를 다시 로드합니다.
        
        Args:
            theme_name (str): 적용할 테마 이름 (예: "810-Gwan")
        """
        if theme_name in THEMES:
            self.current_theme = theme_name
            # 텍스처 다시 로드 (GL 컨텍스트가 활성화된 상태여야 함)
            if self.isValid():
                self.makeCurrent()
                self._load_textures()
                # 지오메트리도 텍스처 인덱스 재할당 위해 다시 생성 필요
                # 현재 구조에서는 텍스처 로드만 하고, 이후 렌더링 시 반영됨
                pass 
                self.doneCurrent()

        # VBO 메타데이터
        self.vbo_initialized = False
        self.wall_count = 0
        self.floor_count = 0

        # 캐싱된 Quadric (목표 지점 렌더링용)
        self.goal_quadric = None

    def set_gpu_acceleration(self, enabled):
        """GPU 가속 사용 여부 설정"""
        self.use_gpu_acceleration = enabled
        self.update()

    def set_fog(self, enabled):
        """안개 켜기/끄기"""
        self.fog_enabled = enabled
        if self.isValid():
            self.makeCurrent()
            if enabled:
                glEnable(GL_FOG)
            else:
                glDisable(GL_FOG)
            self.doneCurrent()
            self.update()

    def set_weather(self, type_name):
        """날씨 설정 (Clear, Rain, Snow)"""
        if self.weather:
            self.weather.set_weather(type_name)

    def initializeGL(self):
        """OpenGL 초기화"""
        glClearColor(0.1, 0.1, 0.15, 1.0)  # 어두운 배경
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        glEnable(GL_TEXTURE_2D) # 텍스처 활성화

        # 안개 설정
        glFogi(GL_FOG_MODE, GL_EXP2) # 거리에 따라 지수적으로 진해짐 (자연스러움)
        glFogfv(GL_FOG_COLOR, self.fog_color)
        glFogf(GL_FOG_DENSITY, self.fog_density)
        glHint(GL_FOG_HINT, GL_NICEST)
        
        if self.fog_enabled:
            glEnable(GL_FOG)
        else:
            glDisable(GL_FOG)

        # 조명 설정
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 10.0, 0.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0]) # 조금 더 밝게
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.7, 0.7, 0.7, 1.0])

        # 캐싱된 Quadric 생성 (목표 지점 렌더링용)
        self.goal_quadric = gluNewQuadric()
        gluQuadricNormals(self.goal_quadric, GLU_SMOOTH)
        
        # 텍스처 로드
        self._load_textures()

        # 지연된 VBO 생성 (데이터는 로드되었으나 VBO가 없는 경우)
        if self.maze_vertices and not self.vbo_initialized:
            self._create_vbos(self.wall_faces, self.floor_faces)

    def _load_textures(self):
        """현재 테마에 맞는 텍스처 로드"""
        
        # 기존 텍스처 삭제
        for t_id in self.theme_textures['walls'] + self.theme_textures['floors']:
            if t_id: glDeleteTextures([t_id])
            
        self.theme_textures['walls'] = []
        self.theme_textures['floors'] = []
        
        base_path = os.path.dirname(__file__)
        assets_path = os.path.join(base_path, 'assets', 'textures')
        
        if not os.path.exists(assets_path):
            print(f"Assets directory not found: {assets_path}")
            return

        theme_prefix = THEMES.get(self.current_theme, "theme_810")
        
        # 벽 텍스처 로드 (glob 사용)
        wall_pattern = os.path.join(assets_path, f"{theme_prefix}_wall_*.png")
        wall_files = sorted(glob.glob(wall_pattern))
        for f in wall_files:
            t_id = self._create_texture(f)
            if t_id: self.theme_textures['walls'].append(t_id)
            
        # 바닥 텍스처 로드
        floor_pattern = os.path.join(assets_path, f"{theme_prefix}_floor_*.png")
        floor_files = sorted(glob.glob(floor_pattern))
        for f in floor_files:
            t_id = self._create_texture(f)
            if t_id: self.theme_textures['floors'].append(t_id)
            
        print(f"Theme '{self.current_theme}' loaded: {len(self.theme_textures['walls'])} walls, {len(self.theme_textures['floors'])} floors")

    def _create_texture(self, file_path):
        """단일 텍스처 생성 헬퍼"""
        if not os.path.exists(file_path):
            print(f"Texture not found: {file_path}")
            return None
            
        image = QImage(file_path)
        if image.isNull():
            print(f"Failed to load image: {file_path}")
            return None
            
        # OpenGL 호환 포맷으로 변환
        image = image.convertToFormat(QImage.Format_RGBA8888)
        width = image.width()
        height = image.height()
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        data = ptr.asstring()
        
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        
        # 텍스처 파라미터 설정 (반복, 선형 필터링)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        
        return texture_id

    def resizeGL(self, w, h):
        """뷰포트 크기 조정"""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h if h > 0 else 1.0
        gluPerspective(70.0, aspect, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        """렌더링"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # 안개 상태 확인 (initializeGL에서 설정했더라도 확실하게)
        if self.fog_enabled:
            glEnable(GL_FOG)
        else:
            glDisable(GL_FOG)

        # 1인칭 카메라 설정
        self._setup_camera()

        # 미로 렌더링
        self._draw_maze()

        # 날씨 렌더링 (투명도 처리를 위해 미로보다 나중에)
        if self.weather:
            self.weather.draw()

        # 목표 지점 표시
        self._draw_goal()

    def _setup_camera(self):
        """1인칭 카메라 설정"""
        # 시선 방향 계산
        dir_x = math.cos(self.player_pitch) * math.sin(self.player_yaw)
        dir_y = math.sin(self.player_pitch)
        dir_z = math.cos(self.player_pitch) * math.cos(self.player_yaw)

        eye_x, eye_y, eye_z = self.player_pos
        center_x = eye_x + dir_x
        center_y = eye_y + dir_y
        center_z = eye_z + dir_z

        gluLookAt(eye_x, eye_y, eye_z,
                  center_x, center_y, center_z,
                  0.0, 1.0, 0.0)

    def _draw_maze(self):
        """VBO를 사용한 텍스처 미로 렌더링 (배치 렌더링)"""
        if not self.vbo_initialized:
            return

        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        
        glColor3f(1.0, 1.0, 1.0) # 텍스처 색상 혼합 방지 (흰색)

        # 헬퍼 함수: 배치 그리기
        def draw_batches(batches):
            for batch in batches:
                if batch['count'] > 0 and batch['texture_id']:
                    glBindTexture(GL_TEXTURE_2D, batch['texture_id'])
                    
                    glBindBuffer(GL_ARRAY_BUFFER, batch['vbo_vertices'])
                    glVertexPointer(3, GL_FLOAT, 0, None)
                    
                    glBindBuffer(GL_ARRAY_BUFFER, batch['vbo_normals'])
                    glNormalPointer(GL_FLOAT, 0, None)
                    
                    glBindBuffer(GL_ARRAY_BUFFER, batch['vbo_uvs'])
                    glTexCoordPointer(2, GL_FLOAT, 0, None)
                    
                    glDrawArrays(GL_QUADS, 0, batch['count'])

        # 1. 벽 렌더링
        draw_batches(self.wall_batches)

        # 2. 바닥 렌더링
        draw_batches(self.floor_batches)

        # 정리
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisable(GL_TEXTURE_2D)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def _draw_goal(self):
        """목표 지점 표시 (빛나는 기둥) - 캐싱된 Quadric 사용"""
        glPushMatrix()
        glTranslatef(self.goal_pos[0], 0.0, self.goal_pos[1])
        glRotatef(-90, 1, 0, 0)  # X축 기준 -90도 회전 (Z축→Y축 방향으로)

        # 반투명 효과를 위해 조명 끄기
        glDisable(GL_LIGHTING)
        glColor3f(0.0, 1.0, 0.3)  # 녹색 빛

        # 캐싱된 Quadric 사용 (매 프레임 생성/삭제 제거)
        if self.goal_quadric:
            gluCylinder(self.goal_quadric, 0.3, 0.3, 2.0, 16, 1)

        glEnable(GL_LIGHTING)
        glPopMatrix()

    def load_maze(self, file_path):
        """미로 파일 로드 (.dat 형식)"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                idx = 0

                # 헤더 파싱 (v6 형식)
                parts = lines[idx].strip().split()
                idx += 1

                # 경로 수 (미로에서는 0)
                num_paths = int(lines[idx].strip())
                idx += 1

                # 경로 스킵
                for _ in range(num_paths):
                    num_pts = int(lines[idx].strip())
                    idx += 1
                    try:
                        p = lines[idx].strip().split()
                        if len(p) == 1 and p[0] in ['0', '1']:
                            idx += 1
                    except:
                        pass
                    idx += num_pts

                # 정점 파싱
                num_v = int(lines[idx].strip())
                idx += 1
                self.maze_vertices = []
                for _ in range(num_v):
                    coords = list(map(float, lines[idx].strip().split()))
                    self.maze_vertices.append(coords)
                    idx += 1

                # 면 파싱 및 분류 (벽 vs 바닥)
                num_f = int(lines[idx].strip())
                idx += 1
                self.maze_faces = [] # 원본 유지 (충돌 감지용)
                wall_faces = []
                floor_faces = []
                
                for _ in range(num_f):
                    parts = list(map(int, lines[idx].strip().split()))
                    face_indices = parts[1:]
                    self.maze_faces.append(face_indices)
                    idx += 1
                    
                    # 면 분류: 정점 중 하나라도 Y > 0.05 이면 벽으로 간주
                    is_wall = False
                    for v_idx in face_indices:
                        if v_idx < len(self.maze_vertices):
                            if self.maze_vertices[v_idx][1] > 0.05:
                                is_wall = True
                                break
                    
                    if is_wall:
                        wall_faces.append(face_indices)
                    else:
                        floor_faces.append(face_indices)

            # 멤버 변수에 저장 (재생성/지연생성 위해)
            self.wall_faces = wall_faces
            self.floor_faces = floor_faces

            # 법선 계산 (원본 면 기준)
            self._calculate_normals()

            # 미로 범위 계산 및 시작/목표 위치 설정
            self._calculate_maze_bounds()

            # VBO 생성 (컨텍스트가 유효하고 텍스처가 로드된 경우에만 즉시 생성)
            # 그렇지 않으면 initializeGL에서 수행됨
            self._cleanup_vbos()
            
            if self.isValid() and self.theme_textures['walls']:
                self.makeCurrent()
                self._create_vbos(self.wall_faces, self.floor_faces)
                self.doneCurrent()
            
            print(f"미로 로드 완료: {file_path}")
            print(f"정점: {len(self.maze_vertices)}, 벽 면: {len(wall_faces)}, 바닥 면: {len(floor_faces)}")
            print(f"시작: {self.start_pos}, 목표: {self.goal_pos}")

            self.update()

        except Exception as e:
            print(f"미로 로드 실패: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_normals(self):
        """면 법선 계산"""
        self.maze_normals = []
        for face in self.maze_faces:
            if len(face) >= 3:
                v0 = self.maze_vertices[face[0]]
                v1 = self.maze_vertices[face[1]]
                v2 = self.maze_vertices[face[2]]

                # 두 변 벡터
                u = [v1[i] - v0[i] for i in range(3)]
                v = [v2[i] - v0[i] for i in range(3)]

                # 외적
                n = [
                    u[1]*v[2] - u[2]*v[1],
                    u[2]*v[0] - u[0]*v[2],
                    u[0]*v[1] - u[1]*v[0]
                ]

                # 정규화
                length = math.sqrt(sum(x*x for x in n))
                if length > 0:
                    n = [x/length for x in n]
                else:
                    n = [0, 1, 0]

                self.maze_normals.append(n)
            else:
                self.maze_normals.append([0, 1, 0])

    def _cleanup_vbos(self):
        """VBO 리소스 정리 (배치 포함)"""
        # OpenGL 컨텍스트 유효성 검사
        if not self.isValid():
            # Python 측 참조만 정리
            self.wall_batches = []
            self.floor_batches = []
            self.vbo_wireframe_indices = None
            self.vbo_initialized = False
            self.wireframe_index_count = 0
            return

        # GL 호출 전 컨텍스트 활성화
        self.makeCurrent()

        # 배치가 생성된 경우 리스트 순회
        all_batches = self.wall_batches + self.floor_batches
        for batch in all_batches:
            buffers = [batch['vbo_vertices'], batch['vbo_uvs'], batch['vbo_normals']]
            if glDeleteBuffers:  # 추가 안전 검사
                glDeleteBuffers(len(buffers), buffers)

        if self.vbo_wireframe_indices:
            if glDeleteBuffers:
                glDeleteBuffers(1, [self.vbo_wireframe_indices])

        self.wall_batches = []
        self.floor_batches = []
        self.vbo_wireframe_indices = None

        self.vbo_initialized = False
        self.wireframe_index_count = 0

        self.doneCurrent()

    # ... _calculate_maze_bounds ...

    # ... (other methods) ...

    def cleanup_gl_resources(self):
        """OpenGL 리소스 정리 (위젯 소멸 시 호출)"""
        self._cleanup_vbos()

        # OpenGL 컨텍스트 유효성 검사
        if not self.isValid():
            self.goal_quadric = None
            self.theme_textures['walls'] = []
            self.theme_textures['floors'] = []
            return

        self.makeCurrent()

        if self.goal_quadric:
            gluDeleteQuadric(self.goal_quadric)
            self.goal_quadric = None

        # 텍스처 삭제 (리스트 순회)
        all_textures = self.theme_textures['walls'] + self.theme_textures['floors']
        if all_textures and glDeleteTextures:
            glDeleteTextures(len(all_textures), all_textures)

        self.theme_textures['walls'] = []
        self.theme_textures['floors'] = []

        self.doneCurrent()

    def _create_vbos(self, wall_faces, floor_faces):
        """벽과 바닥을 텍스처별로 그룹화하여 VBO 배치 생성"""
        if not self.maze_vertices:
            return

        # 벽의 전체 높이 계산 (텍스처 수직 스케일링용)
        # 모든 정점 중 Y 최대값 찾기 (최소값은 0이라 가정)
        all_ys = [v[1] for v in self.maze_vertices]
        max_wall_height = max(all_ys) if all_ys else 1.0
        if max_wall_height < 1.0: max_wall_height = 1.0

        self.wall_batches = []
        self.floor_batches = []
        
        # 헬퍼 함수: VBO 생성 및 등록
        def create_buffer(data):
            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)
            return vbo

        def process_faces(faces, texture_ids, batches_list, is_wall=True):
            if not texture_ids:
                return

            # 1. 텍스처 인덱스별로 면 분류 (Grouping)
            grouped_faces = {i: [] for i in range(len(texture_ids))}
            for face in faces:
                idx = random.randint(0, len(texture_ids) - 1)
                grouped_faces[idx].append(face)

            # 2. 각 그룹별 지오메트리 생성 및 VBO 생성
            for idx, group in grouped_faces.items():
                if not group: continue
                
                v_list = []
                uv_list = []
                n_list = []
                
                for face in group:
                    if len(face) < 4: continue
                    # 면 정점 좌표 (배열 변환)
                    p0 = np.array(self.maze_vertices[face[0]])
                    p1 = np.array(self.maze_vertices[face[1]])
                    p2 = np.array(self.maze_vertices[face[2]])
                    p3 = np.array(self.maze_vertices[face[3]])
                    
                    # 법선 계산
                    u_vec = p1 - p0
                    v_vec = p2 - p0
                    n_cross = np.cross(u_vec, v_vec)
                    length = np.linalg.norm(n_cross)
                    if length > 0:
                        normal = n_cross / length
                    else:
                        normal = np.array([0.0, 1.0, 0.0])
                    
                    # 정점 및 법선 추가
                    v_list.extend(p0.tolist() + p1.tolist() + p2.tolist() + p3.tolist())
                    n_list_val = normal.tolist()
                    for _ in range(4): n_list.extend(n_list_val)
                        
                    # UV 계산 (Face-Relative, Aspect Preserved, Y-Flipped)
                    local_uvs = []
                    points = [p0, p1, p2, p3]
                    
                    if abs(normal[1]) > 0.9: # 바닥 (XZ 평면)
                        # X, Z 좌표 추출
                        xs = [p[0] for p in points]
                        zs = [p[2] for p in points]
                        min_x, min_z = min(xs), min(zs)
                        
                        # 로컬 좌표 (0.0 ~ Width/Height)
                        for p in points:
                            u = p[0] - min_x
                            v = p[2] - min_z
                            local_uvs.extend([u, v])
                            
                    else: # 벽 (수직)
                        # [UV 매핑 로직 설명]
                        # 1. 수직 텍스처 통합 (One Long Vertical Texture):
                        #    벽의 높이가 1.0을 넘더라도 (예: 전체 미로 높이), 텍스처가 타일링(반복)되지 않고
                        #    바닥(Y=0)에서 천장(Y=max_height)까지 한 번만 늘어나도록 V좌표를 계산합니다.
                        #    Formula: v = 1.0 - (p[1] / max_wall_height)
                        
                        # 2. 상하 반전 해결 (Fix Upside Down):
                        #    이미지 좌표계(Top-Left=0,0)와 OpenGL 텍스처 좌표계(Bottom-Left=0,0)의 차이로 인해,
                        #    일반적인 매핑(v=y) 시 이미지가 뒤집힙니다.
                        #    따라서 World Top(Y=MAX)을 V=0(Image Top), World Bottom(Y=0)을 V=1(Image Bottom)으로 매핑합니다.
                        
                        # 3. 좌우 반전 해결 (Fix Left-Right Flip):
                        #    가로(U) 좌표를 max_dim - val 로 계산하여 좌우를 뒤집어 매핑합니다.

                        # 가로(U) 범위 계산
                        if abs(normal[0]) > 0.5: # YZ 평면 (Normal X) -> Z축이 가로
                             dim_vals = [p[2] for p in points]
                        else: # XY 평면 (Normal Z) -> X축이 가로
                             dim_vals = [p[0] for p in points]
                        
                        min_dim = min(dim_vals)
                        max_dim = max(dim_vals)
                        
                        for p in points:
                            val = p[2] if abs(normal[0]) > 0.5 else p[0]
                            
                            # U: 좌우 반전 적용 (Texture Mirroring Fix)
                            u = max_dim - val
                            
                            # V: 전체 높이 기준 정규화 및 반전 (Vertical Stretch & Flip)
                            # Y=0 -> 1.0 (Bottom), Y=H -> 0.0 (Top)
                            v = 1.0 - (p[1] / max_wall_height)
                            
                            local_uvs.extend([u, v])
    
                    uv_list.extend(local_uvs)
                
                # Numpy 배열 변환
                v_data = np.array(v_list, dtype=np.float32)
                uv_data = np.array(uv_list, dtype=np.float32)
                n_data = np.array(n_list, dtype=np.float32)
                
                # 배치 정보 저장
                batch = {
                    'texture_id': texture_ids[idx],
                    'vbo_vertices': create_buffer(v_data),
                    'vbo_uvs': create_buffer(uv_data),
                    'vbo_normals': create_buffer(n_data),
                    'count': len(v_data) // 3
                }
                batches_list.append(batch)

        # 벽 배치 생성
        process_faces(wall_faces, self.theme_textures['walls'], self.wall_batches, is_wall=True)
        # 바닥 배치 생성
        process_faces(floor_faces, self.theme_textures['floors'], self.floor_batches, is_wall=False)

        # Unbind
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        
        self.vbo_initialized = True

    def _calculate_maze_bounds(self):
        """미로 범위 계산 및 시작/목표 위치 설정"""
        if not self.maze_vertices:
            return

        # 미로 범위 계산
        min_x = min(v[0] for v in self.maze_vertices)
        max_x = max(v[0] for v in self.maze_vertices)
        min_z = min(v[2] for v in self.maze_vertices)
        max_z = max(v[2] for v in self.maze_vertices)

        # 미로 그리드 재구성 (충돌 감지용) - 먼저 생성
        self._build_collision_grid(min_x, max_x, min_z, max_z)

        # 시작점: 통로 셀 중 상단에서 가장 가까운 위치 찾기
        self.start_pos = self._find_safe_spawn(near_top=True)

        # 목표점: 통로 셀 중 하단에서 가장 가까운 위치 찾기
        self.goal_pos = self._find_safe_spawn(near_top=False)

    def _build_collision_grid(self, min_x, max_x, min_z, max_z):
        """충돌 감지용 그리드 구축 (정점 기반)"""
        # 그리드 해상도: 1.0 단위
        grid_scale = 1.0

        self.grid_min_x = min_x
        self.grid_min_z = min_z
        self.grid_scale = grid_scale

        grid_width = int((max_x - min_x) / grid_scale) + 2
        grid_height = int((max_z - min_z) / grid_scale) + 2

        # 모든 셀을 통로로 초기화 (0)
        self.maze_grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]

        # 벽의 윗면(Top Face)을 찾아 해당 셀을 벽으로 표시 (1)
        # 벽은 바닥(y=0)에서 시작하므로, 모든 정점의 y가 0.1보다 큰 면은 벽의 윗면뿐입니다.
        # 정점 기반 판정은 벽 두께가 1.0일 때 이웃 셀을 침범하는 문제가 있어, 면의 중심점을 사용합니다.
        for face in self.maze_faces:
            # 면을 구성하는 정점들의 좌표 가져오기
            verts = [self.maze_vertices[idx] for idx in face if idx < len(self.maze_vertices)]
            if not verts:
                continue

            # y좌표 최소값 확인 (0.1보다 크면 바닥에 닿지 않은 면 = 윗면)
            min_y = min(v[1] for v in verts)
            
            if min_y > 0.1:
                # 면의 중심점(X, Z) 계산
                avg_x = sum(v[0] for v in verts) / len(verts)
                avg_z = sum(v[2] for v in verts) / len(verts)
                
                # 그리드 인덱스로 변환
                gx = int((avg_x - min_x) / grid_scale)
                gz = int((avg_z - min_z) / grid_scale)
                
                if 0 <= gz < grid_height and 0 <= gx < grid_width:
                    self.maze_grid[gz][gx] = 1

        self.maze_width = grid_width
        self.maze_height = grid_height

    def _find_safe_spawn(self, near_top=True):
        """통로 셀에서 안전한 스폰 위치 찾기"""
        if not self.maze_grid or not self.maze_grid[0]:
            return [0.0, 0.0]

        grid_height = len(self.maze_grid)
        grid_width = len(self.maze_grid[0])

        # 패딩을 제외한 실제 미로 범위 (패딩은 +2이므로 마지막 2칸 제외)
        max_gz = grid_height - 3
        max_gx = grid_width - 3

        def is_valid_passage(gz, gx):
            """통로이면서 인접 셀에 벽이 있는지 확인 (미로 내부 판별)"""
            if self.maze_grid[gz][gx] != 0:
                return False
            # 인접 4방향 중 하나라도 벽이 있으면 미로 내부
            for dz, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nz, nx = gz + dz, gx + dx
                if 0 <= nz < grid_height and 0 <= nx < grid_width:
                    if self.maze_grid[nz][nx] == 1:
                        return True
            return False

        if near_top:
            # 시작점: 상단에서 첫 번째 유효 통로 찾기 (패딩 제외)
            for gz in range(max_gz + 1):
                for gx in range(max_gx + 1):
                    if is_valid_passage(gz, gx):
                        x = self.grid_min_x + (gx + 0.5) * self.grid_scale
                        z = self.grid_min_z + (gz + 0.5) * self.grid_scale
                        return [x, z]
        else:
            # 목표점: 하단에서 유효 통로 찾기 (패딩 제외)
            for gz in range(max_gz, -1, -1):
                for gx in range(max_gx, -1, -1):
                    if is_valid_passage(gz, gx):
                        x = self.grid_min_x + (gx + 0.5) * self.grid_scale
                        z = self.grid_min_z + (gz + 0.5) * self.grid_scale
                        return [x, z]

        # 유효한 통로를 찾지 못하면 중앙 반환
        center_x = self.grid_min_x + (grid_width / 2) * self.grid_scale
        center_z = self.grid_min_z + (grid_height / 2) * self.grid_scale
        return [center_x, center_z]

    def start_game(self):
        """게임 시작"""
        # 플레이어 시작 위치 설정
        self.player_pos = [self.start_pos[0], PLAYER_HEIGHT, self.start_pos[1]]
        self.player_yaw = 0.0  # 앞쪽(+Z 방향) 바라보기
        self.player_pitch = 0.0

        # 키 상태 초기화
        self.keys_pressed.clear()

        # 게임 활성화
        self.game_active = True

        # 마우스 캡처
        self.mouse_captured = True
        self.setMouseTracking(True)
        self.grabMouse()
        self.setCursor(Qt.BlankCursor)

        # 게임 루프 시작
        self.game_timer.start(GAME_TICK_MS)

        # 포커스 설정
        self.setFocus()

        print("게임 시작!")

    def stop_game(self):
        """게임 중지"""
        self.game_active = False
        self.game_timer.stop()

        # 마우스 해제
        self.mouse_captured = False
        self.setMouseTracking(False)
        self.releaseMouse()
        self.setCursor(Qt.ArrowCursor)

    def _update_game(self):
        """게임 루프 (타이머에서 호출)"""
        if not self.game_active:
            return

        # 날씨 업데이트
        if self.weather:
            # 60FPS 기준 dt approx 0.016
            dt = GAME_TICK_MS / 1000.0
            self.weather.update(dt, self.player_pos)

        # 이동 처리
        self._process_movement()

        # 목표 도달 체크
        self._check_goal()

        # 화면 갱신
        self.update()

    def _process_movement(self):
        """WASD 이동 처리"""
        if not self.keys_pressed:
            return

        # 이동 방향 (yaw 기준)
        forward_x = math.sin(self.player_yaw)
        forward_z = math.cos(self.player_yaw)
        right_x = math.cos(self.player_yaw)
        right_z = -math.sin(self.player_yaw)

        dx, dz = 0.0, 0.0

        if Qt.Key_W in self.keys_pressed:
            dx += forward_x * MOVE_SPEED
            dz += forward_z * MOVE_SPEED
        if Qt.Key_S in self.keys_pressed:
            dx -= forward_x * MOVE_SPEED
            dz -= forward_z * MOVE_SPEED
        if Qt.Key_A in self.keys_pressed:
            dx += right_x * MOVE_SPEED
            dz += right_z * MOVE_SPEED
        if Qt.Key_D in self.keys_pressed:
            dx -= right_x * MOVE_SPEED
            dz -= right_z * MOVE_SPEED

        # 충돌 감지 후 이동
        new_x = self.player_pos[0] + dx
        new_z = self.player_pos[2] + dz

        # X축 이동 체크
        if not self._check_collision(new_x, self.player_pos[2]):
            self.player_pos[0] = new_x

        # Z축 이동 체크
        if not self._check_collision(self.player_pos[0], new_z):
            self.player_pos[2] = new_z

    def _check_collision(self, x, z):
        """충돌 감지 (True면 충돌)"""
        if not self.maze_grid:
            return False

        # 플레이어 반경 내의 그리드 셀 체크
        for offset_x in [-PLAYER_RADIUS, 0, PLAYER_RADIUS]:
            for offset_z in [-PLAYER_RADIUS, 0, PLAYER_RADIUS]:
                check_x = x + offset_x
                check_z = z + offset_z

                gx = int((check_x - self.grid_min_x) / self.grid_scale)
                gz = int((check_z - self.grid_min_z) / self.grid_scale)

                # 범위 밖 = 충돌 (미로 밖으로 나갈 수 없음)
                if not (0 <= gz < len(self.maze_grid) and 0 <= gx < len(self.maze_grid[0])):
                    return True
                # 벽 충돌
                if self.maze_grid[gz][gx] == 1:
                    return True

        return False

    def _check_goal(self):
        """목표 도달 체크 (거리 제곱 비교로 sqrt 제거)"""
        dx = self.player_pos[0] - self.goal_pos[0]
        dz = self.player_pos[2] - self.goal_pos[1]
        # sqrt 제거: 거리 제곱과 반경 제곱 비교
        distance_sq = dx * dx + dz * dz
        goal_radius_sq = self.goal_radius * self.goal_radius

        if distance_sq < goal_radius_sq:
            self.stop_game()
            self.game_won.emit()

    def keyPressEvent(self, event):
        """키 누름 이벤트"""
        key = event.key()

        if not self.game_active:
            event.ignore()
            return

        if key in (Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D):
            self.keys_pressed.add(key)
            event.accept()
        elif key == Qt.Key_Escape:
            self.stop_game()
            event.accept()
        else:
            event.ignore()

    def keyReleaseEvent(self, event):
        """키 놓음 이벤트"""
        key = event.key()
        if key in self.keys_pressed:
            self.keys_pressed.discard(key)
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트 (시점 회전)"""
        if not self.game_active or not self.mouse_captured:
            return

        # 위젯 중앙
        center = QPoint(self.width() // 2, self.height() // 2)

        # 마우스 이동량
        dx = event.x() - center.x()
        dy = event.y() - center.y()

        # 시점 회전 (좌우 반전 수정: -= 사용)
        self.player_yaw -= dx * MOUSE_SENSITIVITY * 0.01
        self.player_pitch -= dy * MOUSE_SENSITIVITY * 0.01

        # pitch 제한 (-89° ~ 89°)
        max_pitch = math.radians(89)
        self.player_pitch = max(-max_pitch, min(max_pitch, self.player_pitch))

        # 마우스 중앙으로 이동
        global_center = self.mapToGlobal(center)
        QCursor.setPos(global_center)

    def focusOutEvent(self, event):
        """포커스 잃음 이벤트"""
        # 게임 중 포커스를 잃으면 마우스 캡처 해제
        if self.game_active:
            self.mouse_captured = False
            self.releaseMouse()
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        if self.game_active and not self.mouse_captured:
            # 게임 중 클릭하면 마우스 다시 캡처
            self.mouse_captured = True
            self.grabMouse()
            self.setCursor(Qt.BlankCursor)
            self.setFocus()


