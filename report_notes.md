# SOR 모델러 개발 보고서 초안

이 파일은 최종 보고서 작성을 위한 자료를 수집하는 공간입니다.
프로젝트의 구조, 사용된 라이브러리, 핵심 코드 설명, 알고리즘, 그리고 오픈소스 활용 및 변형에 대한 내용을 기록합니다.

## 1. 프로젝트 개요
- **프로젝트 명:** PyOpenGL을 이용한 SOR(Surface of Revolution) 3D 모델러
- **개발 언어:** Python
- **핵심 라이브러리:**
  - **PyQt5 (GUI):** 애플리케이션의 그래픽 사용자 인터페이스(GUI)를 구축합니다. 버튼, 메뉴, 창 등의 UI 요소를 생성하고 관리하며, PyOpenGL 위젯을 통합하는 컨테이너 역할을 합니다.
  - **PyOpenGL (3D 렌더링):** 3D 그래픽을 렌더링하는 핵심 라이브러리입니다. SOR 모델의 생성, 시점 변환, 조명 효과 등 OpenGL의 그래픽 파이프라인을 Python에서 사용할 수 있게 해줍니다.

## 2. 시스템 아키텍처

본 애플리케이션은 **관심사 분리(Separation of Concerns)** 원칙에 따라 설계되었으며, 코드의 가독성과 유지보수성을 높이기 위해 크게 3개의 모듈로 구성됩니다.

- **`main.py` (Application Entry Point):** 애플리케이션의 시작점입니다. PyQt5 애플리케이션을 생성하고 메인 윈도우(`MainWindow`)를 실행하는 최소한의 역할만 담당합니다.

- **`ui_and_chang.py` (UI Layer):** 사용자 인터페이스(UI)의 생성과 관리를 전담합니다.
  - `MainWindow` 클래스가 정의되어 있으며, 툴바, 컨트롤 패널, 버튼 등 모든 UI 요소를 생성하고 배치합니다.
  - 사용자의 입력(버튼 클릭 등)을 받는 시그널(Signal)을 처리하고, 이에 따른 동작을 `opengl_haeksim.py`의 핵심 로직에 요청하는 '컨트롤러' 역할을 수행합니다.

- **`opengl_haeksim.py` (Core Logic / Graphics Engine):** 모든 그래픽 처리와 핵심 데이터 및 로직을 담당합니다.
  - `OpenGLWidget` 클래스가 정의되어 있으며, 실제 OpenGL 렌더링을 수행합니다.
  - 2D/3D 뷰 전환, 프로파일 점 관리, 좌표 변환, SOR 모델 데이터 생성 등 애플리케이션의 핵심 로직을 모두 포함하는 '모델'이자 '뷰' 역할을 합니다.

### 클래스 간 상호작용: 시그널-슬롯 메커니즘

UI와 핵심 로직은 PyQt의 **시그널-슬롯(Signal-Slot)** 메커니즘을 통해 상호작용하여 결합도를 낮춥니다. `MainWindow`는 사용자 입력을 받아 `OpenGLWidget`의 메서드(슬롯)를 호출하고, `OpenGLWidget`은 내부 데이터 변경 시 시그널을 보내 `MainWindow`가 UI를 업데이트하도록 합니다.

**예시: '점 삭제' 기능의 동작 흐름**

1.  **[UI]** 사용자가 'Points List'에서 특정 점 옆의 '×' 버튼을 클릭합니다.
2.  **[UI]** `ui_and_chang.py`의 `_update_point_list` 함수 내에서 해당 버튼의 `clicked` 시그널은 `lambda` 함수를 통해 `opengl_haeksim.py`에 있는 `glWidget.delete_point(index)` 메서드(슬롯)와 연결되어 있습니다.
3.  **[Core Logic]** `delete_point(index)` 메서드가 호출되어 `self.points` 리스트에서 해당 인덱스의 점 데이터를 삭제합니다.
4.  **[Core Logic]** 데이터 변경이 완료된 후, `delete_point` 메서드는 `self.pointsChanged.emit()` 코드를 통해 `pointsChanged` 시그널을 발생시킵니다.
5.  **[UI]** `ui_and_chang.py`의 `_connect_signals` 함수에서 `glWidget.pointsChanged` 시그널은 `self._update_point_list` 슬롯과 미리 연결되어 있습니다.
6.  **[UI]** 시그널이 수신되면 `_update_point_list` 함수가 자동으로 실행되고, 변경된 `glWidget.points` 리스트를 기반으로 점 목록 UI를 새로 그려 화면을 갱신합니다.

이러한 구조를 통해 UI 코드는 그래픽 처리의 상세 로직을 알 필요가 없으며, 그래픽스 코드는 UI의 구체적인 형태를 알 필요 없이 독립적으로 개발 및 수정이 가능합니다.

## 3. 핵심 기능 및 알고리즘
### 3.1. SOR (Surface of Revolution) 알고리즘
- (여기에 SOR 알고리즘 구현에 대한 설명을 추가합니다.)

### 3.2. 데이터 저장 포맷
- (여기에 `.dat` 파일 저장 형식에 대한 설명을 추가합니다.)

## 4. 오픈소스 활용 및 수정 내역
- (여기에 참고한 오픈소스와 어떻게 수정하여 독창성을 확보했는지 기록합니다.)

---
