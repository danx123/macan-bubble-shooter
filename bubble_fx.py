"""
bubble_fx.py - Sound Effects Manager untuk Macan Bubble Shooter
Modul terpisah untuk mengelola semua sound effect dan background music
"""

from pathlib import Path
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

class BubbleSoundManager:
    """
    Manager untuk mengelola semua sound effects dan background music.
    
    Features:
    - Background music looping
    - Multiple sound effect channels
    - Volume control
    - Easy play/stop methods
    """
    
    def __init__(self, sound_folder="bubble_sound"):
        """
        Initialize sound manager
        
        Args:
            sound_folder: Folder name yang berisi file audio (default: "bubble_sound")
        """
        # Path ke folder sound (relatif terhadap file game)
        self.sound_path = Path(__file__).parent / sound_folder
        
        # Cek apakah folder exists
        if not self.sound_path.exists():
            print(f"Warning: Sound folder '{sound_folder}' tidak ditemukan di {self.sound_path}")
            print("Sound effects akan dinonaktifkan.")
            self.sound_enabled = False
            return
        
        self.sound_enabled = True
        
        # === BGM Player (Background Music) ===
        self.bgm_player = QMediaPlayer()
        self.bgm_audio_output = QAudioOutput()
        self.bgm_player.setAudioOutput(self.bgm_audio_output)
        self.bgm_audio_output.setVolume(0.3)  # Volume BGM 30%
        
        # === SFX Players (Sound Effects) - Multiple channels ===
        # Buat 5 player untuk SFX agar bisa play bersamaan
        self.sfx_players = []
        self.sfx_outputs = []
        
        for i in range(5):
            player = QMediaPlayer()
            output = QAudioOutput()
            player.setAudioOutput(output)
            output.setVolume(0.6)  # Volume SFX 60%
            self.sfx_players.append(player)
            self.sfx_outputs.append(output)
        
        self.current_sfx_index = 0  # Rotating index untuk sfx players
        
        # Load semua sound files
        self._load_sounds()
        
    def _load_sounds(self):
        """Load semua file sound ke dictionary untuk akses cepat"""
        self.sounds = {
            'bgm': self.sound_path / "bubble_bgm.mp3",
            'shoot': self.sound_path / "shoot.wav",
            'burst': self.sound_path / "burst.wav",
            'clear': self.sound_path / "clear.wav",
            'combo': self.sound_path / "combo.wav"
        }
        
        # Validasi semua file exists
        missing_files = []
        for name, path in self.sounds.items():
            if not path.exists():
                missing_files.append(f"{name} ({path.name})")
        
        if missing_files:
            print(f"Warning: File audio tidak ditemukan: {', '.join(missing_files)}")
    
    def play_bgm(self, loop=True):
        """
        Play background music
        
        Args:
            loop: True untuk looping BGM (default: True)
        """
        if not self.sound_enabled:
            return
            
        bgm_file = self.sounds.get('bgm')
        if bgm_file and bgm_file.exists():
            self.bgm_player.setSource(QUrl.fromLocalFile(str(bgm_file)))
            
            if loop:
                # Set looping dengan signal
                self.bgm_player.mediaStatusChanged.connect(self._on_bgm_status_changed)
            
            self.bgm_player.play()
    
    def _on_bgm_status_changed(self, status):
        """Callback untuk looping BGM"""
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.bgm_player.setPosition(0)
            self.bgm_player.play()
    
    def stop_bgm(self):
        """Stop background music"""
        if self.sound_enabled:
            self.bgm_player.stop()
    
    def pause_bgm(self):
        """Pause background music"""
        if self.sound_enabled:
            self.bgm_player.pause()
    
    def resume_bgm(self):
        """Resume background music setelah pause"""
        if self.sound_enabled:
            self.bgm_player.play()
    
    def play_sfx(self, effect_name):
        """
        Play sound effect
        
        Args:
            effect_name: Nama effect ('shoot', 'burst', 'clear', 'combo')
        """
        if not self.sound_enabled:
            return
        
        sfx_file = self.sounds.get(effect_name)
        if not sfx_file or not sfx_file.exists():
            return
        
        # Gunakan rotating player agar bisa play multiple sounds bersamaan
        player = self.sfx_players[self.current_sfx_index]
        player.setSource(QUrl.fromLocalFile(str(sfx_file)))
        player.play()
        
        # Rotate ke player berikutnya
        self.current_sfx_index = (self.current_sfx_index + 1) % len(self.sfx_players)
    
    def set_bgm_volume(self, volume):
        """
        Set volume BGM
        
        Args:
            volume: Float 0.0 - 1.0
        """
        if self.sound_enabled:
            self.bgm_audio_output.setVolume(max(0.0, min(1.0, volume)))
    
    def set_sfx_volume(self, volume):
        """
        Set volume semua SFX
        
        Args:
            volume: Float 0.0 - 1.0
        """
        if self.sound_enabled:
            for output in self.sfx_outputs:
                output.setVolume(max(0.0, min(1.0, volume)))
    
    def set_master_volume(self, volume):
        """
        Set volume master (BGM dan SFX)
        
        Args:
            volume: Float 0.0 - 1.0
        """
        self.set_bgm_volume(volume * 0.3)  # BGM 30% dari master
        self.set_sfx_volume(volume * 0.6)  # SFX 60% dari master
    
    def mute_all(self):
        """Mute semua audio"""
        self.set_bgm_volume(0)
        self.set_sfx_volume(0)
    
    def unmute_all(self):
        """Unmute semua audio ke volume default"""
        self.set_bgm_volume(0.3)
        self.set_sfx_volume(0.6)


# === CONVENIENCE FUNCTIONS ===
# Singleton instance untuk easy access
_sound_manager = None

def get_sound_manager():
    """Get singleton instance of sound manager"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = BubbleSoundManager()
    return _sound_manager

def play_shoot():
    """Quick function: Play shoot sound"""
    get_sound_manager().play_sfx('shoot')

def play_burst():
    """Quick function: Play burst sound"""
    get_sound_manager().play_sfx('burst')

def play_clear():
    """Quick function: Play clear sound"""
    get_sound_manager().play_sfx('clear')

def play_combo():
    """Quick function: Play combo sound"""
    get_sound_manager().play_sfx('combo')

def start_bgm():
    """Quick function: Start background music"""
    get_sound_manager().play_bgm()

def stop_bgm():
    """Quick function: Stop background music"""
    get_sound_manager().stop_bgm()