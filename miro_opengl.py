# -*- coding: utf-8 -*-
"""
Miro Game OpenGL Widget - 1인칭 미로 게임
"""

import math
import os
import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QCursor, QImage

from OpenGL.GL import *
from OpenGL.GLU import *

# 게임 상수
PLAYER_HEIGHT = 0.8       # 눈높이
PLAYER_RADIUS = 0.25      # 충돌 반경
MOVE_SPEED = 0.08         # 이동 속도
MOUSE_SENSITIVITY = 0.15  # 마우스 감도
GAME_TICK_MS = 16         # ~60 FPS


class MiroOpenGLWidget(QOpenGLWidget):
    """
    1인칭 미로 게임을 위한 OpenGL 위젯.
    WASD로 이동, 마우스로 시점 회전.
    """

    # 시그널: 게임 클리어 시 발생
    game_won = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 플레이어 상태
        self.player_pos = [0.0, PLAYER_HEIGHT, 0.0]  # x, y, z
        self.player_yaw = 0.0      # 좌우 회전 (라디안)
        self.player_pitch = 0.0    # 상하 회전 (라디안)

        # 키 입력 상태
        self.keys_pressed = set()

        # 미로 데이터
        self.maze_vertices = []
        self.maze_faces = []
        self.maze_normals = []
        self.maze_width = 0
        self.maze_height = 0
        self.maze_grid = []  # 충돌 감지용 2D 그리드 (재구성)
        self.grid_min_x = 0.0
        self.grid_min_z = 0.0
        self.grid_scale = 1.0

        # 시작/목표 위치
        self.start_pos = [0.0, 0.0]   # x, z
        self.goal_pos = [0.0, 0.0]    # x, z
        self.goal_radius = 0.5        # 목표 도달 판정 반경

        # 게임 상태
        self.game_active = False
        self.mouse_captured = False
        self.last_mouse_pos = None

        # 게임 루프 타이머
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self._update_game)

        # 키보드 포커스 설정
        self.setFocusPolicy(Qt.StrongFocus)

        # VBO IDs
        self.vbo_wall_vertices = None
        self.vbo_wall_uvs = None
        self.vbo_wall_normals = None
        self.vbo_floor_vertices = None
        self.vbo_floor_uvs = None
        self.vbo_floor_normals = None
        self.vbo_wireframe_indices = None
        
        # 텍스처 ID
        self.texture_wall = None
        self.texture_floor = None

        # VBO 메타데이터
        self.vbo_initialized = False
        self.wall_count = 0
        self.floor_count = 0

        # 캐싱된 Quadric (목표 지점 렌더링용)
        self.goal_quadric = None

    def initializeGL(self):
        """OpenGL 초기화"""
        glClearColor(0.1, 0.1, 0.15, 1.0)  # 어두운 배경
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        glEnable(GL_TEXTURE_2D) # 텍스처 활성화

        # 조명 설정
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 10.0, 0.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0]) # 조금 더 밝게
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.7, 0.7, 0.7, 1.0])

        # 캐싱된 Quadric 생성 (목표 지점 렌더링용)
        self.goal_quadric = gluNewQuadric()
        gluQuadricNormals(self.goal_quadric, GLU_SMOOTH)
        
        # 텍스처 로드
        self._load_textures()

    def _load_textures(self):
        """텍스처 이미지 로드 및 OpenGL 텍스처 생성"""
        import os
        base_path = os.path.dirname(__file__)
        assets_path = os.path.join(base_path, 'assets')
        
        self.texture_wall = self._create_texture(os.path.join(assets_path, 'wall_texture.png'))
        self.texture_floor = self._create_texture(os.path.join(assets_path, 'floor_texture.png'))

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
        
        print(f"Texture loaded: {file_path} (ID: {texture_id})")
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

        # 1인칭 카메라 설정
        self._setup_camera()

        # 미로 렌더링
        self._draw_maze()

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
        """VBO를 사용한 텍스처 미로 렌더링"""
        if not self.vbo_initialized:
            return

        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        
        glColor3f(1.0, 1.0, 1.0) # 텍스처 색상 혼합 방지 (흰색)

        # 1. 벽 렌더링
        if self.wall_count > 0 and self.texture_wall:
            glBindTexture(GL_TEXTURE_2D, self.texture_wall)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_wall_vertices)
            glVertexPointer(3, GL_FLOAT, 0, None)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_wall_normals)
            glNormalPointer(GL_FLOAT, 0, None)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_wall_uvs)
            glTexCoordPointer(2, GL_FLOAT, 0, None)
            
            glDrawArrays(GL_QUADS, 0, self.wall_count)

        # 2. 바닥 렌더링
        if self.floor_count > 0 and self.texture_floor:
            glBindTexture(GL_TEXTURE_2D, self.texture_floor)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_floor_vertices)
            glVertexPointer(3, GL_FLOAT, 0, None)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_floor_normals)
            glNormalPointer(GL_FLOAT, 0, None)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_floor_uvs)
            glTexCoordPointer(2, GL_FLOAT, 0, None)
            
            glDrawArrays(GL_QUADS, 0, self.floor_count)

        # 3. Wireframe (옵션, 현재 비활성화 - VBO 인덱스 불일치 문제 방지)
        # if self.wireframe_index_count > 0:
        #    glDisable(GL_TEXTURE_2D)
        #    ...

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
        glTranslatef(self.goal_pos[0], 0.5, self.goal_pos[1])

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

            # 법선 계산 (원본 면 기준)
            self._calculate_normals()

            # 미로 범위 계산 및 시작/목표 위치 설정
            self._calculate_maze_bounds()

            # VBO 생성 (분류된 면 사용)
            self._cleanup_vbos()
            self._create_vbos(wall_faces, floor_faces)

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
        """VBO 리소스 정리"""
        vbo_list = [
            self.vbo_wall_vertices, self.vbo_wall_uvs, self.vbo_wall_normals,
            self.vbo_floor_vertices, self.vbo_floor_uvs, self.vbo_floor_normals,
            self.vbo_wireframe_indices
        ]
        
        for vbo in vbo_list:
            if vbo is not None:
                glDeleteBuffers(1, [vbo])
        
        self.vbo_wall_vertices = None
        self.vbo_wall_uvs = None
        self.vbo_wall_normals = None
        self.vbo_floor_vertices = None
        self.vbo_floor_uvs = None
        self.vbo_floor_normals = None
        self.vbo_wireframe_indices = None
        
        self.vbo_initialized = False
        self.wall_count = 0
        self.floor_count = 0
        self.wireframe_index_count = 0

    def _create_vbos(self, wall_faces, floor_faces):
        """벽과 바닥을 분리하여 VBO 생성 (UV 포함)"""
        if not self.maze_vertices:
            return

        def generate_geometry(faces, is_wall=True):
            v_list = []
            uv_list = []
            n_list = []
            
            for i, face in enumerate(faces):
                if len(face) < 4: continue
                
                # 면 정점 좌표
                p0 = self.maze_vertices[face[0]]
                p1 = self.maze_vertices[face[1]]
                p2 = self.maze_vertices[face[2]]
                p3 = self.maze_vertices[face[3]]
                
                # 법선 계산 (평면 노멀)
                # v1-v0 x v2-v0
                u = [p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]]
                v = [p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]]
                nx = u[1]*v[2] - u[2]*v[1]
                ny = u[2]*v[0] - u[0]*v[2]
                nz = u[0]*v[1] - u[1]*v[0]
                length = math.sqrt(nx*nx + ny*ny + nz*nz)
                if length > 0:
                    normal = [nx/length, ny/length, nz/length]
                else:
                    normal = [0, 1, 0]
                
                # 정점 추가 (Explode)
                v_list.extend(p0 + p1 + p2 + p3)
                
                # 법선 추가
                for _ in range(4):
                    n_list.extend(normal)
                
                # UV 계산 (World Space 매핑)
                if abs(normal[1]) > 0.9: # 바닥 또는 바닥면 (수평)
                    # XZ 평면 매핑
                    scale = 0.5 # 텍스처 스케일 
                    uv_list.extend([p0[0]*scale, p0[2]*scale])
                    uv_list.extend([p1[0]*scale, p1[2]*scale])
                    uv_list.extend([p2[0]*scale, p2[2]*scale])
                    uv_list.extend([p3[0]*scale, p3[2]*scale])
                else: # 벽 (수직)
                    # Box Mapping 비슷한 로직 - normal 방향에 따라 투영
                    scale_x = 0.5
                    scale_y = 0.5
                    if abs(normal[0]) > 0.5: # YZ 평면
                        uv_list.extend([p0[2]*scale_x, p0[1]*scale_y])
                        uv_list.extend([p1[2]*scale_x, p1[1]*scale_y])
                        uv_list.extend([p2[2]*scale_x, p2[1]*scale_y])
                        uv_list.extend([p3[2]*scale_x, p3[1]*scale_y])
                    else: # XY 평면 (Normal Z)
                        uv_list.extend([p0[0]*scale_x, p0[1]*scale_y])
                        uv_list.extend([p1[0]*scale_x, p1[1]*scale_y])
                        uv_list.extend([p2[0]*scale_x, p2[1]*scale_y])
                        uv_list.extend([p3[0]*scale_x, p3[1]*scale_y])

            return np.array(v_list, dtype=np.float32), np.array(uv_list, dtype=np.float32), np.array(n_list, dtype=np.float32)

        # 1. 벽 지오메트리 생성
        wall_v, wall_uv, wall_n = generate_geometry(wall_faces, is_wall=True)
        self.wall_count = len(wall_v) // 3
        
        # 2. 바닥 지오메트리 생성
        floor_v, floor_uv, floor_n = generate_geometry(floor_faces, is_wall=False)
        self.floor_count = len(floor_v) // 3
        
        # VBO 생성 및 데이터 업로드
        def create_buffer(data):
            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)
            return vbo

        if self.wall_count > 0:
            self.vbo_wall_vertices = create_buffer(wall_v)
            self.vbo_wall_uvs = create_buffer(wall_uv)
            self.vbo_wall_normals = create_buffer(wall_n)

        if self.floor_count > 0:
            self.vbo_floor_vertices = create_buffer(floor_v)
            self.vbo_floor_uvs = create_buffer(floor_uv)
            self.vbo_floor_normals = create_buffer(floor_n)

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

        # 상단(near_top=True)이면 z 인덱스 0부터, 하단이면 끝에서부터 탐색
        z_range = range(len(self.maze_grid)) if near_top else range(len(self.maze_grid) - 1, -1, -1)
        # 출구는 오른쪽에서 왼쪽으로 탐색해서 만들어지므로, 목표점도 오른쪽부터 탐색
        x_range = range(len(self.maze_grid[0])) if near_top else range(len(self.maze_grid[0]) - 1, -1, -1)

        for gz in z_range:
            for gx in x_range:
                if self.maze_grid[gz][gx] == 0:  # 통로 셀
                    # 셀 중앙 좌표 계산
                    x = self.grid_min_x + (gx + 0.5) * self.grid_scale
                    z = self.grid_min_z + (gz + 0.5) * self.grid_scale
                    return [x, z]

        # 통로를 찾지 못하면 중앙 반환
        center_x = self.grid_min_x + (len(self.maze_grid[0]) / 2) * self.grid_scale
        center_z = self.grid_min_z + (len(self.maze_grid) / 2) * self.grid_scale
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

                if 0 <= gz < len(self.maze_grid) and 0 <= gx < len(self.maze_grid[0]):
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

    def cleanup_gl_resources(self):
        """OpenGL 리소스 정리 (위젯 소멸 시 호출)"""
        self._cleanup_vbos()
        if self.goal_quadric:
            gluDeleteQuadric(self.goal_quadric)
            self.goal_quadric = None
            
        # 텍스처 삭제
        if self.texture_wall:
            glDeleteTextures([self.texture_wall])
            self.texture_wall = None
        if self.texture_floor:
            glDeleteTextures([self.texture_floor])
            self.texture_floor = None
