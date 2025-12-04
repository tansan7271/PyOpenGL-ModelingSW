# -*- coding: utf-8 -*-
"""
미로 게임 UI 모듈
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from miro_opengl import MiroOpenGLWidget

class MiroWindow(QWidget):
    """
    미로 찾기 게임의 메인 UI 위젯입니다.
    OpenGL 위젯과 게임 제어 버튼 등을 포함합니다.
    """
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 헤더 (Header)
        self.label_title = QLabel("Maze Game (Coming Soon)")
        self.label_title.setAlignment(Qt.AlignCenter)
        self.label_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(self.label_title)
        
        # OpenGL 위젯 (OpenGL Widget)
        self.gl_widget = MiroOpenGLWidget()
        layout.addWidget(self.gl_widget)
        
        # 컨트롤 (Controls)
        self.btn_start = QPushButton("Start Game")
        layout.addWidget(self.btn_start)
