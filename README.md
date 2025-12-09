# PyOpenGL 3D Modeler & Maze Game

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![PyOpenGL](https://img.shields.io/badge/PyOpenGL-3.1-green)
![PyQt5](https://img.shields.io/badge/PyQt5-5.x-41CD52?logo=qt&logoColor=white)

PyOpenGL 기반의 3D 모델링 소프트웨어와 1인칭 미로 게임입니다.

## 주요 기능 (Features)

### 🎨 3D 모델러

- **SOR (Surface of Revolution)**: 2D 프로파일을 회전축 기준으로 회전시켜 3D 모델 생성
- **Sweep Surface**: 2D 프로파일을 경로를 따라 압출 (twist, caps 옵션)
- **렌더링 모드**: Wireframe, Solid, Flat Shading, Gouraud Shading
- **GPU 가속**: VBO(Vertex Buffer Object) 기반 렌더링
- **파일 저장/불러오기**: .dat 포맷 지원

### 🎮 미로 게임

- **스토리 모드**: 3개의 스테이지 (810관, 캠퍼스, 정문 가는 길)
- **커스텀 모드**: 미로 크기, 벽 두께/높이, 높이 변화 설정
- **1인칭 시점**: WASD 이동, 점프, 충돌 감지
- **아이템 & 스킬**: 수집 아이템과 6종류의 스킬 효과
- **날씨 시스템**: 맑음, 비, 눈 효과

### ⚙️ 설정

- **그래픽**: GPU 가속, 그림자 품질 (Off/Low/High)
- **오디오**: 마스터 볼륨 조절
- **컨트롤**: 이동 속도, 마우스 감도

## 설치 방법 (Installation)

### 요구 사항

- Python 3.x
- Windows / macOS / Linux

### 설치

```bash
# 저장소 클론
git clone https://github.com/tansan7271/PyOpenGL-ModelingSW
cd PyOpenGL-ModelingSW

# 가상환경 생성 및 활성화
python -m venv CG_Project

# Windows
CG_Project\Scripts\activate

# macOS/Linux
source CG_Project/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
```

## 조작법 (Controls)

### 모델러

| 조작 | 설명 |
|------|------|
| 클릭 | 점 추가 (2D 모드) |
| 드래그 | 점 이동 (2D 모드) |
| 마우스 드래그 | 모델 회전 (3D 모드) |
| 마우스 휠 | 줌 인/아웃 |

### 미로 게임

| 조작 | 설명 |
|------|------|
| W/A/S/D | 이동 |
| 마우스 | 시점 회전 |
| Space | 점프 |
| ESC | 일시정지 |

## 프로젝트 구조 (Project Structure)

```
PyOpenGL-ModelingSW/
├── main.py                  # 진입점, MainContainer
├── modeler_opengl.py        # 모델러 OpenGL 렌더링
├── modeler_ui_and_chang.py  # 모델러 UI
├── miro_opengl.py           # 미로 OpenGL 렌더링
├── miro_ui_and_chang.py     # 미로 게임 UI
├── maze_generator.py        # DFS 미로 생성 알고리즘
├── requirements.txt         # 의존성 목록
└── assets/                  # 리소스 (아이콘, 텍스처, 사운드)
```

## 기술 스택 (Tech Stack)

- **Python 3.x** - 메인 언어
- **PyOpenGL** - OpenGL 바인딩
- **PyQt5** - GUI 프레임워크
- **NumPy** - 수치 연산

## 빌드 (Build)

PyInstaller를 사용하여 실행 파일로 빌드할 수 있습니다:

```bash
# PyInstaller 설치
pip install pyinstaller
```

### Windows

```bash
pyinstaller main.spec
```

빌드 결과물: `dist/EscapeFromCAU/EscapeFromCAU.exe`

### macOS

```bash
pyinstaller main_macos.spec
```

빌드 결과물: `dist/EscapeFromCAU.app`

> **참고**: PyInstaller는 크로스 컴파일을 지원하지 않습니다. 각 OS에서 직접 빌드해야 합니다.

## 배포 (Distribution)

### Windows

```
dist/EscapeFromCAU/
├── EscapeFromCAU.exe    # 실행 파일
├── _internal/           # Python 런타임 (자동 생성)
├── assets/              # 리소스 (아이콘, 사운드, 텍스처)
└── datasets/            # 데이터 파일 (미로, 아이템)
```

배포 시 `dist/EscapeFromCAU/` 폴더 전체를 ZIP으로 압축하여 배포합니다.

### macOS

```
dist/EscapeFromCAU.app   # macOS 앱 번들
```

배포 시 `.app` 파일을 ZIP으로 압축하거나 DMG로 패키징하여 배포합니다.

> **참고**: macOS에서 커스텀 미로는 `~/Library/Application Support/EscapeFromCAU/datasets/`에 저장됩니다.

### 실행 요구사항 (End Users)

- **Windows**: Windows 10/11 (64-bit)
- **macOS**: macOS 10.13 이상
- OpenGL 지원 그래픽 드라이버
- Python 설치 불필요
