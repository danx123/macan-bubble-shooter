"""
bubble_timer.py - Sistem Timer & Tekanan Waktu untuk Macan Bubble Shooter
Modul ini mengelola:
- Timer per-tembakan (tekanan waktu)
- Timer mode "RUSH" saat bubble mendekati bawah
- Score multiplier berbasis kecepatan tembakan
- Visual countdown bar
- Danger zone detection
"""

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtGui import QColor, QBrush, QPen, QLinearGradient, QFont
from PySide6.QtCore import Qt, QRectF


# ============================================================
# KONFIGURASI TIMER
# ============================================================
SHOT_TIME_LIMIT    = 8.0   # Detik untuk menembak sebelum penalti
RUSH_TIME_LIMIT    = 5.0   # Detik saat mode RUSH aktif
TICK_INTERVAL_MS   = 100   # Update setiap 100ms (0.1 detik)

# Multiplier berdasarkan sisa waktu
TIME_MULTIPLIER_TABLE = [
    (7.0, 3.0),   # Tembak dalam 1 detik pertama → 3x
    (5.0, 2.5),   # Tembak dalam 3 detik → 2.5x
    (3.0, 2.0),   # Tembak dalam 5 detik → 2x
    (1.5, 1.5),   # Tembak dalam 6.5 detik → 1.5x
    (0.0, 1.0),   # Tembak di akhir → 1x
]

PENALTY_SCORE = -50  # Penalti jika waktu habis


class ShotTimer(QObject):
    """
    Timer untuk setiap tembakan.
    Memberikan tekanan waktu dan score multiplier.
    """
    tick = Signal(float)          # Sisa waktu (float detik)
    time_up = Signal()            # Waktu habis → penalti
    multiplier_changed = Signal(float)  # Multiplier berubah

    def __init__(self, time_limit=SHOT_TIME_LIMIT):
        super().__init__()
        self.time_limit = time_limit
        self.time_remaining = time_limit
        self.running = False
        self.rush_mode = False

        self._timer = QTimer()
        self._timer.setInterval(TICK_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)

    def start(self, rush_mode=False):
        """Mulai timer tembakan"""
        self.rush_mode = rush_mode
        self.time_limit = RUSH_TIME_LIMIT if rush_mode else SHOT_TIME_LIMIT
        self.time_remaining = self.time_limit
        self.running = True
        self._timer.start()
        self.tick.emit(self.time_remaining)

    def stop(self):
        """Hentikan timer (setelah tembakan)"""
        self._timer.stop()
        self.running = False

    def reset(self):
        """Reset timer ke kondisi awal"""
        self.stop()
        self.time_remaining = self.time_limit

    def pause(self):
        self._timer.stop()

    def resume(self):
        if self.running:
            self._timer.start()

    def _on_tick(self):
        self.time_remaining -= TICK_INTERVAL_MS / 1000.0
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self._timer.stop()
            self.running = False
            self.time_up.emit()
        self.tick.emit(self.time_remaining)
        self.multiplier_changed.emit(self.get_multiplier())

    def get_multiplier(self):
        """Hitung multiplier berdasarkan sisa waktu"""
        for threshold, mult in TIME_MULTIPLIER_TABLE:
            if self.time_remaining >= threshold:
                return mult
        return 1.0

    def get_progress(self):
        """Kembalikan progress 0.0–1.0 (1.0 = penuh)"""
        if self.time_limit == 0:
            return 0.0
        return max(0.0, self.time_remaining / self.time_limit)

    @property
    def is_danger(self):
        """True jika sisa waktu < 30%"""
        return self.get_progress() < 0.30


# ============================================================
# TIMER BAR — Ditambahkan langsung ke QGraphicsScene
# ============================================================

class TimerBar:
    """
    Komponen visual HUD untuk menampilkan countdown bar di scene.
    Bar berubah warna: hijau → kuning → merah
    """

    def __init__(self, scene, x, y, width, height=14):
        self.scene = scene
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # Background track
        self._bg = QGraphicsRectItem(x, y, width, height)
        self._bg.setBrush(QBrush(QColor(30, 30, 50, 180)))
        self._bg.setPen(QPen(QColor(80, 80, 120), 1))
        self._bg.setZValue(200)
        scene.addItem(self._bg)

        # Foreground fill
        self._fill = QGraphicsRectItem(x + 2, y + 2, width - 4, height - 4)
        self._fill.setZValue(201)
        scene.addItem(self._fill)

        # Label multiplier
        self._label = QGraphicsTextItem("1.0x")
        self._label.setDefaultTextColor(QColor(255, 255, 255))
        font = QFont("Segoe UI", 9, QFont.Bold)
        self._label.setFont(font)
        self._label.setZValue(202)
        self._label.setPos(x + width + 6, y - 2)
        scene.addItem(self._label)

        self.update(1.0, 1.0)

    def update(self, progress: float, multiplier: float):
        """Update bar visual"""
        fill_w = max(2, int((self.width - 4) * progress))
        self._fill.setRect(self.x + 2, self.y + 2, fill_w, self.height - 4)

        # Warna interpolasi: hijau → kuning → merah
        if progress > 0.6:
            r, g = int(255 * (1 - progress) * 2.5), 220
        elif progress > 0.3:
            r, g = 255, int(220 * (progress / 0.6))
        else:
            r, g = 255, int(80 * (progress / 0.3))
        color = QColor(r, g, 40)
        self._fill.setBrush(QBrush(color))
        self._fill.setPen(QPen(color.lighter(130), 0))

        mult_text = f"{multiplier:.1f}x"
        color_str = "#00ff88" if multiplier >= 2.0 else ("#ffdd00" if multiplier >= 1.5 else "#aaaaaa")
        self._label.setHtml(f'<span style="color:{color_str}; font-weight:bold">{mult_text}</span>')

    def set_visible(self, visible: bool):
        self._bg.setVisible(visible)
        self._fill.setVisible(visible)
        self._label.setVisible(visible)

    def remove(self):
        self.scene.removeItem(self._bg)
        self.scene.removeItem(self._fill)
        self.scene.removeItem(self._label)


