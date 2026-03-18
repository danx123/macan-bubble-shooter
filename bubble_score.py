"""
bubble_score.py - Sistem Scoring Lanjutan untuk Macan Bubble Shooter
Modul ini mengelola:
- Scoring formula dengan multiplier
- Combo counter & chain reaction bonus
- Score popup animasi di scene
- Leaderboard lokal (top 10)
- Streak tracking
"""

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QGraphicsTextItem
from PySide6.QtGui import QColor, QFont
import json
import math
import random
from pathlib import Path


# ============================================================
# KONFIGURASI SCORING
# ============================================================

# Poin dasar per bubble
BASE_BUBBLE_SCORE   = 10
# Bonus per extra bubble di atas 3
EXTRA_BUBBLE_BONUS  = 15
# Bonus drop (bubble melayang jatuh)
DROP_SCORE_PER      = 20
# Bonus per level
LEVEL_MULTIPLIER    = 5

# Combo system
COMBO_DECAY_SHOTS   = 2    # Combo reset setelah N tembakan tanpa match
MAX_COMBO           = 10   # Combo maksimum

# Streak system
STREAK_BONUS_TABLE = {
    3:  50,
    5:  150,
    7:  300,
    10: 750,
    15: 2000,
}

# Perfect shot bonus (tembak tepat sasaran, tidak memantul)
PERFECT_SHOT_BONUS = 25
# Speed bonus (dari shot timer multiplier)


# ============================================================
# SCORE EVENT — Data class
# ============================================================

class ScoreEvent:
    """Representasi satu kejadian scoring"""

    def __init__(self, base, multiplier=1.0, combo=1, label="", x=0, y=0, color=None):
        self.base = base
        self.multiplier = multiplier
        self.combo = combo
        self.label = label
        self.x = x
        self.y = y
        self.color = color or QColor(255, 220, 50)
        self.total = int(base * multiplier * combo)


# ============================================================
# SCORE MANAGER — Otak scoring
# ============================================================

