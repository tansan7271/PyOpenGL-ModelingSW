# SOR 모델 데이터 포맷 가이드 (v5)

이 문서는 PyOpenGL SOR Modeler에서 생성된 `.dat` 파일의 구조를 설명합니다. 이 포맷은 사용자가 그린 2D 프로파일 데이터와 이를 바탕으로 생성된 3D 메쉬 데이터를 모두 저장하는 데 사용됩니다.

## 파일 포맷 개요

이 파일은 일반 텍스트 파일이며, 각 줄마다 하나의 데이터 요소를 포함합니다. 데이터는 아래에 설명된 순서대로 순차적으로 기록되므로, 반드시 이 순서를 지켜서 파싱해야 합니다.

### 1. 전역 설정 (Global Settings)

| 줄 번호 | 설명                             | 타입       | 예시          | 비고                                                                |
| :------ | :------------------------------- | :--------- | :------------ | :------------------------------------------------------------------ |
| 1       | **단면 개수 (Number of Slices)** | `int`      | `30`          | 360도 회전을 몇 개의 구간으로 나눌지 결정하는 값입니다.             |
| 2       | **회전축 (Rotation Axis)**       | `int`      | `1`           | `0`: X축, `1`: Y축.                                                 |
| 3       | **렌더링 모드 (Render Mode)**    | `int`      | `3`           | `0`: 와이어프레임, `1`: 솔리드, `2`: 플랫 쉐이딩, `3`: 고로 쉐이딩. |
| 4       | **모델 색상 (Model Color)**      | `float` x3 | `1.0 0.0 0.0` | RGB 색상 값 (0.0 ~ 1.0). 공백으로 구분됩니다.                       |

### 2. 2D 프로파일 경로 (2D Profile Paths)

사용자가 2D 편집 모드에서 그린 곡선 데이터입니다.

| 줄 번호 | 설명                            | 타입  | 예시 | 비고                                  |
| :------ | :------------------------------ | :---- | :--- | :------------------------------------ |
| 5       | **경로 개수 (Number of Paths)** | `int` | `2`  | 그려진 프로파일 곡선의 총 개수입니다. |

**각 경로(Path)마다 아래 데이터가 반복됩니다:**

| 순서 | 설명                            | 타입       | 예시      | 비고                                          |
| :--- | :------------------------------ | :--------- | :-------- | :-------------------------------------------- |
| 1    | **점 개수 (Number of Points)**  | `int`      | `5`       | 해당 경로에 포함된 점의 개수입니다.           |
| 2    | **닫힘 여부 (Closed Flag)**     | `int`      | `1`       | `0`: 열린 곡선, `1`: 닫힌 도형.               |
| 3..N | **점 좌표 (Point Coordinates)** | `float` x2 | `1.5 2.0` | 점의 X, Y 좌표입니다. 점 개수만큼 반복됩니다. |

### 3. 3D 메쉬 데이터 - 정점 (Vertices)

생성된 3D 모델의 기하학적 정점 데이터입니다.

| 줄 번호 | 설명                               | 타입       | 예시          | 비고                                                 |
| :------ | :--------------------------------- | :--------- | :------------ | :--------------------------------------------------- |
| ...     | **정점 개수 (Number of Vertices)** | `int`      | `150`         | 생성된 3D 정점의 총 개수입니다.                      |
| ...     | **정점 좌표 (Vertex Coordinates)** | `float` x3 | `1.5 2.0 0.5` | 정점의 X, Y, Z 좌표입니다. 정점 개수만큼 반복됩니다. |

### 4. 3D 메쉬 데이터 - 면 (Faces)

정점 리스트의 인덱스를 사용하여 메쉬의 면(토폴로지)을 정의합니다.

| 줄 번호 | 설명                          | 타입     | 예시          | 비고                                                                                                                   |
| :------ | :---------------------------- | :------- | :------------ | :--------------------------------------------------------------------------------------------------------------------- |
| ...     | **면 개수 (Number of Faces)** | `int`    | `150`         | 생성된 면(사각형, Quad)의 총 개수입니다.                                                                               |
| ...     | **면 인덱스 (Face Indices)**  | `int` x5 | `4 0 1 31 30` | 형식: `<한 면의 점 개수> <v1> <v2> <v3> <v4>`<br>첫 번째 숫자는 항상 `4` (사각형)입니다.<br>인덱스는 0부터 시작합니다. |

## 파싱 예제 코드 (Python)

팀원들이 데이터를 쉽게 불러올 수 있도록 아래 Python 코드를 참고할 수 있습니다.

```python
def parse_sor_model(file_path):
    with open(file_path, 'r') as f:
        lines = [l.strip() for l in f.readlines()]

    idx = 0

    # 1. 전역 설정 읽기
    num_slices = int(lines[idx]); idx += 1
    rotation_axis = 'Y' if int(lines[idx]) == 1 else 'X'; idx += 1
    render_mode = int(lines[idx]); idx += 1
    color = list(map(float, lines[idx].split())); idx += 1

    # 2. 2D 경로 데이터 읽기
    num_paths = int(lines[idx]); idx += 1
    paths = []
    for _ in range(num_paths):
        num_points = int(lines[idx]); idx += 1
        is_closed = bool(int(lines[idx])); idx += 1
        points = []
        for _ in range(num_points):
            points.append(list(map(float, lines[idx].split())))
            idx += 1
        paths.append({'closed': is_closed, 'points': points})

    # 3. 3D 정점 데이터 읽기
    num_vertices = int(lines[idx]); idx += 1
    vertices = []
    for _ in range(num_vertices):
        vertices.append(list(map(float, lines[idx].split())))
        idx += 1

    # 4. 면 데이터 읽기
    num_faces = int(lines[idx]); idx += 1
    faces = []
    for _ in range(num_faces):
        # 형식: "4 v1 v2 v3 v4" -> 맨 앞의 '4'는 건너뜀
        indices = list(map(int, lines[idx].split()))[1:]
        faces.append(indices)
        idx += 1

    return {
        'settings': {'slices': num_slices, 'axis': rotation_axis, 'mode': render_mode, 'color': color},
        'paths': paths,
        'mesh': {'vertices': vertices, 'faces': faces}
    }
```
