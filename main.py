# -*- coding: utf-8 -*-
"""
PyOpenGL SOR Modeler Application Entry Point

이 파일은 PyOpenGL을 이용한 SOR(Surface of Revolution) 모델러 애플리케이션의
메인 실행 파일입니다. PyQt5 애플리케이션을 초기화하고, ui_and_chang.py에 정의된
메인 윈도우(MainWindow)를 생성하고 실행하는 역할을 담당합니다.
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui_and_chang import MainWindow

if __name__ == '__main__':
    # PyQt5 애플리케이션 인스턴스를 생성합니다.
    # sys.argv는 커맨드 라인 인수를 애플리케이션에 전달할 수 있도록 합니다.
    app = QApplication(sys.argv)

    # 메인 윈도우(MainWindow) 객체를 생성합니다.
    # 모든 UI 요소와 시그널/슬롯 연결은 MainWindow 클래스 내에서 관리됩니다.
    window = MainWindow()

    # 윈도우를 화면에 표시합니다.
    window.show()

    # 애플리케이션의 이벤트 루프를 시작합니다.
    # 이 함수가 호출되면 프로그램은 사용자의 입력(마우스 클릭, 키보드 입력 등)을
    # 기다리는 상태가 되며, 창이 닫힐 때 종료 코드를 반환합니다.
    sys.exit(app.exec_())
