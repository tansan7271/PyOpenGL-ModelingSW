import random

class Maze:
    """
    무작위 깊이 우선 탐색(Randomized DFS) 알고리즘을 사용하여 미로를 생성하는 클래스.
    """
    def __init__(self, width, height):
        """
        미로 객체를 초기화합니다.

        Args:
            width (int): 미로의 가로 크기.
            height (int): 미로의 세로 크기.
        """
        # 미로의 벽과 길을 명확히 구분하기 위해 크기를 홀수로 조정합니다.
        self.width = width if width % 2 != 0 else width + 1
        self.height = height if height % 2 != 0 else height + 1
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

    def export_to_dat(self, filename):
        """
        생성된 미로를 3D 모델(.dat) 파일로 내보냅니다.
        벽을 1x1x1 큐브로 변환하여 저장합니다.
        """
        vertices = []
        faces = []
        
        # 미로 스케일 및 오프셋 설정 (중앙 정렬)
        scale = 1.0
        height = 1.0
        offset_x = -(self.width * scale) / 2
        offset_z = -(self.height * scale) / 2
        
        vertex_count = 0
        
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 1: # 벽인 경우 큐브 생성
                    # 기준 좌표
                    bx = x * scale + offset_x
                    bz = y * scale + offset_z
                    
                    # 큐브의 8개 정점 생성
                    # Bottom (y=0)
                    v_bottom = [
                        (bx, 0, bz), (bx + scale, 0, bz), 
                        (bx + scale, 0, bz + scale), (bx, 0, bz + scale)
                    ]
                    # Top (y=height)
                    v_top = [
                        (bx, height, bz), (bx + scale, height, bz), 
                        (bx + scale, height, bz + scale), (bx, height, bz + scale)
                    ]
                    
                    vertices.extend(v_bottom + v_top)
                    
                    # 큐브의 6개 면 생성 (CCW Winding)
                    # 각 면은 4개의 정점 인덱스로 구성됨
                    base = vertex_count
                    
                    # Bottom (0, 3, 2, 1)
                    faces.append((base+0, base+3, base+2, base+1))
                    # Top (4, 5, 6, 7)
                    faces.append((base+4, base+5, base+6, base+7))
                    # Front (0, 1, 5, 4)
                    faces.append((base+0, base+1, base+5, base+4))
                    # Right (1, 2, 6, 5)
                    faces.append((base+1, base+2, base+6, base+5))
                    # Back (2, 3, 7, 6)
                    faces.append((base+2, base+3, base+7, base+6))
                    # Left (3, 0, 4, 7)
                    faces.append((base+3, base+0, base+4, base+7))
                    
                    vertex_count += 8

        try:
            with open(filename, 'w') as f:
                # 1. 설정 (v5 포맷 호환)
                f.write("30\n") # Slices (의미 없음)
                f.write("1\n")  # Axis Y
                f.write("2\n")  # Render Mode: Flat Shading
                f.write("0.6 0.6 0.6\n") # Color: Gray
                
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
            filename = input("저장할 파일 이름을 입력하세요 (예: maze.dat): ")
            if not filename.endswith('.dat'):
                filename += '.dat'
            
            import os
            if not os.path.exists('datasets'):
                os.makedirs('datasets')
                
            filepath = os.path.join('datasets', filename)
            current_maze.export_to_dat(filepath)
        elif choice == '3':
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()
