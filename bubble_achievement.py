"""
bubble_achievement.py - Sistem Achievement untuk Macan Bubble Shooter
Modul ini mengelola:
- Definisi semua achievement
- Progress tracking
- Unlock notification
- Persistence ke disk
- Achievement HUD display
"""

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem
from PySide6.QtGui import QColor, QBrush, QPen, QLinearGradient, QFont, QRadialGradient
from PySide6.QtCore import Qt
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# ACHIEVEMENT DEFINITION
# ============================================================

@dataclass
class AchievementDef:
    id: str
    name: str
    description: str
    icon: str                  # Emoji icon
    target: int                # Target value
    category: str              # 'score', 'combat', 'skill', 'time', 'special'
    hidden: bool = False       # Tersembunyi sampai unlock
    reward_score: int = 0      # Bonus score saat unlock


# Semua achievement yang tersedia
ALL_ACHIEVEMENTS = [

    # ── SCORE ──────────────────────────────────────────
    AchievementDef("score_1k",    "Rookie",         "Reach 1,000 points",             "🌱", 1_000,   "score",  reward_score=100),
    AchievementDef("score_5k",    "Sharpshooter",   "Reach 5,000 points",             "🎯", 5_000,   "score",  reward_score=250),
    AchievementDef("score_10k",   "Expert",         "Reach 10,000 points",            "⭐", 10_000,  "score",  reward_score=500),
    AchievementDef("score_25k",   "Master",         "Reach 25,000 points",            "💫", 25_000,  "score",  reward_score=1000),
    AchievementDef("score_50k",   "Grand Master",   "Reach 50,000 points",            "🏆", 50_000,  "score",  reward_score=2500),
    AchievementDef("score_100k",  "Legend",         "Reach 100,000 points",           "👑", 100_000, "score",  hidden=True, reward_score=5000),

    # ── COMBAT ─────────────────────────────────────────
    AchievementDef("pop_10",      "First Pops",     "Pop 10 bubbles",                 "💥", 10,      "combat", reward_score=50),
    AchievementDef("pop_100",     "Demolisher",     "Pop 100 bubbles",                "💣", 100,     "combat", reward_score=150),
    AchievementDef("pop_500",     "Destructor",     "Pop 500 bubbles",                "🔥", 500,     "combat", reward_score=400),
    AchievementDef("pop_1000",    "Annihilator",    "Pop 1,000 bubbles",              "☄️", 1000,   "combat", reward_score=800),
    AchievementDef("big_match",   "Cluster Bomb",   "Match 9+ bubbles at once",       "🌋", 9,       "combat", reward_score=300),
    AchievementDef("drop_20",     "Gravity King",   "Drop 20 floating bubbles",       "⬇️", 20,      "combat", reward_score=200),
    AchievementDef("chain_3",     "Chain React",    "Trigger 3 chain reactions",      "⛓️", 3,       "combat", reward_score=250),

    # ── COMBO & SKILL ───────────────────────────────────
    AchievementDef("combo_3",     "Triple Kill",    "Reach combo x3",                 "🔱", 3,       "skill",  reward_score=100),
    AchievementDef("combo_5",     "Penta Kill",     "Reach combo x5",                 "⚡", 5,       "skill",  reward_score=300),
    AchievementDef("combo_8",     "Ultra Kill",     "Reach combo x8",                 "🌀", 8,       "skill",  hidden=True, reward_score=750),
    AchievementDef("streak_5",    "Hot Streak",     "5 consecutive matching shots",   "🔥", 5,       "skill",  reward_score=200),
    AchievementDef("streak_10",   "On Fire!",       "10 consecutive matching shots",  "🌟", 10,      "skill",  hidden=True, reward_score=600),
    AchievementDef("speed_5",     "Lightning",      "Fire 5 shots under 2 seconds",   "⚡", 5,       "skill",  reward_score=150),
    AchievementDef("speed_3x",    "Speed Shooter",  "Achieve 3.0x speed multiplier",  "💨", 1,       "skill",  reward_score=200),

    # ── LEVEL ───────────────────────────────────────────
    AchievementDef("level_3",     "Moving Up",      "Reach Level 3",                  "📈", 3,       "score",  reward_score=200),
    AchievementDef("level_5",     "Veteran",        "Reach Level 5",                  "🎖️", 5,       "score",  reward_score=500),
    AchievementDef("level_10",    "Elite",          "Reach Level 10",                 "🌠", 10,      "score",  hidden=True, reward_score=1500),

    # ── POWER-UP ────────────────────────────────────────
    AchievementDef("use_bomb",    "Boom!",          "Use the Bomb power",             "💣", 1,       "skill",  reward_score=100),
    AchievementDef("use_laser",   "Pew Pew",        "Use the Laser power",            "⚡", 1,       "skill",  reward_score=100),
    AchievementDef("use_rainbow", "Rainbow",        "Use the Rainbow bubble",         "🌈", 1,       "skill",  reward_score=100),
    AchievementDef("use_fireball","Dragon Fire",    "Use the Fireball power",         "🐉", 1,       "skill",  reward_score=150),
    AchievementDef("use_freeze",  "Deep Freeze",    "Use the Freeze power",           "❄️", 1,       "skill",  reward_score=100),
    AchievementDef("power_master","Power Master",   "Use all power types",            "🎮", 5,       "skill",  hidden=True, reward_score=1000),

    # ── TIME & SURVIVAL ─────────────────────────────────
    AchievementDef("survive_5min","Survivor",       "Survive for 5 minutes",          "⏱️", 300,     "time",   reward_score=300),
    AchievementDef("survive_10m", "Endurance",      "Survive for 10 minutes",         "🛡️", 600,     "time",   hidden=True, reward_score=700),
    AchievementDef("shots_50",    "Gunner",         "Fire 50 shots",                  "🎱", 50,      "combat", reward_score=100),
    AchievementDef("shots_200",   "Out of Ammo",    "Fire 200 shots",                 "🔫", 200,     "combat", reward_score=300),

    # ── SPECIAL / HIDDEN ────────────────────────────────
    AchievementDef("first_blood", "First Blood",    "Your very first match",          "🩸", 1,       "special",reward_score=50),
    AchievementDef("no_miss_10",  "Precision",      "10 shots without missing",       "🎯", 10,      "special",hidden=True, reward_score=400),
    AchievementDef("rush_survive","Never Give Up",  "Survive Rush Mode",              "😤", 1,       "special",hidden=True, reward_score=500),
    AchievementDef("comeback",    "Comeback King",  "Clear grid at danger level 3",   "🦅", 1,       "special",hidden=True, reward_score=1000),
]

