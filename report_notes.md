# SOR 모델러 개발 보고서

이 문서는 PyOpenGL을 이용한 SOR(Surface of Revolution) 3D 모델러의 최종 시스템 구조와 핵심 알고리즘을 설명합니다.

## 1. 프로젝트 개요

- **프로젝트 명:** PyOpenGL SOR 3D Modeler
- **개발 언어:** Python 3.x
- **핵심 라이브러리:**
  - **PyQt5:** GUI 프레임워크. 이벤트 루프 관리 및 UI 컴포넌트 제공.
  - **PyOpenGL:** OpenGL 바인딩. 3D 렌더링 파이프라인 제어.

## 2. 시스템 아키텍처

본 애플리케이션은 **MVC(Model-View-Controller)** 패턴을 변형하여 관심사를 분리했습니다.

### 2.1. 모듈 구성

1.  **`main.py` (Entry Point)**

    - 애플리케이션의 진입점입니다. `QApplication` 인스턴스를 생성하고 메인 윈도우를 실행합니다.

2.  **`ui_and_chang.py` (View & Controller)**

    - **UI 구성:** `MainWindow` 클래스에서 툴바, 도킹 위젯, 컨트롤 패널 등을 생성합니다.
    - **이벤트 처리:** 사용자의 입력(버튼 클릭, 값 변경)을 시그널(Signal)로 받아 `OpenGLWidget`의 슬롯(Slot)을 호출하거나, `OpenGLWidget`의 상태 변화를 감지하여 UI를 갱신합니다.
    - **동적 UI:** 2D 편집 모드와 3D 뷰 모드에 따라 컨트롤 패널의 구성을 동적으로 변경하여 사용자 경험을 최적화합니다.

3.  **`opengl_haeksim.py` (Model & View)**
    - **Core Logic:** `OpenGLWidget` 클래스에서 실제 데이터(점, 3D 메쉬)를 관리하고 렌더링합니다.
    - **Rendering Pipeline:** `initializeGL`, `resizeGL`, `paintGL`을 오버라이딩하여 OpenGL 상태 설정, 투영 행렬 계산, 렌더링 루프를 제어합니다.
    - **Interaction:** 마우스 이벤트를 처리하여 2D 점 추가, 드래그 이동, 선택 삭제 기능을 수행합니다.

## 3. 핵심 기능 및 알고리즘

### 3.1. SOR (Surface of Revolution) 알고리즘

2D 프로파일 곡선을 특정 축을 기준으로 회전시켜 3D 메쉬를 생성하는 알고리즘입니다.

1.  **회전 각도 계산:** 360도를 사용자가 설정한 `단면 개수(slices)`로 나누어 단위 회전각 $\theta$를 구합니다.
2.  **정점 생성 (Vertex Generation):**
    - 2D 프로파일의 각 점 $(x, y)$에 대해 회전 행렬을 적용하여 3D 좌표 $(x', y', z')$를 계산합니다.
    - **Y축 회전 시:**
      $$x' = x \cos(k\theta)$$
      $$y' = y$$
      $$z' = -x \sin(k\theta)$$
      (여기서 $k$는 현재 단면의 인덱스)
3.  **면 생성 (Face Generation):**
    - 인접한 두 단면($k, k+1$)과 두 점($i, i+1$)을 연결하여 사각형(Quad) 면을 구성합니다.
    - 인덱스 순서: $(k, i) \rightarrow (k, i+1) \rightarrow (k+1, i+1) \rightarrow (k+1, i)$

### 3.2. 렌더링 및 조명 (Rendering & Lighting)

- **렌더링 모드:**
  - **Wireframe:** `glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)`을 사용하여 메쉬의 엣지만 렌더링.
  - **Solid/Flat/Gouraud:** `glPolygonMode(..., GL_FILL)`과 `glShadeModel(GL_FLAT/GL_SMOOTH)`를 조합하여 다양한 질감 표현.
- **조명 시스템 (Dual Lighting):**
  - **Key Light (GL_LIGHT0):** 우측 상단 전면에서 강한 빛을 비추어 주된 형태를 잡습니다.
  - **Fill Light (GL_LIGHT1):** 좌측 상단 후면에서 약한 빛을 비추어 그림자 영역의 디테일을 살리고 입체감을 더합니다.
  - **Material:** `GL_COLOR_MATERIAL`을 사용하여 객체의 색상이 조명과 반응하도록 설정했습니다.

### 3.3. 데이터 저장 포맷 (.dat v5)

자체 정의한 텍스트 기반 포맷으로, 2D 편집 상태와 3D 모델 데이터를 모두 저장합니다.

- **구조:**
  1.  **헤더:** 단면 수, 회전축, 렌더링 모드, 색상 정보.
  2.  **2D 경로:** 다중 경로(Multi-path) 지원. 각 경로의 점 개수, 닫힘 여부, 좌표 리스트.
  3.  **3D 메쉬:** 생성된 정점 리스트와 면(Quad) 인덱스 리스트.

## 4. 오픈소스 활용 및 독창성

- **기반 코드:** PyOpenGL의 기본적인 윈도우 셋업 및 `gluLookAt` 활용 예제를 참고했습니다.
- **독창적 구현:**
  - **동적 UI 시스템:** 2D/3D 모드에 따라 UI가 실시간으로 변하는 로직을 직접 설계했습니다.
  - **다중 경로 편집기:** 단순한 점 찍기를 넘어, 여러 개의 닫힌/열린 도형을 관리하고 드래그로 수정하며 스냅(Snap) 기능까지 지원하는 벡터 편집기를 직접 구현했습니다.
  - **이중 조명 시스템:** 입체감을 극대화하기 위해 Key/Fill Light 조합을 고안하고 적용했습니다.