# ============================================================
# COUNTDOWN OVERLAY — Flash angka besar saat RUSH
# ============================================================

class CountdownFlash:
    """Tampilkan angka flash besar di tengah layar saat sisa waktu kritis"""

    def __init__(self, scene, scene_width, scene_height):
        self.scene = scene
        self.cx = scene_width / 2
        self.cy = scene_height / 2
        self._items = []

    def flash(self, text: str, color: QColor = QColor(255, 80, 80)):
        """Tampilkan teks flash sesaat"""
        for item in self._items:
            self.scene.removeItem(item)
        self._items.clear()

        label = QGraphicsTextItem(text)
        font = QFont("Segoe UI Black", 64, QFont.Black)
        label.setFont(font)
        label.setDefaultTextColor(color)
        label.setOpacity(0.85)
        label.setZValue(500)

        bw = label.boundingRect().width()
        bh = label.boundingRect().height()
        label.setPos(self.cx - bw / 2, self.cy - bh / 2)
        self.scene.addItem(label)
        self._items.append(label)

        # Auto-hapus setelah 600ms
        QTimer.singleShot(600, self._clear)

    def _clear(self):
        for item in self._items:
            if item.scene():
                self.scene.removeItem(item)
        self._items.clear()


# ============================================================
# RUSH MODE — Pengelola level darurat
# ============================================================

class RushModeManager(QObject):
    """
    Aktifkan RUSH MODE saat bubble mencapai zona bahaya.
    Rush mode: timer dipercepat, score bonus meningkat.
    """
    rush_started  = Signal()
    rush_ended    = Signal()
    danger_level_changed = Signal(int)  # 0=normal, 1=warning, 2=danger, 3=rush

    def __init__(self):
        super().__init__()
        self._danger_level = 0
        self.rush_active = False

    def evaluate(self, bubbles, scene_height, shooter_y):
        """
        Evaluasi posisi bubble terbawah dan tentukan danger level.
        Dipanggil setiap kali bubble baru menempel.
        """
        if not bubbles:
            self._set_level(0)
            return

        lowest_y = max(b.y() for b in bubbles)
        distance = shooter_y - lowest_y

        # Zona bahaya berbasis jarak ke shooter
        if distance < 80:
            new_level = 3  # RUSH
        elif distance < 160:
            new_level = 2  # DANGER
        elif distance < 240:
            new_level = 1  # WARNING
        else:
            new_level = 0  # NORMAL

        self._set_level(new_level)

    def _set_level(self, level: int):
        if level == self._danger_level:
            return
        old = self._danger_level
        self._danger_level = level

        if level == 3 and old < 3:
            self.rush_active = True
            self.rush_started.emit()
        elif level < 3 and old == 3:
            self.rush_active = False
            self.rush_ended.emit()

        self.danger_level_changed.emit(level)

    @property
    def danger_level(self):
        return self._danger_level

    def get_time_limit(self):
        """Kembalikan time limit sesuai danger level"""
        limits = {0: 8.0, 1: 7.0, 2: 5.5, 3: 4.0}
        return limits.get(self._danger_level, 8.0)

    def get_score_bonus(self):
        """Bonus score saat rush mode"""
        bonuses = {0: 0, 1: 5, 2: 15, 3: 30}
        return bonuses.get(self._danger_level, 0)


# ============================================================
# GLOBAL GAME TIMER — Total waktu bermain
# ============================================================

class GameTimer(QObject):
    """Menghitung total waktu bermain dalam sesi ini"""
    elapsed_changed = Signal(int)  # Detik total

    def __init__(self):
        super().__init__()
        self._elapsed = 0
        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def reset(self):
        self.stop()
        self._elapsed = 0

    def pause(self):
        self._timer.stop()

    def resume(self):
        self._timer.start()

    def _tick(self):
        self._elapsed += 1
        self.elapsed_changed.emit(self._elapsed)

    @property
    def elapsed(self):
        return self._elapsed

    def format(self):
        """Format mm:ss"""
        m = self._elapsed // 60
        s = self._elapsed % 60
        return f"{m:02d}:{s:02d}"


# ============================================================
# SINGLETON HELPERS
# ============================================================

_shot_timer = None
_rush_manager = None
_game_timer = None


def get_shot_timer() -> ShotTimer:
    global _shot_timer
    if _shot_timer is None:
        _shot_timer = ShotTimer()
    return _shot_timer


def get_rush_manager() -> RushModeManager:
    global _rush_manager
    if _rush_manager is None:
        _rush_manager = RushModeManager()
    return _rush_manager


def get_game_timer() -> GameTimer:
    global _game_timer
    if _game_timer is None:
        _game_timer = GameTimer()
    return _game_timer


def reset_all_timers():
    """Reset semua timer ke kondisi awal (dipanggil saat new game)"""
    global _shot_timer, _rush_manager, _game_timer
    _shot_timer = ShotTimer()
    _rush_manager = RushModeManager()
    _game_timer = GameTimer()
