# -*- coding: utf-8 -*-
"""
미로 게임 스토리 모드 UI 모듈
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter

class AspectRatioLabel(QLabel):
    """
    비율을 유지하며 부모 위젯에 맞춰 크기가 조절되는 라벨입니다.
    PaintEvent를 사용하여 리사이즈 루프를 방지하고 부드러운 렌더링을 지원합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # 중요: 레이아웃이 이미지 크기에 영향을 받아 무한 확장되지 않도록 Ignored 설정
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setAlignment(Qt.AlignCenter)
        self._pixmap = None

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        # 부모 setPixmap은 호출하지 않거나, 빈 픽스맵으로 초기화하여 기본 그리기 동작 방지
        super().setPixmap(QPixmap()) 
        self.update() # 다시 그리기 요청

    def paintEvent(self, event):
        if not self._pixmap or self._pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 위젯 가용 크기
        w = self.width()
        h = self.height()
        
        # 원본 이미지 비율 유지하며 현재 위젯 크기에 맞게 스케일링
        scaled_pixmap = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 중앙 정렬 좌표 계산
        x = (w - scaled_pixmap.width()) // 2
        y = (h - scaled_pixmap.height()) // 2
        
        painter.drawPixmap(x, y, scaled_pixmap)

class MiroStoryWidget(QWidget):
    """
    스토리 이미지를 순차적으로 보여주는 위젯입니다.
    """
    finished = pyqtSignal() # 스토리 읽기가 끝나고 타이틀로 돌아갈 때 발생

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 0
        self.total_pages = 7 # 총 7장으로 변경
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # 1. 스토리 이미지 표시 영역 (AspectRatioLabel 사용)
        self.lbl_image = AspectRatioLabel()
        self.lbl_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 배경색/테두리 제거 (투명 처리되어 레터박스 안 보임)
        layout.addWidget(self.lbl_image)
        
        # 2. 하단 네비게이션 버튼
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(20)
        
        # 이전 페이지 버튼
        self.btn_prev = QPushButton("Previous Page")
        self.btn_prev.setMinimumHeight(40)
        self.btn_prev.setFont(QFont("Arial", 12))
        self.btn_prev.clicked.connect(self._prev_page)
        nav_layout.addWidget(self.btn_prev)
        
        nav_layout.addStretch()
        
        # 페이지 표시용 라벨
        self.lbl_page_num = QLabel()
        self.lbl_page_num.setStyleSheet("color: #AAA; font-size: 14px;")
        nav_layout.addWidget(self.lbl_page_num)
        
        nav_layout.addStretch()
        
        # 다음 페이지 / 타이틀 복귀 버튼
        self.btn_next = QPushButton("Next Page")
        self.btn_next.setMinimumHeight(40)
        self.btn_next.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_next.clicked.connect(self._next_page)
        nav_layout.addWidget(self.btn_next)
        
        layout.addLayout(nav_layout)
        
    def reset_story(self):
        """스토리를 처음부터 다시 시작합니다."""
        self.current_page = 1
        self._update_ui()
        
    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._update_ui()
            
    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._update_ui()
        else:
            # 마지막 페이지에서 누르면 종료
            self.finished.emit()
            
    def _update_ui(self):
        """현재 페이지에 맞춰 UI(이미지, 버튼 상태)를 갱신합니다."""
        # 1. 이미지 로드
        image_name = f"story_{self.current_page}.png"
        image_path = os.path.join(os.path.dirname(__file__), 'assets', image_name)
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.lbl_image.setPixmap(pixmap)
            # 텍스트 초기화는 AspectRatioLabel 내부에서 처리되지 않으므로 필요 시 별도 메서드 사용, 
            # 하지만 여기서는 이미지가 있으면 텍스트가 덮어씌워짐 (QLabel 특성상)
        else:
            # 이미지가 없을 경우 플레이스홀더 (기본 QLabel 기능 사용 불가하므로 빈 픽스맵 + 오버레이 텍스트 방식 고려, 
            # 혹은 단순하게 텍스트 표시용 이미지를 생성하거나, 임시로 텍스트 설정)
            # AspectRatioLabel은 setPixmap을 오버라이드했으므로 setText 사용 시 주의.
            # 여기서는 편의상 빈 픽스맵을 설정하고 부모 클래스의 setText를 호출하지 않음.
            # 대신 QPainter로 텍스트를 그리는 방식으로 가거나, 간단히 콘솔 로그만 남김.
            # 사용자 요청은 '규격 정립'이므로 검은 화면 유지.
            print(f"Image not found: {image_path}")
            # 빈 픽스맵 생성 (1920x1440 검은색)
            empty = QPixmap(1920, 1440)
            empty.fill(QColor("#222"))
            self.lbl_image.setPixmap(empty)

        # 2. 버튼 상태 업데이트
        self.btn_prev.setVisible(self.current_page > 1)
        
        if self.current_page == self.total_pages:
            self.btn_next.setText("Return to Title")
            self.btn_next.setStyleSheet("")
        else:
            self.btn_next.setText("Next Page")
            self.btn_next.setStyleSheet("")

        # 3. 페이지 번호 업데이트
        self.lbl_page_num.setText(f"{self.current_page} / {self.total_pages}")
