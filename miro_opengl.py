# -*- coding: utf-8 -*-
"""
Miro Game OpenGL Widget
"""

from PyQt5.QtWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *

class MiroOpenGLWidget(QOpenGLWidget):
    """
    미로 찾기 게임을 위한 OpenGL 위젯입니다.
    현재는 초기화 및 기본 렌더링 테스트용 코드가 포함되어 있습니다.
    추후 미로 생성 및 플레이어 이동 로직이 구현될 예정입니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_pos = [0, 10, 10]

    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / h, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(self.camera_pos[0], self.camera_pos[1], self.camera_pos[2], 
                  0, 0, 0, 
                  0, 1, 0)
        
        # Placeholder: Draw a simple triangle
        glBegin(GL_TRIANGLES)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0.0, 1.0, 0.0)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(-1.0, -1.0, 0.0)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(1.0, -1.0, 0.0)
        glEnd()
