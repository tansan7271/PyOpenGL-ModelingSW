# SOR 모델러 개발 보고서 (상세 기술 명세)

이 문서는 최종 보고서 작성 및 다이어그램(Class Diagram, Sequence Diagram) 작성을 돕기 위해 시스템의 구조와 동작 원리를 상세하게 기술한 문서입니다.

## 1. 시스템 아키텍처 (System Architecture)

본 시스템은 **MVC (Model-View-Controller)** 패턴을 변형하여 구현되었습니다.

### 1.1. 클래스 구조 (Class Structure)

#### `MainWindow` (View & Controller)

- **역할:** 사용자 인터페이스(UI) 관리 및 사용자 입력 처리.
- **주요 속성 (Attributes):**
  - `glWidget`: `OpenGLWidget` 인스턴스 (Central Widget).
  - `toolbar`: 상단 툴바 (2D/3D 전환, 저장/불러오기).
  - `dock_widget`: 우측 컨트롤 패널 컨테이너.
  - `spin_slices`: 단면 개수 설정 `QSpinBox`.
  - `radio_x/y_axis`: 회전축 선택 `QRadioButton`.
  - `combo_render_mode`: 렌더링 모드 선택 `QComboBox`.
  - `btn_color_picker`: 색상 변경 `QPushButton`.
- **주요 메서드 (Methods):**
  - `_setup_ui()`: UI 초기화 및 레이아웃 배치.
  - `_connect_signals()`: UI 시그널과 `OpenGLWidget` 슬롯 연결.
  - `_on_view_mode_changed(mode)`: 뷰 모드에 따라 UI 활성/비활성 상태 변경.
  - `_update_point_list()`: `glWidget.points` 데이터를 기반으로 점 목록 UI 갱신.

#### `OpenGLWidget` (Model & View)

- **역할:** 데이터 관리(Model) 및 3D 렌더링(View).
- **주요 속성 (Attributes):**
  - **State:** `view_mode` ('2D'/'3D'), `render_mode` (Wire/Solid/Flat/Gouraud).
  - **Data:** `paths` (2D 프로파일), `sor_vertices` (3D 정점), `sor_faces` (3D 면).
  - **Settings:** `num_slices`, `rotation_axis`, `model_color`.
- **주요 메서드 (Methods):**
  - **Lifecycle:** `initializeGL` (초기화), `resizeGL` (투영 설정), `paintGL` (렌더링 루프).
  - **Input:** `mousePressEvent` (점 추가/선택), `mouseMoveEvent` (드래그).
  - **Logic:** `generate_sor_model` (3D 메쉬 생성), `calculate_normals` (법선 계산).

### 1.2. 클래스 다이어그램 (Class Diagram Description)

- `MainWindow`는 `OpenGLWidget`을 **포함(Composite)**합니다.
- `MainWindow`는 `OpenGLWidget`의 **Public Methods** (`set_view_mode`, `clear_points` 등)를 호출하여 상태를 변경합니다.
- `OpenGLWidget`은 **Signals** (`viewModeChanged`, `pointsChanged`)를 통해 `MainWindow`에 상태 변화를 알립니다.

---

## 2. 제어 흐름 (Control Flow)

### 2.1. 3D 모델 생성 시퀀스 (Sequence: Create SOR Model)

1.  **User**: 툴바의 '3D View' 버튼 클릭.
2.  **MainWindow**: `glWidget.set_view_mode('3D')` 호출.
3.  **OpenGLWidget**:
    1.  `view_mode`를 '3D'로 변경.
    2.  `generate_sor_model()` 실행:
        - 2D `paths` 데이터를 읽음.
        - 회전 알고리즘을 적용하여 `sor_vertices`, `sor_faces` 생성.
        - `calculate_normals()` 실행하여 조명용 법선 벡터 계산.
    3.  `viewModeChanged.emit('3D')` 시그널 발생.
    4.  `update()` 호출 -> `paintGL()` 트리거.
