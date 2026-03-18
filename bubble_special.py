"""
bubble_special.py — Boss Bubbles, Obstacle Bubbles, Color-blind Mode, Replay System

All four feature subsystems in one module to keep satellite count manageable.
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QObject, QTimer, Signal
from PySide6.QtGui import (QColor, QBrush, QPen, QFont, QRadialGradient,
                            QLinearGradient)
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsTextItem,
                                QGraphicsRectItem, QGraphicsLineItem,
                                QGraphicsScene)


# ══════════════════════════════════════════════════════════════════════════════
# 1. BOSS BUBBLE
# ══════════════════════════════════════════════════════════════════════════════

BOSS_MIN_HP = 2   # Default HP for a boss bubble
BOSS_MAX_HP = 5   # HP for tough boss bubbles (higher levels)

# Color-blind safe symbols (drawn on bubbles)
COLORBLIND_SYMBOLS = ["●", "■", "▲", "★", "♦", "✚"]


class BossBubble(QObject, QGraphicsEllipseItem):
    """
    A large bubble that requires multiple direct hits to destroy.
    Displayed with a HP counter and a pulsing glow ring.
    """

    destroyed = Signal(object)   # emits self when HP reaches 0

    def __init__(self, color_index: int, x: float, y: float,
                 hp: int = BOSS_MIN_HP, radius: int = 30):
        QObject.__init__(self)
        QGraphicsEllipseItem.__init__(self, -radius, -radius, radius * 2, radius * 2)

        self.color_index = color_index
        self.radius_val  = radius
        self.max_hp      = hp
        self.current_hp  = hp
        self.row         = 0
        self.col         = 0
        self.is_boss     = True

        self.setPos(x, y)
        self._setup_appearance()

        # HP text label
        self._hp_label = QGraphicsTextItem(str(self.current_hp), self)
        font = QFont("Segoe UI Black", int(radius * 0.55), QFont.Black)
        self._hp_label.setFont(font)
        self._hp_label.setDefaultTextColor(QColor(255, 255, 255))
        self._center_label()

        # Pulsing glow ring
        self._ring = QGraphicsEllipseItem(
            -(radius + 6), -(radius + 6),
            (radius + 6) * 2, (radius + 6) * 2, self)
        self._ring.setBrush(QBrush(Qt.NoBrush))
        self._ring.setPen(QPen(QColor(255, 215, 0, 180), 3))
        self._ring.setZValue(-1)

        self._pulse_frame = 0
        self._pulse_timer = QTimer()
        self._pulse_timer.setInterval(50)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.start()

    # ── Appearance ────────────────────────────────────────────────────────────

    def _setup_appearance(self):
        PALETTE = [
            (QColor(255, 69, 58),  QColor(255, 134, 124), QColor(160, 20, 10)),
            (QColor(50, 215, 75),  QColor(120, 255, 140), QColor(20, 120, 40)),
            (QColor(10, 132, 255), QColor(100, 180, 255), QColor(0, 60, 140)),
            (QColor(255, 214, 10), QColor(255, 240, 100), QColor(180, 140, 0)),
            (QColor(191, 90, 242), QColor(220, 150, 255), QColor(100, 30, 140)),
            (QColor(100, 210, 255),QColor(180, 240, 255), QColor(0, 100, 140)),
        ]
        base, light, dark = PALETTE[self.color_index % len(PALETTE)]

        grad = QRadialGradient(-self.radius_val * 0.3, -self.radius_val * 0.3,
                               self.radius_val * 1.8)
        grad.setColorAt(0, light)
        grad.setColorAt(0.35, base)
        grad.setColorAt(0.75, dark)
        grad.setColorAt(1.0, dark.darker(130))
        self.setBrush(QBrush(grad))
        self.setPen(QPen(QColor(255, 215, 0), 3))   # Gold border = boss indicator

    def _center_label(self):
        bw = self._hp_label.boundingRect().width()
        bh = self._hp_label.boundingRect().height()
        self._hp_label.setPos(-bw / 2, -bh / 2)

    def _pulse(self):
        self._pulse_frame += 1
        t = self._pulse_frame * 0.15
        alpha = int(120 + 80 * math.sin(t))
        hp_ratio = self.current_hp / self.max_hp
        # Ring turns red as HP drops
        r = int(255)
        g = int(215 * hp_ratio)
        self._ring.setPen(QPen(QColor(r, g, 0, alpha), 3))

    # ── Hit logic ─────────────────────────────────────────────────────────────

    def take_hit(self) -> bool:
        """
        Register one hit. Returns True if the boss is still alive, False if destroyed.
        """
        self.current_hp -= 1
        self._hp_label.setPlainText(str(max(0, self.current_hp)))
        self._center_label()

        # Flash white on hit
        self.setPen(QPen(QColor(255, 255, 255), 4))
        QTimer.singleShot(120, lambda: self.setPen(QPen(QColor(255, 215, 0), 3)))

        if self.current_hp <= 0:
            self._pulse_timer.stop()
            self.destroyed.emit(self)
            return False
        return True

    def cleanup(self):
        self._pulse_timer.stop()


# ── Boss spawn helper ─────────────────────────────────────────────────────────

def should_spawn_boss(level: int, match_size: int) -> bool:
    """
    Probabilistic boss spawn: becomes more common at higher levels.
    Only triggered after a match of 5+ bubbles.
    """
    if match_size < 5:
        return False
    base_chance = 5 + level * 2     # 7 % at lv1 → 25 % at lv10
    return random.randint(1, 100) <= min(base_chance, 30)


def create_boss_bubble(color_index: int, x: float, y: float, level: int) -> BossBubble:
    hp = min(BOSS_MIN_HP + level // 2, BOSS_MAX_HP)
    return BossBubble(color_index, x, y, hp=hp)


# ══════════════════════════════════════════════════════════════════════════════
# 2. OBSTACLE / WALL BUBBLE
# ══════════════════════════════════════════════════════════════════════════════

OBSTACLE_COLOR_INDEX = -2    # Reserved sentinel value in the grid


class ObstacleBubble(QGraphicsEllipseItem):
    """
    An indestructible bubble that cannot be matched or shot through.
    Must be cleared by popping all surrounding bubbles so it becomes
    a floating island and drops naturally.
    """

    def __init__(self, x: float, y: float, radius: int = 22):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.radius_val  = radius
        self.color_index = OBSTACLE_COLOR_INDEX
        self.is_obstacle = True
        self.row         = 0
        self.col         = 0
        self.setPos(x, y)
        self._setup_appearance()

    def _setup_appearance(self):
        # Dark steel/concrete look
        grad = QRadialGradient(-self.radius_val * 0.3, -self.radius_val * 0.3,
                               self.radius_val * 1.5)
        grad.setColorAt(0, QColor(160, 170, 180))
        grad.setColorAt(0.4, QColor(90, 95, 105))
        grad.setColorAt(1.0, QColor(40, 45, 55))
        self.setBrush(QBrush(grad))
        self.setPen(QPen(QColor(200, 210, 220), 2))

        # "🚫" / "X" label
        label = QGraphicsTextItem("✕", self)
        font  = QFont("Segoe UI Black", int(self.radius_val * 0.7), QFont.Black)
        label.setFont(font)
        label.setDefaultTextColor(QColor(220, 230, 240, 200))
        bw = label.boundingRect().width()
        bh = label.boundingRect().height()
        label.setPos(-bw / 2, -bh / 2)


def obstacle_chance(level: int) -> float:
    """Probability (0–1) of a cell in the daily/normal grid becoming an obstacle."""
    return min(0.04 + level * 0.01, 0.15)   # 4 % at lv1 → 15 % at lv11+


# ══════════════════════════════════════════════════════════════════════════════
# 3. COLOR-BLIND MODE
# ══════════════════════════════════════════════════════════════════════════════

# Per-color shape symbols and high-contrast replacement colors
COLORBLIND_CONFIG = [
    {"symbol": "●", "cb_color": QColor(0,   114, 178)},   # Blue
    {"symbol": "■", "cb_color": QColor(230, 159,  0)},    # Orange/Yellow
    {"symbol": "▲", "cb_color": QColor(0,   158, 115)},   # Green
    {"symbol": "★", "cb_color": QColor(213,  94,   0)},   # Vermillion
    {"symbol": "♦", "cb_color": QColor(204, 121, 167)},   # Rose/Pink
    {"symbol": "✚", "cb_color": QColor(86,  180, 233)},   # Sky Blue
]

_colorblind_mode: bool = False


def is_colorblind_mode() -> bool:
    return _colorblind_mode


def set_colorblind_mode(enabled: bool):
    global _colorblind_mode
    _colorblind_mode = enabled


def get_cb_symbol(color_index: int) -> str:
    if color_index < 0 or color_index >= len(COLORBLIND_CONFIG):
        return "?"
    return COLORBLIND_CONFIG[color_index]["symbol"]


def get_cb_color(color_index: int) -> QColor:
    if color_index < 0 or color_index >= len(COLORBLIND_CONFIG):
        return QColor(200, 200, 200)
    return COLORBLIND_CONFIG[color_index]["cb_color"]


def apply_colorblind_to_bubble(bubble_item, color_index: int):
    """
    Overlay a symbol on an existing bubble item when color-blind mode is active.
    Call this right after a Bubble is created if colorblind mode is on.
    """
    if not _colorblind_mode:
        return
    symbol = get_cb_symbol(color_index)
    radius = getattr(bubble_item, 'radius_val', 22)
    label  = QGraphicsTextItem(symbol, bubble_item)
    font   = QFont("Segoe UI", int(radius * 0.6), QFont.Bold)
    label.setFont(font)
    label.setDefaultTextColor(QColor(255, 255, 255))
    bw = label.boundingRect().width()
    bh = label.boundingRect().height()
    label.setPos(-bw / 2, -bh / 2 - 2)


# ══════════════════════════════════════════════════════════════════════════════
# 4. REPLAY SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

MAX_REPLAYS = 5        # Keep only the top N replays by score
REPLAY_VERSION = 1


class ReplayEvent:
    """A single recorded action in a replay."""
    __slots__ = ("tick", "kind", "data")

    SHOT  = "shot"    # data: {"angle": float, "color": int}
    SWAP  = "swap"    # data: {}
    MATCH = "match"   # data: {"size": int, "score": int}
    DROP  = "drop"    # data: {"count": int}

    def __init__(self, tick: int, kind: str, data: dict):
        self.tick = tick
        self.kind = kind
        self.data = data

    def to_dict(self) -> dict:
        return {"t": self.tick, "k": self.kind, "d": self.data}

    @classmethod
    def from_dict(cls, d: dict) -> "ReplayEvent":
        return cls(d["t"], d["k"], d["d"])


class ReplayRecorder:
    """
    Records every player action during a game session.
    Attach it to GameScene events; call save() at session end.
    """

    def __init__(self):
        self._events : list[ReplayEvent] = []
        self._tick   : int  = 0
        self._score  : int  = 0
        self._level  : int  = 1
        self._active : bool = False
        self._seed   : int  = 0
        self._start_ts: str = ""

    def start(self, grid_seed: int = 0):
        self._events   = []
        self._tick     = 0
        self._score    = 0
        self._level    = 1
        self._active   = True
        self._seed     = grid_seed
        self._start_ts = datetime.now().isoformat(timespec="seconds")

    def stop(self):
        self._active = False

    def tick(self):
        """Call once per game frame (16 ms)."""
        if self._active:
            self._tick += 1

    def record_shot(self, angle: float, color: int):
        if self._active:
            self._events.append(ReplayEvent(self._tick, ReplayEvent.SHOT,
                                            {"angle": round(angle, 2), "color": color}))

    def record_swap(self):
        if self._active:
            self._events.append(ReplayEvent(self._tick, ReplayEvent.SWAP, {}))

    def record_match(self, size: int, score: int):
        if self._active:
            self._score += score
            self._events.append(ReplayEvent(self._tick, ReplayEvent.MATCH,
                                            {"size": size, "score": score}))

    def record_drop(self, count: int):
        if self._active:
            self._events.append(ReplayEvent(self._tick, ReplayEvent.DROP,
                                            {"count": count}))

    def set_level(self, level: int):
        self._level = level

    def set_final_score(self, score: int):
        self._score = score

    def to_dict(self) -> dict:
        return {
            "version":    REPLAY_VERSION,
            "timestamp":  self._start_ts,
            "score":      self._score,
            "level":      self._level,
            "seed":       self._seed,
            "events":     [e.to_dict() for e in self._events],
        }


class ReplayPlayer:
    """
    Plays back a saved replay by scheduling shot/swap events via QTimer.
    The caller is responsible for actually executing the game actions.
    """

    def __init__(self, data: dict, on_shot=None, on_swap=None, on_done=None):
        self._events  = [ReplayEvent.from_dict(d) for d in data.get("events", [])]
        self._on_shot = on_shot     # callable(angle, color)
        self._on_swap = on_swap     # callable()
        self._on_done = on_done     # callable()
        self._idx     = 0
        self._tick    = 0
        self._timer   = QTimer()
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._step)

    def start(self):
        self._idx  = 0
        self._tick = 0
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _step(self):
        self._tick += 1
        while self._idx < len(self._events):
            ev = self._events[self._idx]
            if ev.tick > self._tick:
                break
            if ev.kind == ReplayEvent.SHOT and self._on_shot:
                self._on_shot(ev.data["angle"], ev.data["color"])
            elif ev.kind == ReplayEvent.SWAP and self._on_swap:
                self._on_swap()
            self._idx += 1

        if self._idx >= len(self._events):
            self._timer.stop()
            if self._on_done:
                self._on_done()


class ReplayManager:
    """Persists the top-N replays to disk."""

    def __init__(self, save_dir: Path):
        self.save_dir  = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._replays  : list[dict] = []
        self._load()

    def save_replay(self, recorder: ReplayRecorder):
        """Attempt to save this session's replay. Keeps top MAX_REPLAYS by score."""
        data = recorder.to_dict()
        if not data["events"]:
            return
        self._replays.append(data)
        self._replays.sort(key=lambda r: r.get("score", 0), reverse=True)
        self._replays = self._replays[:MAX_REPLAYS]
        self._persist()

    def get_replays(self) -> list[dict]:
        """Return list of replay metadata (without event lists) for display."""
        return [
            {
                "timestamp": r.get("timestamp", ""),
                "score":     r.get("score", 0),
                "level":     r.get("level", 1),
                "shots":     sum(1 for e in r.get("events", [])
                                 if e.get("k") == ReplayEvent.SHOT),
            }
            for r in self._replays
        ]

    def get_replay_data(self, index: int) -> dict | None:
        if 0 <= index < len(self._replays):
            return self._replays[index]
        return None

    def _persist(self):
        try:
            path = self.save_dir / "replays.json"
            with open(path, "w") as f:
                json.dump(self._replays, f)
        except Exception as e:
            print(f"ReplayManager save error: {e}")

    def _load(self):
        try:
            path = self.save_dir / "replays.json"
            if path.exists():
                with open(path) as f:
                    self._replays = json.load(f)
        except Exception as e:
            print(f"ReplayManager load error: {e}")
            self._replays = []


# ── Singletons ────────────────────────────────────────────────────────────────

_replay_manager  : ReplayManager  | None = None
_replay_recorder : ReplayRecorder | None = None


def get_replay_manager(save_dir: Path | None = None) -> ReplayManager:
    global _replay_manager
    if _replay_manager is None:
        if save_dir is None:
            save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6" / "saves"
        _replay_manager = ReplayManager(save_dir)
    return _replay_manager


def get_replay_recorder() -> ReplayRecorder:
    global _replay_recorder
    if _replay_recorder is None:
        _replay_recorder = ReplayRecorder()
    return _replay_recorder
