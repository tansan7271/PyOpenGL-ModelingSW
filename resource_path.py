"""
PyInstaller 빌드 후에도 리소스 경로가 올바르게 작동하도록 하는 헬퍼 모듈
"""
import sys
import os


def get_resource_path(relative_path):
    """
    PyInstaller 빌드 후에도 리소스 경로를 올바르게 반환

    Args:
        relative_path: 프로젝트 루트 기준 상대 경로

    Returns:
        절대 경로 문자열
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 EXE 실행 중
        base_path = sys._MEIPASS
    else:
        # 일반 Python 스크립트 실행 중
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_base_path():
    """
    프로젝트/앱의 기본 경로 반환

    Returns:
        기본 경로 문자열
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


def ensure_user_datasets():
    """
    번들된 datasets를 사용자 쓰기 가능 경로로 복사

    빌드된 앱 실행 시 _internal/datasets의 파일들을
    사용자 datasets 폴더로 복사하여 일관된 경로 사용
    """
    if not getattr(sys, 'frozen', False):
        return  # 개발 환경에서는 불필요

    import shutil
    import glob

    # 번들된 datasets 경로 (_internal/datasets)
    bundled_datasets = os.path.join(sys._MEIPASS, 'datasets')
    if not os.path.exists(bundled_datasets):
        return

    # 사용자 datasets 경로
    user_datasets = get_user_data_path('datasets')

    # 번들된 파일들을 사용자 경로로 복사 (존재하지 않는 경우만)
    for src_file in glob.glob(os.path.join(bundled_datasets, '*.dat')):
        filename = os.path.basename(src_file)
        dst_file = os.path.join(user_datasets, filename)
        if not os.path.exists(dst_file):
            shutil.copy2(src_file, dst_file)


def get_user_data_path(relative_path=''):
    """
    사용자 데이터 저장 경로 반환 (쓰기 가능한 경로)

    Windows: 실행 파일과 같은 경로 (기존 방식 유지)
    macOS: .app 번들은 읽기 전용이므로 ~/Library/Application Support/ 사용

    Args:
        relative_path: 기본 경로 기준 상대 경로

    Returns:
        절대 경로 문자열
    """
    app_name = 'EscapeFromCAU'

    if sys.platform == 'darwin':  # macOS
        # macOS .app 번들은 읽기 전용이므로 별도 경로 사용
        base = os.path.expanduser(f'~/Library/Application Support/{app_name}')
        # 기본 디렉토리 생성
        if not os.path.exists(base):
            os.makedirs(base)
    elif sys.platform == 'win32':  # Windows
        # Windows: 실행 파일과 같은 경로 사용
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 EXE 실행 중 - EXE 파일 위치
            base = os.path.dirname(sys.executable)
        else:
            # 일반 Python 스크립트 실행 중
            base = os.path.dirname(os.path.abspath(__file__))
    else:  # Linux 등
        base = os.path.expanduser(f'~/.local/share/{app_name}')
        if not os.path.exists(base):
            os.makedirs(base)

    if relative_path:
        full_path = os.path.join(base, relative_path)
        # 하위 디렉토리 생성 (존재하지 않는 경우)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        return full_path

    return base