class ScoreManager(QObject):
    """
    Mengelola semua aspek scoring:
    - Kalkulasi poin
    - Combo tracking
    - Streak tracking
    - High score & leaderboard
    """

    score_updated    = Signal(int)          # Total score saat ini
    combo_updated    = Signal(int)          # Combo count terbaru
    streak_updated   = Signal(int)          # Streak count
    score_event      = Signal(object)       # ScoreEvent untuk popup
    highscore_beaten = Signal(int)          # Saat high score dipecahkan

    def __init__(self, save_dir: Path):
        super().__init__()
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # State scoring
        self._score = 0
        self._high_score = 0
        self._combo = 0
        self._combo_no_match_count = 0
        self._streak = 0          # Berapa tembakan berturut-turut menghasilkan match
        self._total_shots = 0
        self._total_pops  = 0
        self._total_drops = 0
        self._best_combo  = 0
        self._level = 1

        # Load high score
        self._load_highscore()

    # --- PUBLIC API ---

    def reset(self):
        self._score = 0
        self._combo = 0
        self._combo_no_match_count = 0
        self._streak = 0
        self._total_shots = 0
        self._total_pops = 0
        self._total_drops = 0
        self._best_combo = 0
        self.score_updated.emit(0)
        self.combo_updated.emit(0)

    def set_level(self, level: int):
        self._level = level

    def on_shot_fired(self):
        """Dipanggil setiap kali bola ditembak"""
        self._total_shots += 1
        self._combo_no_match_count += 1
        if self._combo_no_match_count >= COMBO_DECAY_SHOTS:
            self._reset_combo()

    def on_match(self, match_size: int, time_multiplier: float = 1.0,
                  was_bounced: bool = False, x: float = 0, y: float = 0,
                  rush_bonus: int = 0):
        """
        Dipanggil saat terjadi match.

        Args:
            match_size: Jumlah bubble yang cocok
            time_multiplier: Multiplier dari shot timer
            was_bounced: Apakah tembakan memantul (kurangi bonus)
            x, y: Posisi event untuk popup
            rush_bonus: Bonus dari rush mode
        """
        self._combo_no_match_count = 0
        self._combo = min(self._combo + 1, MAX_COMBO)
        self._streak += 1
        self._total_pops += match_size

        if self._combo > self._best_combo:
            self._best_combo = self._combo

        # Hitung skor dasar
        base = BASE_BUBBLE_SCORE * match_size
        base += EXTRA_BUBBLE_BONUS * max(0, match_size - 3)
        base += self._level * LEVEL_MULTIPLIER
        base += rush_bonus

        if not was_bounced:
            base += PERFECT_SHOT_BONUS

        # Combo multiplier
        combo_mult = 1.0 + (self._combo - 1) * 0.3  # +0.3x per combo
        combo_mult = min(combo_mult, 4.0)

        total_mult = round(time_multiplier * combo_mult, 1)
        final = int(base * total_mult)

        # Streak bonus
        streak_bonus = STREAK_BONUS_TABLE.get(self._streak, 0)
        final += streak_bonus

        # Tentukan warna popup
        if total_mult >= 3.0:
            color = QColor(255, 50, 50)
        elif total_mult >= 2.0:
            color = QColor(255, 165, 0)
        elif total_mult >= 1.5:
            color = QColor(255, 220, 50)
        else:
            color = QColor(180, 255, 180)

        label = self._build_label(match_size, total_mult, streak_bonus)

        event = ScoreEvent(base, total_mult, 1, label, x, y, color)
        event.total = final

        self._add_score(final)
        self.combo_updated.emit(self._combo)
        self.streak_updated.emit(self._streak)
        self.score_event.emit(event)

        self.combo_updated.emit(self._combo)

    def on_drops(self, count: int, x: float = 0, y: float = 0):
        """Poin untuk bubble yang jatuh"""
        if count <= 0:
            return
        total = count * DROP_SCORE_PER
        self._total_drops += count

        event = ScoreEvent(total, 1.0, 1, f"DROP x{count}", x, y, QColor(100, 200, 255))
        self._add_score(total)
        self.score_event.emit(event)

    def on_powerup_effect(self, destroyed: int, bonus_per: int, x: float = 0, y: float = 0, label: str = "POWER!"):
        """Poin dari efek power-up"""
        total = destroyed * bonus_per
        event = ScoreEvent(total, 1.0, 1, label, x, y, QColor(255, 80, 200))
        self._add_score(total)
        self.score_event.emit(event)

    def _reset_combo(self):
        if self._combo > 0:
            self._combo = 0
            self._streak = 0
            self.combo_updated.emit(0)

    def _build_label(self, match_size, mult, streak_bonus):
        parts = []
        if match_size >= 9:
            parts.append("ULTRA!")
        elif match_size >= 6:
            parts.append("SUPER!")
        elif match_size >= 3:
            parts.append("NICE!")
        if self._combo >= 5:
            parts.append(f"COMBO x{self._combo}!")
        elif self._combo >= 3:
            parts.append(f"x{self._combo}")
        if streak_bonus > 0:
            parts.append(f"+STREAK")
        if mult >= 2.5:
            parts.append(f"⚡{mult}x")
        return " ".join(parts) if parts else "GOOD"

    def _add_score(self, amount: int):
        self._score += amount
        if self._score > self._high_score:
            was_beaten = self._high_score > 0
            self._high_score = self._score
            if was_beaten:
                self.highscore_beaten.emit(self._high_score)
            self._save_highscore()
        self.score_updated.emit(self._score)

    # --- PROPERTIES ---

    @property
    def score(self): return self._score

    @score.setter
    def score(self, val):
        self._score = val
        self.score_updated.emit(val)

    @property
    def high_score(self): return self._high_score

    @high_score.setter
    def high_score(self, val):
        self._high_score = val

    @property
    def combo(self): return self._combo

    @property
    def streak(self): return self._streak

    @property
    def total_shots(self): return self._total_shots

    @property
    def total_pops(self): return self._total_pops

    @property
    def best_combo(self): return self._best_combo

    def get_stats(self):
        return {
            'score': self._score,
            'high_score': self._high_score,
            'total_shots': self._total_shots,
            'total_pops': self._total_pops,
            'total_drops': self._total_drops,
            'best_combo': self._best_combo,
        }

    # --- SAVE / LOAD ---

    def _save_highscore(self):
        try:
            path = self.save_dir / "highscore.json"
            with open(path, 'w') as f:
                json.dump({'high_score': self._high_score}, f)
        except Exception as e:
            print(f"ScoreManager save error: {e}")

    def _load_highscore(self):
        try:
            path = self.save_dir / "highscore.json"
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                    self._high_score = data.get('high_score', 0)
        except Exception as e:
            print(f"ScoreManager load error: {e}")