# Dict lookup by ID
ACHIEVEMENT_MAP = {a.id: a for a in ALL_ACHIEVEMENTS}


# ============================================================
# ACHIEVEMENT STATE
# ============================================================

class AchievementProgress:
    def __init__(self, ach_def: AchievementDef):
        self.id = ach_def.id
        self.current = 0
        self.unlocked = False
        self.unlock_time = None

    def to_dict(self):
        return {'current': self.current, 'unlocked': self.unlocked}

    @classmethod
    def from_dict(cls, ach_def, d):
        obj = cls(ach_def)
        obj.current = d.get('current', 0)
        obj.unlocked = d.get('unlocked', False)
        return obj


# ============================================================
# ACHIEVEMENT MANAGER
# ============================================================

class AchievementManager(QObject):
    """
    Core engine achievement.
    Tracking progress dan emit signal saat unlock.
    """

    achievement_unlocked = Signal(object)  # AchievementDef

    def __init__(self, save_dir: Path):
        super().__init__()
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._progress = {a.id: AchievementProgress(a) for a in ALL_ACHIEVEMENTS}
        self._load()

    # --- TRIGGER METHODS (dipanggil oleh GameScene) ---

    def on_score(self, total_score: int):
        self._check_threshold('score_1k', total_score)
        self._check_threshold('score_5k', total_score)
        self._check_threshold('score_10k', total_score)
        self._check_threshold('score_25k', total_score)
        self._check_threshold('score_50k', total_score)
        self._check_threshold('score_100k', total_score)

    def on_pop(self, total_pops: int, single_match_size: int = 0):
        self._check_threshold('pop_10', total_pops)
        self._check_threshold('pop_100', total_pops)
        self._check_threshold('pop_500', total_pops)
        self._check_threshold('pop_1000', total_pops)
        if single_match_size >= 9:
            self._unlock_once('big_match')
        # First blood
        if total_pops >= 3:
            self._unlock_once('first_blood')

    def on_drop(self, total_drops: int):
        self._check_threshold('drop_20', total_drops)

    def on_combo(self, combo: int):
        self._check_threshold('combo_3', combo)
        self._check_threshold('combo_5', combo)
        self._check_threshold('combo_8', combo)

    def on_streak(self, streak: int):
        self._check_threshold('streak_5', streak)
        self._check_threshold('streak_10', streak)

    def on_shots(self, total_shots: int, no_miss_streak: int = 0):
        self._check_threshold('shots_50', total_shots)
        self._check_threshold('shots_200', total_shots)
        self._check_threshold('no_miss_10', no_miss_streak)

    def on_level(self, level: int):
        self._check_threshold('level_3', level)
        self._check_threshold('level_5', level)
        self._check_threshold('level_10', level)

    def on_power_used(self, power_type: str):
        power_map = {
            'bomb': 'use_bomb',
            'laser': 'use_laser',
            'rainbow': 'use_rainbow',
            'fireball': 'use_fireball',
            'freeze': 'use_freeze',
        }
        ach_id = power_map.get(power_type)
        if ach_id:
            self._unlock_once(ach_id)
        # Check power_master
        used_powers = sum(1 for pid in power_map.values() if self._progress[pid].unlocked)
        self._check_threshold('power_master', used_powers)

    def on_speed_shot(self, speed_shot_streak: int, multiplier: float):
        self._check_threshold('speed_5', speed_shot_streak)
        if multiplier >= 3.0:
            self._unlock_once('speed_3x')

    def on_survive_time(self, seconds: int):
        self._check_threshold('survive_5min', seconds)
        self._check_threshold('survive_10m', seconds)

    def on_rush_survived(self):
        self._unlock_once('rush_survive')

    def on_comeback(self):
        self._unlock_once('comeback')

    def on_chain_reaction(self, chain_count: int):
        self._check_threshold('chain_3', chain_count)

    # --- INTERNAL ---

    def _check_threshold(self, ach_id: str, current_value: int):
        prog = self._progress.get(ach_id)
        if not prog or prog.unlocked:
            return
        prog.current = current_value
        ach_def = ACHIEVEMENT_MAP[ach_id]
        if current_value >= ach_def.target:
            self._unlock(ach_id)

    def _unlock_once(self, ach_id: str):
        prog = self._progress.get(ach_id)
        if not prog or prog.unlocked:
            return
        self._unlock(ach_id)

    def _unlock(self, ach_id: str):
        prog = self._progress[ach_id]
        if prog.unlocked:
            return
        prog.unlocked = True
        prog.current = ACHIEVEMENT_MAP[ach_id].target
        ach_def = ACHIEVEMENT_MAP[ach_id]
        self.achievement_unlocked.emit(ach_def)
        self._save()

    def get_all_progress(self):
        result = []
        for ach in ALL_ACHIEVEMENTS:
            prog = self._progress[ach.id]
            result.append({
                'def': ach,
                'current': prog.current,
                'unlocked': prog.unlocked,
                'progress_pct': min(1.0, prog.current / ach.target) if ach.target > 0 else 1.0,
            })
        return result

    def get_unlocked_count(self):
        return sum(1 for p in self._progress.values() if p.unlocked)

    def get_total_count(self):
        return len(ALL_ACHIEVEMENTS)

    # --- SAVE / LOAD ---

    def _save(self):
        try:
            data = {k: v.to_dict() for k, v in self._progress.items()}
            with open(self.save_dir / "achievements.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Achievement save error: {e}")

    def _load(self):
        try:
            path = self.save_dir / "achievements.json"
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                for ach_id, d in data.items():
                    if ach_id in self._progress:
                        ach_def = ACHIEVEMENT_MAP[ach_id]
                        self._progress[ach_id] = AchievementProgress.from_dict(ach_def, d)
        except Exception as e:
            print(f"Achievement load error: {e}")


