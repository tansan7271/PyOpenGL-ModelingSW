import os
from PyQt5.QtCore import QUrl, QObject
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from resource_path import get_resource_path

class SoundManager(QObject):
    """
    게임 전체의 사운드를 관리하는 클래스.
    
    기능:
    1. 배경음악(BGM) 재생: 타이틀(Clean/Muffled) 및 스테이지별 BGM
    2. 효과음(SFX) 재생: 게임 클리어, 게임 오버 등
    3. Muffled Effect: 타이틀 화면 외의 탭에서는 먹먹한 버전의 BGM으로 전환
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- 오디오 플레이어 초기화 ---
        
        # 0. 마스터 볼륨 (0~100)
        self.master_volume = 100
        self.ducking_factor = 1.0 # 스킬 발동 시 BGM 줄임 (0.0~1.0)
        
        # 1. 타이틀 BGM (Clean 버전)
        self.player_title_clean = QMediaPlayer()
        self.player_title_clean.setVolume(self.master_volume)
        
        # 2. 타이틀 BGM (Muffled 버전)
        self.player_title_muffled = QMediaPlayer()
        self.player_title_muffled.setVolume(0) # 초기에는 안 들림
        
        # 3. 스테이지 BGM
        self.player_stage = QMediaPlayer()
        self.player_stage.setVolume(int(self.master_volume * 0.8)) # 80%
        
        # 4. 효과음 (SFX)
        # 4. 효과음 (SFX) - 다중 재생을 위한 풀(Pool) 방식
        self.sfx_pool = []
        for _ in range(8): # 8개 채널
            player = QMediaPlayer()
            player.setVolume(self.master_volume)
            self.sfx_pool.append(player)
        
        # 경로 설정 (assets/sounds 폴더 가정)
        self.base_path = get_resource_path(os.path.join('assets', 'sounds'))
            
        # 플레이리스트 설정 (반복 재생을 위해)
        self._setup_playlists()

    def _setup_playlists(self):
        """배경음악 무한 반복을 위한 플레이리스트 설정"""
        # 타이틀 BGM은 반복 재생
        self.playlist_title_clean = QMediaPlaylist()
        self.playlist_title_clean.setPlaybackMode(QMediaPlaylist.Loop)
        self.player_title_clean.setPlaylist(self.playlist_title_clean)
        
        self.playlist_title_muffled = QMediaPlaylist()
        self.playlist_title_muffled.setPlaybackMode(QMediaPlaylist.Loop)
        self.player_title_muffled.setPlaylist(self.playlist_title_muffled)
        
        # 스테이지 BGM도 반복 재생
        self.playlist_stage = QMediaPlaylist()
        self.playlist_stage.setPlaybackMode(QMediaPlaylist.Loop)
        self.player_stage.setPlaylist(self.playlist_stage)

    def _get_media_content(self, filename):
        """파일 경로로부터 QMediaContent 생성"""
        path = os.path.join(self.base_path, filename)
        if os.path.exists(path):
            return QMediaContent(QUrl.fromLocalFile(path))
        return QMediaContent()

    def load_title_bgm(self, clean_file, muffled_file):
        """타이틀 BGM 로드 (Clean & Muffled)"""
        self.playlist_title_clean.clear()
        self.playlist_title_clean.addMedia(self._get_media_content(clean_file))
        
        self.playlist_title_muffled.clear()
        self.playlist_title_muffled.addMedia(self._get_media_content(muffled_file))

    def play_title_bgm(self):
        """타이틀 BGM 재생 시작 (동기화 재생 - 처음부터)"""
        self.player_stage.stop() # 스테이지 음악 중지
        
        # 두 트랙을 동시에 처음부터 재생
        self.player_title_clean.stop()
        self.player_title_muffled.stop()
        
        self.player_title_clean.play()
        self.player_title_muffled.play()
        
        # 기본 상태: Clean 들림, Muffled 안 들림
        self.set_muffled(False)

    def set_master_volume(self, volume):
        """
        마스터 볼륨 설정 (0~100)
        
        Args:
            volume (int): 0~100 사이의 값
        """
        self.master_volume = volume
        
        # 현재 Muffled 상태에 따라 볼륨 재설정
        # (Clean이 들리고 있었다면 Clean에 볼륨 적용, 아니면 Muffled에 적용)
        is_clean_active = (self.player_title_clean.volume() > 0)
        
        self.set_muffled(not is_clean_active)
        
        # 스테이지 BGM과 SFX도 업데이트
        # 스테이지 BGM과 SFX도 업데이트
        self._update_stage_volume()
        for player in self.sfx_pool:
            player.setVolume(self.master_volume)

    def set_ducking(self, factor):
        """BGM 일시적 볼륨 조절 (Ducking)"""
        self.ducking_factor = factor
        self._update_stage_volume()
        
    def _update_stage_volume(self):
        """스테이지 BGM 볼륨 실제 적용"""
        vol = int(self.master_volume * 0.8 * self.ducking_factor)
        self.player_stage.setVolume(vol)

    def set_muffled(self, is_muffled):
        """
        타이틀 BGM의 Muffled 효과 전환
        
        Args:
            is_muffled (bool): True면 먹먹한 소리, False면 선명한 소리
        """
        if is_muffled:
            self.player_title_clean.setVolume(0)
            self.player_title_muffled.setVolume(self.master_volume)
        else:
            self.player_title_clean.setVolume(self.master_volume)
            self.player_title_muffled.setVolume(0)

    def play_stage_bgm(self, stage_name):
        """
        스테이지별 BGM 재생
        
        Args:
            stage_name (str): "Stage 1", "Stage 2", "Stage 3" 등
        """
        # 타이틀 음악 일시 중지 (완전 정지하지 않고, 나중에 이어질 수도 있음)
        self.player_title_clean.pause()
        self.player_title_muffled.pause()
        
        # 파일 매핑
        bgm_file = "bgm_custom.mp3" # 기본값
        if "Stage 1" in stage_name:
            bgm_file = "bgm_stage_1.mp3"
        elif "Stage 2" in stage_name:
            bgm_file = "bgm_stage_2.mp3"
        elif "Stage 3" in stage_name:
            bgm_file = "bgm_stage_3.mp3"
            
        # 플레이리스트 갱신 및 재생
        self.playlist_stage.clear()
        content = self._get_media_content(bgm_file)
        if not content.isNull():
            self.playlist_stage.addMedia(content)
            self._update_stage_volume()
            self.player_stage.play()
        else:
            print(f"BGM file not found: {bgm_file}")

    def play_sfx(self, sfx_type):
        """
        효과음 재생 (One-shot)
        
        Args:
            sfx_type (str): "clear", "gameover" 등
        """
        filename = ""
        if sfx_type == "clear":
            filename = "sfx_clear.wav"
        elif sfx_type == "gameover":
            filename = "sfx_gameover.wav"
        elif sfx_type == "item_get":
            filename = "sfx_item_get.wav"
        elif sfx_type == "skill_activate":
            filename = "sfx_skill_activate.wav"
        elif sfx_type == "time_boost":
            filename = "sfx_time_boost.wav"
        elif sfx_type == "trap_fall":
            filename = "sfx_trap_fall.wav"
        elif sfx_type.endswith("_start") or sfx_type.endswith("_end"):
            # 일반화된 처리: sfx_ghost_start.wav 등
            filename = f"sfx_{sfx_type}.wav"
            
        content = self._get_media_content(filename)
        if not content.isNull():
            # 사용 가능한 플레이어 찾기
            player_to_use = None
            for player in self.sfx_pool:
                if player.state() == QMediaPlayer.StoppedState:
                    player_to_use = player
                    break
            
            # 모두 사용 중이면 첫 번째꺼 사용 (Interruption)
            if player_to_use is None:
                player_to_use = self.sfx_pool[0]
                
            player_to_use.setMedia(content)
            player_to_use.setVolume(self.master_volume)
            player_to_use.play()

    def stop_stage_bgm(self):
        """스테이지 BGM 중지"""
        self.player_stage.stop()


    def stop_sfx_pool(self):
        """SFX 풀의 모든 재생 중지"""
        for player in self.sfx_pool:
            player.stop()

    def stop_all(self):
        """모든 사운드 중지"""
        self.player_title_clean.stop()
        self.player_title_muffled.stop()
        self.player_stage.stop()
        self.stop_sfx_pool()
