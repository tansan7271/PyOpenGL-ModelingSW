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
