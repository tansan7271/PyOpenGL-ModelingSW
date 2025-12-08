import numpy as np
from OpenGL.GL import *

class WeatherSystem:
    """
    플레이어 중심(Player-Centric) 날씨 파티클 시스템.
    
    비(Rain)와 눈(Snow) 효과를 제공하며, Numpy를 사용하여 
    수천 개의 파티클 업데이트를 벡터 연산으로 최적화합니다.
    """
    def __init__(self, max_particles=4000, extent=12.0):
        # max_particles: 파티클 개수 (이 값을 조절하여 비/눈의 밀도를 변경)
        self.max_particles = max_particles
        # extent: 플레이어 주변 파티클 생성 범위 (너무 넓으면 산만하고, 좁으면 비어보임)
        self.extent = extent 
        
        # 파티클 크기 설정 (여기서 크기를 조절하세요)
        self.snow_size = 7.0      # 눈송이 크기 (기본: 3.0 -> 5.0 -> 10.0)
        self.rain_width = 3.0     # 빗줄기 굵기 (기본: 1.0 -> 2.0 -> 3.0)
        self.rain_length = 0.8    # 빗줄기 길이 (기본: 0.5 -> 0.8)
        
        self.positions = np.zeros((max_particles, 3), dtype=np.float32)
        self.velocities = np.zeros((max_particles, 3), dtype=np.float32)
        self.active = False
        self.weather_type = "Clear"
        
        # 렌더링 최적화를 위한 배열 버퍼
        self.draw_pos_buffer = None

    def set_weather(self, type_name):
        """날씨 설정 (Clear, Rain, Snow)"""
        self.weather_type = type_name
        self.active = (type_name != "Clear")
        
        if not self.active:
            return

        # 파티클 초기화
        # 범위: (-extent, -2.0, -extent) ~ (extent, 15.0, extent)
        self.positions[:, 0] = np.random.uniform(-self.extent, self.extent, self.max_particles)
        self.positions[:, 1] = np.random.uniform(-2.0, 15.0, self.max_particles) # 높이 -2~15
        self.positions[:, 2] = np.random.uniform(-self.extent, self.extent, self.max_particles)

        if type_name == "Rain":
            # 비: 빠른 수직 하강
            self.velocities[:, 0] = 0.0
            self.velocities[:, 1] = -20.0 # 더 빠른 낙하 속도 (-15 -> -20)
            self.velocities[:, 2] = 0.0
            
        elif type_name == "Snow":
            # 눈: 느린 하강 + 약간의 흔들림 (update에서 추가 처리)
            self.velocities[:, 0] = 0.0
            self.velocities[:, 1] = -2.0 # 느린 낙하 속도
            self.velocities[:, 2] = 0.0

    def update(self, delta_time, player_pos):
        """
        파티클의 위치를 업데이트하고 플레이어 위치를 기준으로 Wrapping합니다.

        Args:
            delta_time (float): 마지막 업데이트 이후 경과된 시간 (초).
            player_pos (tuple): 플레이어의 (x, y, z) 위치.
        """
        if not self.active:
            return

        px, py, pz = player_pos
        
        # 1. 물리 업데이트 (위치 += 속도 * dt)
        self.positions += self.velocities * delta_time

        # 눈일 경우 약간의 난수성 추가 (흔들림)
        if self.weather_type == "Snow":
            noise = np.random.uniform(-0.5, 0.5, (self.max_particles, 3)) * delta_time
            noise[:, 1] = 0 # Y축 흔들림 제거
            self.positions += noise

        # 2. Wrapping Logic (플레이어 중심)
        # 플레이어 위치를 원점으로 하는 로컬 좌표계로 생각
        
        # X축 Wrapping (플레이어보다 너무 멀어지면 반대편으로 이동)
        rel_x = self.positions[:, 0] - px
        self.positions[:, 0] = px + ((rel_x + self.extent) % (2 * self.extent)) - self.extent
        
        # Z축 Wrapping
        rel_z = self.positions[:, 2] - pz
        self.positions[:, 2] = pz + ((rel_z + self.extent) % (2 * self.extent)) - self.extent

        # Y축 Reset (바닥 뚫고 가면 위로)
        floor_y = -2.0 # 바닥보다 조금 아래까지 떨어지게
        ceiling_y = 15.0 # 생성 높이를 더 높게
        
        under_floor = self.positions[:, 1] < floor_y
        self.positions[under_floor, 1] += (ceiling_y - floor_y) # 위로 이동 (범위만큼 더하기)

    def draw(self):
        """날씨 렌더링 (GL_LINES or GL_POINTS)"""
        if not self.active:
            return

        glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT)
        glDisable(GL_LIGHTING) # 파티클은 자체 발광처럼 보이게
        glDisable(GL_TEXTURE_2D)
        
        glEnableClientState(GL_VERTEX_ARRAY)

        if self.weather_type == "Rain":
            glColor4f(0.7, 0.7, 0.8, 0.6) # 약간 푸른 회색, 반투명
            glLineWidth(self.rain_width) # 빗줄기 굵기 적용

            # 비는 선으로 그리기 위해 (pos)와 (pos + up_vector * length) 두 점 필요
            # 그러나 성능을 위해 GL_LINES 대신 단순히 점만 그리면 잘 안보임.
            # 여기서는 간단히 점을 그리거나, 혹은 속도 벡터를 이용해 선을 그림.
            # Numpy로 두 점 배열을 만드는 것이 빠름.
            
            # 빗줄기 길이
            start_points = self.positions
            end_points = self.positions + np.array([0, self.rain_length, 0], dtype=np.float32)
            
            # [P1, P2, P3, P4 ...] 형태로 인터리빙
            # stack을 써서 (N, 2, 3) -> reshape (2N, 3)
            lines = np.stack((start_points, end_points), axis=1).reshape(-1, 3)
            
            glVertexPointer(3, GL_FLOAT, 0, lines)
            glDrawArrays(GL_LINES, 0, len(lines))

        elif self.weather_type == "Snow":
            glColor4f(1.0, 1.0, 1.0, 0.8) # 흰색
            glPointSize(self.snow_size) # 눈송이 크기 적용
            
            glVertexPointer(3, GL_FLOAT, 0, self.positions)
            glDrawArrays(GL_POINTS, 0, self.max_particles)

        glDisableClientState(GL_VERTEX_ARRAY)
        glPopAttrib()