# ============================================================
# SCORE POPUP — Animasi teks melayang di scene
# ============================================================

# ============================================================
# SCORE POPUP — Animasi teks melayang, satu per satu, tidak tumpuk
# ============================================================

# Global pool: batasi popup aktif di scene sekaligus
_active_popups: list = []
_MAX_ACTIVE_POPUPS = 3          # Maksimal popup tampil bersamaan
_POPUP_OFFSET_STEP = 28         # Geser vertikal tiap popup agar tidak tepat tumpuk


class ScorePopup:
    """
    Popup skor yang melayang ke atas lalu fade-out.
    Dikelola secara global agar tidak menumpuk tak terbatas.
    Popup baru akan menggusur yang paling lama jika kuota penuh.
    """

    def __init__(self, scene, event: ScoreEvent, slot: int = 0):
        self.scene = scene
        self._items = []
        self._dead = False

        # --- ukuran font proporsional tapi dibatasi ---
        font_size = min(20, 14 + int(event.total / 120))

        # Posisi: tengah-bawah arena dengan offset per slot agar tidak 100% overlap
        x = event.x
        y = event.y - slot * _POPUP_OFFSET_STEP

        # Teks angka utama ("+617")
        main_text = QGraphicsTextItem(f"+{event.total:,}")
        font = QFont("Segoe UI Black", font_size, QFont.Black)
        main_text.setFont(font)
        main_text.setDefaultTextColor(event.color)
        main_text.setZValue(400)
        bw = main_text.boundingRect().width()
        main_text.setPos(x - bw / 2, y)
        scene.addItem(main_text)
        self._items.append(main_text)

        # Sub-label (NICE!, COMBO x5, dll) — hanya jika ada dan tidak kosong
        if event.label:
            sub_text = QGraphicsTextItem(event.label)
            sub_font = QFont("Segoe UI", 9, QFont.Bold)
            sub_text.setFont(sub_font)
            sub_text.setDefaultTextColor(event.color.lighter(150))
            sub_text.setZValue(400)
            sw = sub_text.boundingRect().width()
            sub_text.setPos(x - sw / 2, y + font_size + 4)
            scene.addItem(sub_text)
            self._items.append(sub_text)

        # Animasi: naik + fade, selesai dalam ~50 frame (~800ms)
        self._frame = 0
        self._max_frame = 50
        self._vy = -1.8          # kecepatan naik (pixel per frame)
        self._timer = QTimer()
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._animate)
        self._timer.start()

    def _animate(self):
        if self._dead:
            return
        self._frame += 1
        # Fade mulai dari 40% animasi, bukan langsung
        fade_start = 0.4
        progress = self._frame / self._max_frame
        if progress > fade_start:
            opacity = max(0.0, 1.0 - (progress - fade_start) / (1.0 - fade_start))
        else:
            opacity = 1.0

        for item in self._items:
            item.setY(item.y() + self._vy)
            item.setOpacity(opacity)
            # Perlambat naik seiring waktu
        self._vy *= 0.97

        if self._frame >= self._max_frame:
            self._kill()

    def _kill(self):
        """Hapus popup dari scene dan dari pool global."""
        if self._dead:
            return
        self._dead = True
        self._timer.stop()
        for item in self._items:
            try:
                if item.scene():
                    self.scene.removeItem(item)
            except Exception:
                pass
        self._items.clear()
        # Keluarkan dari pool global
        try:
            _active_popups.remove(self)
        except ValueError:
            pass