# ============================================================
# ACHIEVEMENT TOAST — Pop-up notifikasi di scene
# ============================================================

class AchievementToast:
    """
    Panel notifikasi achievement yang muncul di pojok kanan atas.
    Tampil 3 detik lalu fade out.
    """

    TOAST_W = 320
    TOAST_H = 72
    PADDING = 14

    def __init__(self, scene, ach_def: AchievementDef, scene_width: int):
        self.scene = scene
        self._items = []

        x = scene_width - self.TOAST_W - 10
        y = 60  # Di bawah HUD

        # Background card
        bg = QGraphicsRectItem(x, y, self.TOAST_W, self.TOAST_H)
        bg.setBrush(QBrush(QColor(15, 20, 40, 230)))
        bg.setPen(QPen(QColor(255, 215, 0), 2))
        bg.setZValue(600)
        scene.addItem(bg)
        self._items.append(bg)

        # Gold accent bar kiri
        accent = QGraphicsRectItem(x, y, 5, self.TOAST_H)
        accent.setBrush(QBrush(QColor(255, 215, 0)))
        accent.setPen(QPen(Qt.NoPen))
        accent.setZValue(601)
        scene.addItem(accent)
        self._items.append(accent)

        # Icon
        icon_label = QGraphicsTextItem(ach_def.icon)
        icon_font = QFont("Segoe UI Emoji", 26)
        icon_label.setFont(icon_font)
        icon_label.setPos(x + 12, y + 10)
        icon_label.setZValue(602)
        scene.addItem(icon_label)
        self._items.append(icon_label)

        # Title (ACHIEVEMENT UNLOCKED!)
        title = QGraphicsTextItem("ACHIEVEMENT UNLOCKED!")
        title_font = QFont("Segoe UI", 9, QFont.Bold)
        title.setFont(title_font)
        title.setDefaultTextColor(QColor(255, 215, 0))
        title.setPos(x + 60, y + 8)
        title.setZValue(602)
        scene.addItem(title)
        self._items.append(title)

        # Achievement name
        name_label = QGraphicsTextItem(ach_def.name)
        name_font = QFont("Segoe UI Black", 13, QFont.Black)
        name_label.setFont(name_font)
        name_label.setDefaultTextColor(QColor(255, 255, 255))
        name_label.setPos(x + 60, y + 26)
        name_label.setZValue(602)
        scene.addItem(name_label)
        self._items.append(name_label)

        # Description
        desc_label = QGraphicsTextItem(ach_def.description)
        desc_font = QFont("Segoe UI", 9)
        desc_label.setFont(desc_font)
        desc_label.setDefaultTextColor(QColor(160, 200, 255))
        desc_label.setPos(x + 60, y + 50)
        desc_label.setZValue(602)
        scene.addItem(desc_label)
        self._items.append(desc_label)

        # Reward label
        if ach_def.reward_score > 0:
            reward = QGraphicsTextItem(f"+{ach_def.reward_score:,}")
            reward_font = QFont("Segoe UI", 10, QFont.Bold)
            reward.setFont(reward_font)
            reward.setDefaultTextColor(QColor(100, 255, 150))
            rw = reward.boundingRect().width()
            reward.setPos(x + self.TOAST_W - rw - 8, y + 28)
            reward.setZValue(602)
            scene.addItem(reward)
            self._items.append(reward)

        # Auto-dismiss setelah 3.5 detik
        self._frame = 0
        self._phase = 0  # 0=slide in, 1=hold, 2=fade out
        self._start_x = scene_width + 10
        self._target_x = x
        self._current_x = float(self._start_x)

        for item in self._items:
            item.setPos(item.x() + (self._start_x - x), item.y())

        self._timer = QTimer()
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._animate)
        self._timer.start()

    def _animate(self):
        self._frame += 1

        if self._phase == 0:
            # Slide in
            dx = (self._target_x - self._current_x) * 0.25
            self._current_x += dx
            offset = self._current_x - self._target_x
            for item in self._items:
                item.moveBy(dx, 0)
            if abs(offset) < 1.0:
                self._phase = 1
                self._frame = 0

        elif self._phase == 1:
            # Hold 3 detik
            if self._frame > 180:
                self._phase = 2
                self._frame = 0

        elif self._phase == 2:
            # Fade out
            opacity = max(0.0, 1.0 - self._frame / 30.0)
            for item in self._items:
                item.setOpacity(opacity)
            if self._frame >= 30:
                self._timer.stop()
                for item in self._items:
                    if item.scene():
                        self.scene.removeItem(item)


# ============================================================
# SINGLETON
# ============================================================

_ach_manager = None


def get_achievement_manager(save_dir: Path = None) -> AchievementManager:
    global _ach_manager
    if _ach_manager is None:
        if save_dir is None:
            save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6" / "saves"
        _ach_manager = AchievementManager(save_dir)
    return _ach_manager


def show_achievement_toast(scene, ach_def: AchievementDef, scene_width: int) -> AchievementToast:
    """Helper untuk menampilkan toast di scene"""
    return AchievementToast(scene, ach_def, scene_width)
