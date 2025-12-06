import random

class Maze:
    """
    무작위 깊이 우선 탐색(Randomized DFS) 알고리즘을 사용하여 미로를 생성하는 클래스.
    """
    def __init__(self, width, height, wall_thickness=1.0, wall_height=1.0):
        """
        미로 객체를 초기화합니다.

        Args:
            width (int): 미로의 가로 크기.
            height (int): 미로의 세로 크기.
            wall_thickness (float): 벽 두께 (0.1 ~ 1.0, 기본값 1.0).
            wall_height (float): 벽 높이 (기본값 1.0).
        """
        # 미로의 벽과 길을 명확히 구분하기 위해 크기를 홀수로 조정합니다.
        self.width = width if width % 2 != 0 else width + 1
        self.height = height if height % 2 != 0 else height + 1
        # 벽 두께 및 높이 설정
        self.wall_thickness = max(0.1, min(1.0, wall_thickness))
        self.wall_height = max(0.1, wall_height)
        # 모든 칸을 벽(1)으로 채운 그리드를 생성합니다.
        self.grid = [[1 for _ in range(self.width)] for _ in range(self.height)]

    def generate(self):
        """
        미로를 생성합니다.
        """
        stack = []
        # 미로 생성을 시작할 임의의 지점(홀수 좌표)을 선택합니다.
        start_x = random.randint(0, (self.width - 3) // 2) * 2 + 1
        start_y = random.randint(0, (self.height - 3) // 2) * 2 + 1
        
        # 시작 지점을 길(0)로 만들고 스택에 추가합니다.
        self.grid[start_y][start_x] = 0
        stack.append((start_x, start_y))

        while stack:
            current_x, current_y = stack[-1]
            
            # 현재 위치에서 방문하지 않은 이웃을 찾습니다.
            neighbors = self._get_unvisited_neighbors(current_x, current_y)

            if neighbors:
                # 이웃이 있으면 무작위로 하나를 선택합니다.
                next_x, next_y = random.choice(neighbors)

                # 현재 위치와 다음 위치 사이의 벽을 허물어 길로 만듭니다.
                self.grid[(current_y + next_y) // 2][(current_x + next_x) // 2] = 0
                # 다음 위치를 길로 만들고 스택에 추가합니다.
                self.grid[next_y][next_x] = 0
                stack.append((next_x, next_y))
            else:
                # 더 이상 갈 곳이 없으면 스택에서 현재 위치를 꺼냅니다.
                stack.pop()
        
        # 입구와 출구를 생성합니다.
        self._create_entry_exit()

    def _get_unvisited_neighbors(self, x, y):
        """
        방문하지 않은 이웃 칸(2칸 거리)의 목록을 반환합니다.
        """
        neighbors = []
        for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
            nx, ny = x + dx, y + dy
            if 0 < nx < self.width - 1 and 0 < ny < self.height - 1 and self.grid[ny][nx] == 1:
                neighbors.append((nx, ny))
        return neighbors

    def _create_entry_exit(self):
        """
        미로의 입구와 출구를 생성합니다.
        """
        # 입구는 위쪽 벽의 두 번째 칸에 생성합니다.
        self.grid[0][1] = 0
        
        # 출구는 아래쪽 벽에서 길과 연결된 지점에 생성합니다.
        for i in range(self.width - 2, 0, -1):
            if self.grid[self.height - 2][i] == 0:
                self.grid[self.height - 1][i] = 0
                return
        # 만약 연결할 길을 찾지 못하면, 오른쪽 끝에 출구를 만듭니다.
        self.grid[self.height - 1][self.width - 2] = 0

    def display(self):
        """
        생성된 미로를 콘솔에 출력합니다.
        """
        for row in self.grid:
            # 벽(1)은 '█', 길(0)은 ' '로 표시합니다.
            print("".join(["██" if cell == 1 else "  " for cell in row]))

    def _is_wall(self, x, y):
        """주어진 좌표가 벽인지 확인합니다."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x] == 1
        return False

    def export_to_dat(self, filename, wall_thickness=None, wall_height=None):
        """
        생성된 미로를 3D 모델(.dat) 파일로 내보냅니다.
        벽 두께와 높이를 적용하여 큐브를 생성합니다.
        인접한 벽이 있으면 해당 방향으로 확장하여 틈이 생기지 않도록 합니다.

        Args:
            filename (str): 저장할 파일 경로.
            wall_thickness (float): 벽 두께 (0.1~1.0, 기본값 1.0).
            wall_height (float): 벽 높이 (기본값 1.0).
        """
        vertices = []
        faces = []

        # 미로 스케일 및 오프셋 설정 (중앙 정렬)
        scale = 1.0  # 그리드 셀 간격 (고정)
        thickness = wall_thickness if wall_thickness is not None else self.wall_thickness
        height = wall_height if wall_height is not None else self.wall_height
        thickness = max(0.1, min(1.0, thickness))  # 범위 제한
        height = max(0.1, height)
        inset = (scale - thickness) / 2  # 셀 내 벽 오프셋

        offset_x = -(self.width * scale) / 2
        offset_z = -(self.height * scale) / 2

        vertex_count = 0

        def add_box(x0, x1, z0, z1):
            """박스(큐브) 하나를 vertices와 faces에 추가"""
            nonlocal vertex_count
            # Bottom (y=0)
            v_bottom = [
                (x0, 0, z0), (x1, 0, z0),
                (x1, 0, z1), (x0, 0, z1)
            ]
            # Top (y=height)
            v_top = [
                (x0, height, z0), (x1, height, z0),
                (x1, height, z1), (x0, height, z1)
            ]
            vertices.extend(v_bottom + v_top)

            base = vertex_count
            faces.append((base+0, base+3, base+2, base+1))  # Bottom
            faces.append((base+4, base+5, base+6, base+7))  # Top
            faces.append((base+0, base+1, base+5, base+4))  # Front
            faces.append((base+1, base+2, base+6, base+5))  # Right
            faces.append((base+2, base+3, base+7, base+6))  # Back
            faces.append((base+3, base+0, base+4, base+7))  # Left
            vertex_count += 8

        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 1:  # 벽인 경우
                    # 기준 좌표 (셀의 왼쪽 하단)
                    bx = x * scale + offset_x
                    bz = y * scale + offset_z

                    # 중앙 박스 좌표
                    cx0 = bx + inset
                    cx1 = bx + inset + thickness
                    cz0 = bz + inset
                    cz1 = bz + inset + thickness

                    # 인접 벽 확인
                    left = self._is_wall(x - 1, y)
                    right = self._is_wall(x + 1, y)
                    up = self._is_wall(x, y - 1)
                    down = self._is_wall(x, y + 1)

                    # 수평 직선: 좌우만 연결 (상하 없음) - 하나의 박스로 병합
                    if (left or right) and not up and not down:
                        x0 = bx if left else cx0
                        x1 = bx + scale if right else cx1
                        add_box(x0, x1, cz0, cz1)

                    # 수직 직선: 상하만 연결 (좌우 없음) - 하나의 박스로 병합
                    elif (up or down) and not left and not right:
                        z0 = bz if up else cz0
                        z1 = bz + scale if down else cz1
                        add_box(cx0, cx1, z0, z1)

                    # 코너/T자/+자/고립: 중앙 박스 + 연결 팔 방식
                    else:
                        add_box(cx0, cx1, cz0, cz1)  # 중앙 박스
                        if left:
                            add_box(bx, cx0, cz0, cz1)
                        if right:
                            add_box(cx1, bx + scale, cz0, cz1)
                        if up:
                            add_box(cx0, cx1, bz, cz0)
                        if down:
                            add_box(cx0, cx1, cz1, bz + scale)

        try:
            with open(filename, 'w') as f:
                # 1. 설정 (v6 포맷)
                # v6 {slices} {axis} {render_mode} {r} {g} {b} {mode} {sweep_len} {twist} {caps}
                f.write("v6 30 Y 2 0.6 0.6 0.6 0 0 0 0\n")

                # 2. 경로 데이터 (0개 - SOR 생성 방지)
                f.write("0\n")
                
                # 3. 3D 정점 데이터
                f.write(f"{len(vertices)}\n")
                for v in vertices:
                    f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                
                # 4. 면 데이터
                f.write(f"{len(faces)}\n")
                for face in faces:
                    f.write(f"4 {face[0]} {face[1]} {face[2]} {face[3]}\n")
                    
            print(f"미로가 성공적으로 내보내졌습니다: {filename}")
        except Exception as e:
            print(f"내보내기 실패: {e}")

def create_maze():
    """
    사용자로부터 입력을 받아 미로를 생성하고 출력합니다.
    """
    try:
        width = int(input("미로의 가로 크기를 입력하세요 (5 이상): "))
        height = int(input("미로의 세로 크기를 입력하세요 (5 이상): "))

        if width < 5 or height < 5:
            print("오류: 미로의 가로와 세로 크기는 모두 5 이상이어야 합니다.")
            return None

        maze = Maze(width, height)
        maze.generate()
        
        print("\n[생성된 미로]")
        maze.display()
        return maze

    except ValueError:
        print("오류: 유효한 숫자를 입력해주세요.")
        return None

def main():
    """
    프로그램의 메인 함수. 사용자에게 메뉴를 보여주고 선택에 따라 동작합니다.
    """
    current_maze = None

    while True:
        print("\n[메뉴]")
        print("1. 새 미로 생성")
        if current_maze:
            print("2. 미로 내보내기 (.dat)")
        print("3. 종료")
        
        choice = input("원하는 작업을 선택하세요: ")

        if choice == '1':
            current_maze = create_maze()
        elif choice == '2' and current_maze:
            # 벽 두께 입력 (선택적, 기본값 1.0)
            thickness_input = input("벽 두께를 입력하세요 (0.1~1.0, 기본값 1.0): ").strip()
            wall_thickness = float(thickness_input) if thickness_input else 1.0

            # 벽 높이 입력 (선택적, 기본값 1.0)
            height_input = input("벽 높이를 입력하세요 (기본값 1.0): ").strip()
            wall_height = float(height_input) if height_input else 1.0

            # 파일 이름 입력
            filename = input("저장할 파일 이름을 입력하세요 (예: maze.dat): ")
            if not filename.endswith('.dat'):
                filename += '.dat'

            import os
            if not os.path.exists('datasets'):
                os.makedirs('datasets')

            filepath = os.path.join('datasets', filename)
            current_maze.export_to_dat(filepath, wall_thickness, wall_height)
        elif choice == '3':
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()