# ============================================================
# LEADERBOARD
# ============================================================

class Leaderboard:
    """Top 10 skor lokal dengan nama dan level"""

    MAX_ENTRIES = 10

    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self._entries = []
        self._load()

    def add_entry(self, score: int, level: int, name: str = "PLAYER",
                  total_shots: int = 0, best_combo: int = 0, playtime_sec: int = 0):
        entry = {
            'name': name[:12],
            'score': score,
            'level': level,
            'shots': total_shots,
            'combo': best_combo,
            'time': playtime_sec,
        }
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e['score'], reverse=True)
        self._entries = self._entries[:self.MAX_ENTRIES]
        self._save()

    def is_high_score(self, score: int) -> bool:
        if len(self._entries) < self.MAX_ENTRIES:
            return True
        return score > self._entries[-1]['score']

    def get_rank(self, score: int) -> int:
        """Kembalikan rank (1-based) dari score ini"""
        for i, e in enumerate(self._entries):
            if score >= e['score']:
                return i + 1
        return len(self._entries) + 1

    def get_entries(self):
        return list(self._entries)

    def _save(self):
        try:
            path = self.save_dir / "leaderboard.json"
            with open(path, 'w') as f:
                json.dump(self._entries, f, indent=2)
        except Exception as e:
            print(f"Leaderboard save error: {e}")

    def _load(self):
        try:
            path = self.save_dir / "leaderboard.json"
            if path.exists():
                with open(path, 'r') as f:
                    self._entries = json.load(f)
        except Exception as e:
            print(f"Leaderboard load error: {e}")
            self._entries = []


# ============================================================
# SINGLETON
# ============================================================

_score_manager = None
_leaderboard = None


def get_score_manager(save_dir: Path = None) -> ScoreManager:
    global _score_manager
    if _score_manager is None:
        if save_dir is None:
            save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6" / "saves"
        _score_manager = ScoreManager(save_dir)
    return _score_manager


def get_leaderboard(save_dir: Path = None) -> Leaderboard:
    global _leaderboard
    if _leaderboard is None:
        if save_dir is None:
            save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6" / "saves"
        _leaderboard = Leaderboard(save_dir)
    return _leaderboard


def spawn_score_popup(scene, event: ScoreEvent) -> 'ScorePopup | None':
    """
    Tampilkan popup skor dengan manajemen pool global.
    - Maksimal _MAX_ACTIVE_POPUPS popup aktif bersamaan.
    - Jika penuh, popup tertua langsung di-kill sebelum yang baru dibuat.
    - Setiap popup mendapat slot (vertikal offset) agar tidak 100% tumpuk.
    """
    global _active_popups

    # Bersihkan popup yang sudah mati dari pool
    _active_popups = [p for p in _active_popups if not p._dead]

    # Jika pool penuh, paksa kill popup TERTUA
    while len(_active_popups) >= _MAX_ACTIVE_POPUPS:
        _active_popups[0]._kill()
        _active_popups = [p for p in _active_popups if not p._dead]

    # Tentukan slot (0, 1, 2) berdasarkan jumlah popup aktif saat ini
    slot = len(_active_popups)

    popup = ScorePopup(scene, event, slot=slot)
    _active_popups.append(popup)
    return popup
