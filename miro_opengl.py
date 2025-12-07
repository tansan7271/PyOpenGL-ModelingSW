# -*- coding: utf-8 -*-
"""
Miro Game OpenGL Widget - 1인칭 미로 게임
"""

import math
import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QCursor
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
        self.vbo_vertices = None
        self.vbo_normals = None
        self.vbo_indices = None
        self.vbo_wireframe_indices = None

        # VBO 메타데이터
        self.vbo_initialized = False
        self.index_count = 0
        self.wireframe_index_count = 0

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

        # 조명 설정
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 10.0, 0.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.7, 0.7, 0.7, 1.0])

        # 캐싱된 Quadric 생성 (목표 지점 렌더링용)
        self.goal_quadric = gluNewQuadric()
        gluQuadricNormals(self.goal_quadric, GLU_SMOOTH)

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
        """VBO를 사용한 최적화된 미로 렌더링"""
        if not self.vbo_initialized or self.index_count == 0:
            return

        # 1. Solid 면 렌더링
        glColor3f(0.6, 0.6, 0.6)  # 회색 벽

        # 정점 VBO 바인딩
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, None)

        # 법선 VBO 바인딩
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals)
        glEnableClientState(GL_NORMAL_ARRAY)
        glNormalPointer(GL_FLOAT, 0, None)

        # Solid 면 그리기
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_indices)
        glDrawElements(GL_QUADS, self.index_count, GL_UNSIGNED_INT, None)

        # 2. Wireframe 렌더링 (엣지 강조)
        glDisable(GL_LIGHTING)
        glColor3f(0.2, 0.2, 0.2)  # 어두운 엣지
        glLineWidth(1.0)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_wireframe_indices)
        glDrawElements(GL_LINES, self.wireframe_index_count, GL_UNSIGNED_INT, None)

        glEnable(GL_LIGHTING)

        # 정리
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
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
                    # closed flag 체크
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

                # 면 파싱
                num_f = int(lines[idx].strip())
                idx += 1
                self.maze_faces = []
                for _ in range(num_f):
                    parts = list(map(int, lines[idx].strip().split()))
                    self.maze_faces.append(parts[1:])  # 첫 번째는 정점 수
                    idx += 1

            # 법선 계산
            self._calculate_normals()

            # 미로 범위 계산 및 시작/목표 위치 설정
            self._calculate_maze_bounds()

            # VBO 생성 (기존 VBO 정리 후)
            self._cleanup_vbos()
            self._create_vbos()

            print(f"미로 로드 완료: {file_path}")
            print(f"정점: {len(self.maze_vertices)}, 면: {len(self.maze_faces)}")
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
        if self.vbo_vertices is not None:
            glDeleteBuffers(1, [self.vbo_vertices])
            self.vbo_vertices = None
        if self.vbo_normals is not None:
            glDeleteBuffers(1, [self.vbo_normals])
            self.vbo_normals = None
        if self.vbo_indices is not None:
            glDeleteBuffers(1, [self.vbo_indices])
            self.vbo_indices = None
        if self.vbo_wireframe_indices is not None:
            glDeleteBuffers(1, [self.vbo_wireframe_indices])
            self.vbo_wireframe_indices = None
        self.vbo_initialized = False
        self.index_count = 0
        self.wireframe_index_count = 0

    def _create_vbos(self):
        """미로 지오메트리로부터 VBO 생성"""
        if not self.maze_vertices or not self.maze_faces:
            return

        # 1. 정점 데이터 준비 (float32 배열)
        vertex_data = np.array(self.maze_vertices, dtype=np.float32).flatten()

        # 2. 법선 데이터 준비 (면 법선을 정점별로 확장)
        # 각 면의 4개 정점에 동일한 법선 적용
        normal_list = []
        for i, face in enumerate(self.maze_faces):
            if len(face) >= 4 and i < len(self.maze_normals):
                normal = self.maze_normals[i]
                for _ in range(4):
                    normal_list.extend(normal)

        # 정점별 법선 배열 생성 (정점 수만큼)
        vertex_normals = [[0.0, 1.0, 0.0] for _ in range(len(self.maze_vertices))]
        for i, face in enumerate(self.maze_faces):
            if len(face) >= 4 and i < len(self.maze_normals):
                normal = self.maze_normals[i]
                for idx in face[:4]:
                    if idx < len(vertex_normals):
                        vertex_normals[idx] = normal
        normal_data = np.array(vertex_normals, dtype=np.float32).flatten()

        # 3. GL_QUADS용 인덱스 데이터 준비
        index_list = []
        for face in self.maze_faces:
            if len(face) >= 4:
                index_list.extend(face[:4])
        index_data = np.array(index_list, dtype=np.uint32)
        self.index_count = len(index_data)

        # 4. Wireframe용 인덱스 데이터 준비 (GL_LINES)
        wire_index_list = []
        for face in self.maze_faces:
            if len(face) >= 4:
                wire_index_list.extend([
                    face[0], face[1],
                    face[1], face[2],
                    face[2], face[3],
                    face[3], face[0]
                ])
        wireframe_data = np.array(wire_index_list, dtype=np.uint32)
        self.wireframe_index_count = len(wireframe_data)

        # 5. VBO 생성
        self.vbo_vertices = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices)
        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL_STATIC_DRAW)

        self.vbo_normals = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals)
        glBufferData(GL_ARRAY_BUFFER, normal_data.nbytes, normal_data, GL_STATIC_DRAW)

        self.vbo_indices = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_indices)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, index_data.nbytes, index_data, GL_STATIC_DRAW)

        self.vbo_wireframe_indices = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_wireframe_indices)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, wireframe_data.nbytes, wireframe_data, GL_STATIC_DRAW)

        # 바인딩 해제
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