4.  **MainWindow**: `viewModeChanged` 시그널 수신 -> `_on_view_mode_changed('3D')` 실행 (2D 컨트롤 숨김, 3D 컨트롤 표시).
5.  **OpenGLWidget (paintGL)**:
    - `setupProjection()`: `gluPerspective`로 원근 투영 설정.
    - `gluLookAt()`: 카메라 위치 설정.
    - `glLightfv()`: 조명(Key/Fill Light) 위치 설정.
    - `draw_sor_model()`: 생성된 메쉬 렌더링.

### 2.2. 점 편집 시퀀스 (Sequence: Edit Points)

1.  **User**: 2D 뷰에서 화면 클릭.
2.  **OpenGLWidget**: `mousePressEvent` 발생.
    - 클릭된 화면 좌표 $(x, y)$를 `glOrtho` 역변환을 통해 월드 좌표 $(wx, wy)$로 변환.
    - **Hit Test**: 기존 점 근처 클릭 시 `dragging_point` 설정 (드래그 모드).
    - **New Point**: 빈 공간 클릭 시 현재 `paths`에 점 추가.
    - `pointsChanged.emit()` 시그널 발생.
    - `update()` 호출.
3.  **MainWindow**: `pointsChanged` 시그널 수신 -> `_update_point_list()` 실행 (우측 패널의 점 목록 UI 갱신).

---

## 3. 핵심 알고리즘 (Core Algorithms)

### 3.1. SOR 메쉬 생성 (Mesh Generation)

2D 프로파일 점 $P(x, y)$를 회전축을 기준으로 $\theta$만큼 회전시켜 3D 정점 $V(x', y', z')$를 생성합니다.

- **파라미터:**

  - $N$: 단면 개수 (`num_slices`)
  - $\Delta\theta = 360^\circ / N$: 회전 각도 간격
  - $k$: 현재 단면 인덱스 ($0 \le k < N$)

- **회전 변환 공식 (Y축 기준):**
  $$ \theta_k = k \times \Delta\theta $$
  $$ x' = x \cdot \cos(\theta_k) $$
  $$ y' = y $$
  $$ z' = -x \cdot \sin(\theta_k) $$

- **면 구성 (Topology):**
  인접한 두 단면 $k, k+1$과 프로파일의 두 점 $i, i+1$을 연결하여 사각형(Quad)을 생성합니다.
  - $V_{k, i}$: $k$번째 단면의 $i$번째 점
  - **Face Indices:** $[V_{k, i}, V_{k, i+1}, V_{k+1, i+1}, V_{k+1, i}]$

### 3.2. 스윕 곡면 생성 (Sweep Surface Generation)

2D 프로파일 점 $P(x, y)$를 Z축 방향으로 밀어내면서(Extrude) 동시에 회전(Twist)시켜 3D 형상을 생성합니다.

- **파라미터:**

  - $L$: 길이 (`sweep_length`)
  - $T_{total}$: 총 비틀림 각도 (`sweep_twist`)
  - $S$: 단계 수 (Steps, 고정값 30)

- **변환 공식:**
  각 단계 $k$ ($0 \le k \le S$)에서의 정점 위치 계산:
  $$ t = k / S $$
  $$ z = (t - 0.5) \times L $$
  $$ \theta = t \times T\_{total} $$
  $$ x' = x \cos\theta - y \sin\theta $$
  $$ y' = x \sin\theta + y \cos\theta $$
  $$ z' = z $$

- **캡(Caps) 생성:**
  - **Start Cap:** $z = -L/2$ 위치에 중심점을 추가하고, 첫 번째 레이어의 점들과 연결 (역순).
  - **End Cap:** $z = +L/2$ 위치에 중심점을 추가하고, 마지막 레이어의 점들과 연결 (정순).

### 3.2. 법선 벡터 계산 (Normal Calculation)

조명 효과(Shading)를 위해 각 면 또는 정점의 수직 벡터(Normal Vector)를 계산합니다.

- **Flat Shading:**

  - 한 면(Face)을 구성하는 세 점 $v1, v2, v3$를 선택.
  - 두 벡터 $U = v2 - v1$, $V = v3 - v1$ 계산.
  - 외적(Cross Product) $N = U \times V$ 계산 후 정규화(Normalize).
  - 해당 면의 모든 정점에 동일한 $N$ 적용.

- **Gouraud Shading:**
  - 한 정점을 공유하는 모든 인접 면들의 법선 벡터를 평균냄.
  - $N_{vertex} = \frac{\sum N_{face}}{Count}$
  - 정점마다 부드럽게 이어지는 법선 벡터를 가짐.

---

## 4. 데이터 구조 (Data Structures)

### 4.1. 2D 프로파일 데이터 (`self.paths`)

다중 경로를 지원하기 위해 리스트의 리스트 구조를 사용합니다.

```python
[
    {
        'points': [(x1, y1), (x2, y2), ...],  # 점 좌표 리스트
        'closed': True                        # 닫힌 도형 여부
    },
    {
        'points': [(x3, y3), ...],
        'closed': False
    }
]
```

### 4.2. 모델링 설정 데이터 (v6 Format)

- **Modeling Mode**: 0 (SOR) / 1 (Sweep)
- **Sweep Parameters**:
  - `sweep_length`: 길이 (float)
  - `sweep_twist`: 비틀림 각도 (float)
  - `sweep_caps`: 캡 여부 (bool)

### 4.3. 3D 메쉬 데이터

OpenGL 렌더링에 최적화된 플랫 리스트 구조입니다.

- **`self.sor_vertices`**: `[(x, y, z), ...]` (모든 단면의 정점들이 순차적으로 저장됨)
- **`self.sor_faces`**: `[[v1_idx, v2_idx, v3_idx, v4_idx], ...]` (정점 인덱스로 구성된 사각형 면 리스트)

---

## 5. 렌더링 파이프라인 (Rendering Pipeline)

`paintGL` 메서드에서 매 프레임 실행되는 과정입니다.

1.  **State Setup**:
    - `glDepthMask(GL_TRUE)`: 깊이 버퍼 쓰기 활성화.
    - `glClear(...)`: 컬러 및 깊이 버퍼 초기화.
2.  **Projection**:
    - 2D 모드: `glOrtho` (직교 투영).
    - 3D 모드: `gluPerspective` (원근 투영).
3.  **View Transform**:
    - 3D 모드: `gluLookAt(eye, center, up)`으로 카메라 위치 설정.
4.  **Lighting**:
    - `glLightfv`로 `GL_LIGHT0` (Key), `GL_LIGHT1` (Fill) 위치 설정.
5.  **Model Rendering**:
    - **Wireframe**: `glPolygonMode(..., GL_LINE)`
    - **Solid**: `glDisable(GL_LIGHTING)` + `glColor`
    - **Flat/Gouraud**: `glEnable(GL_LIGHTING)` + `glShadeModel(GL_FLAT/SMOOTH)` + `glNormal`

---

## 6. UI/UX 고도화 기술 (Advanced UI/UX Techniques)

### 6.1. 동적 테마 시스템 (Dynamic Theme System)

OS의 라이트/다크 모드 전환을 실시간으로 감지하고 애플리케이션 스타일을 즉시 반영하는 시스템입니다.

- **Event Handling:** `changeEvent(QEvent)` 메서드를 오버라이드하여 `QEvent.ApplicationPaletteChange` 이벤트를 감지합니다.
- **Theme Detection:** `QApplication.palette().color(QPalette.Window).lightness()` 값이 128 미만이면 다크 모드로 판단합니다.
- **Adaptive Styling:** 감지된 모드에 따라 UI 컴포넌트(사이드바, 리스트 아이템)의 배경색, 경계선, 텍스트 색상 변수를 런타임에 교체합니다.

### 6.2. 프로그래머틱 아이콘 틴팅 (Programmatic Icon Tinting)

별도의 아이콘 리소스(흰색/검은색)를 두지 않고, 코드로 아이콘 색상을 실시간 변경하여 리소스 효율성과 유연성을 확보했습니다.

- **Algorithm:**
  1. 원본 아이콘 이미지(`QPixmap`)를 로드합니다.
  2. 투명한 `QPixmap` 버퍼를 생성합니다.
  3. `QPainter`로 원본 이미지를 그립니다.
  4. **Composition Mode**: `QPainter.CompositionMode_SourceIn`을 설정합니다. 이 모드는 소스(색상)를 그릴 때 목적지(원본 아이콘)의 불투명한 부분에만 그려지도록 마스킹합니다.
  5. `fillRect`로 원하는 색상(테마에 따른 흰색 또는 회색)을 칠하여 아이콘의 형태만 남기고 색상을 변경합니다.
- **State Management:** `QIcon` 객체 생성 시 `Normal` 상태와 `Selected` 상태에 대해 각각 다른 색상으로 틴팅된 픽스맵을 할당하여, 사용자가 아이콘을 선택했을 때의 시각적 피드백을 명확히 합니다.

### 6.3. 미로 게임 UI 개선 (Maze Game UI Refinement)

- **QMainWindow 상속 전환**: `MiroWindow`의 상속 클래스를 `QWidget`에서 `QMainWindow`로 변경하여 `QToolBar` 및 표준 윈도우 기능을 올바르게 지원하도록 구조를 개선했습니다.
- **QToolBar 통합**: 기존의 `QMenuBar`를 `QToolBar`로 교체하여 3D 모델러와 동일한 심미적 일관성을 확보했습니다. 'View Mode'는 `InstantPopup` 모드의 `QToolButton`을 사용하여 드롭다운 메뉴로, 'Minimap'은 표준 `QAction`을 사용하여 토글 버튼으로 구현했습니다.
- **레이아웃 관리**: `setCentralWidget`을 사용하여 메인 레이아웃 컨테이너를 설정함으로써, 기존의 중첩된 레이아웃 구조를 단순화하고 표준화했습니다.
- **동적 UI 요소**: 설정 항목을 체계적으로 정리하기 위해 중첩된 `QGroupBox`를 구현하고, 툴바에 '타이틀로 복귀' 기능을 직접 추가하여 사용자 편의성을 높였습니다.

### 6.4. 크로스 플랫폼 호환성 (Cross-Platform Compatibility)

- **Windows UI 렌더링 대응**: Windows 환경에서의 폰트 렌더링 차이로 인한 UI 잘림 현상을 해결하기 위해, `QGroupBox`의 너비를 확장하고 `QToolButton`에 CSS 패딩을 적용하여 시각적 공간을 확보했습니다.
- **OpenGL 데이터 안정성**: Windows OpenGL 드라이버의 엄격한 타입 체크로 인한 크래시를 방지하기 위해, 모든 정점 데이터(`glVertex3f`)에 대해 명시적인 `float` 형변환을 적용했습니다. 또한, `glPolygonOffset` 사용 시 발생할 수 있는 예외 상황에 대비하여 안전장치(`try-except`)를 마련했습니다.
- **심층 디버깅 및 최적화**:
  - **NaN/Inf 검증**: 3D 모델 생성 및 법선 계산 과정에서 발생할 수 있는 수학적 오류(0으로 나누기 등)를 방지하기 위해 NaN/Inf 검사 로직을 추가했습니다.
  - **인덱스 바운드 체크**: 렌더링 시 잘못된 인덱스 참조로 인한 크래시를 막기 위해 `draw_model`과 `calculate_normals`에 인덱스 유효성 검사 코드를 삽입했습니다.
  - **UI 유연성 확보**: `QToolButton`의 메뉴 인디케이터를 CSS로 제거하여 깔끔한 룩을 구현하고, 패널 너비를 동적으로 설정하여 다양한 해상도와 폰트 환경에 대응하도록 개선했습니다. 또한, 패널 간 간격과 여백을 추가하여 시각적 답답함을 해소했습니다.
  - **실행 흐름 추적**: Windows 환경에서의 크래시 원인을 정확히 파악하기 위해 `generate_model`, `calculate_normals`, `paintGL` 등 핵심 메서드에 상세한 디버그 로그를 추가하여 문제 발생 지점을 추적할 수 있도록 했습니다.
