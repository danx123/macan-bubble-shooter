"""
bubble_daily.py — Daily Challenge System
Generates a deterministic daily grid (same for all players on the same date),
tracks the daily score, and exposes a simple comparison leaderboard entry.
"""

import json
import random
import hashlib
from datetime import date, datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal


# ── Grid configuration ────────────────────────────────────────────────────────
DAILY_ROWS      = 8    # Pre-filled rows in the daily challenge
DAILY_COLS      = 20
DAILY_COLORS    = 6    # How many colors to use
DAILY_SHOTS_CAP = 40   # Max shots before the challenge ends (adds pressure)


def _seed_for_today() -> int:
    """Return a deterministic integer seed based on today's ISO date string."""
    today_str = date.today().isoformat()          # e.g. "2026-03-18"
    digest = hashlib.md5(today_str.encode()).hexdigest()
    return int(digest[:8], 16)                    # first 32 bits of MD5


def generate_daily_grid(rows: int = DAILY_ROWS, cols: int = DAILY_COLS) -> list:
    """
    Build a deterministic bubble grid for today.
    Returns a 2-D list of color indices (int) or None (empty cell).
    """
    rng = random.Random(_seed_for_today())
    grid = []
    for row in range(rows):
        row_list = []
        density = max(0.4, 1.0 - row * 0.08)
        for col in range(cols):
            if row % 2 == 1 and col == cols - 1:
                row_list.append(None)
            elif rng.random() < density:
                row_list.append(rng.randint(0, DAILY_COLORS - 1))
            else:
                row_list.append(None)
        grid.append(row_list)

    # Pad remaining rows with None so caller can extend to full ROWS
    TOTAL_ROWS = 14   # matches ROWS in macan_bubble_shooter.py
    while len(grid) < TOTAL_ROWS:
        grid.append([None] * cols)

    return grid


# ── Daily record ──────────────────────────────────────────────────────────────

class DailyRecord:
    """Holds the daily challenge result for today."""

    def __init__(self):
        self.date_str   : str  = date.today().isoformat()
        self.score      : int  = 0
        self.shots_used : int  = 0
        self.level      : int  = 1
        self.completed  : bool = False   # True if the grid was cleared
        self.time_sec   : int  = 0

    def to_dict(self) -> dict:
        return {
            "date":       self.date_str,
            "score":      self.score,
            "shots_used": self.shots_used,
            "level":      self.level,
            "completed":  self.completed,
            "time_sec":   self.time_sec,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DailyRecord":
        r = cls()
        r.date_str   = d.get("date",       date.today().isoformat())
        r.score      = d.get("score",      0)
        r.shots_used = d.get("shots_used", 0)
        r.level      = d.get("level",      1)
        r.completed  = d.get("completed",  False)
        r.time_sec   = d.get("time_sec",   0)
        return r


# ── Manager ───────────────────────────────────────────────────────────────────

class DailyChallengeManager(QObject):
    """Manages daily challenge state: grid generation, scoring, and persistence."""

    challenge_completed = Signal(int)   # emits final score when grid is cleared
    shots_remaining_changed = Signal(int)

    def __init__(self, save_dir: Path):
        super().__init__()
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self._record   : DailyRecord | None = None
        self._shots_left: int = DAILY_SHOTS_CAP
        self._active   : bool = False

        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def is_today_played(self) -> bool:
        """True if the player has already started or completed today's challenge."""
        if self._record is None:
            return False
        return self._record.date_str == date.today().isoformat()

    def is_today_completed(self) -> bool:
        if not self.is_today_played():
            return False
        return self._record.completed

    def start(self) -> list:
        """
        Start today's challenge. Returns the daily grid.
        Resets the shot counter even if already played (allow retry on same day).
        """
        self._record = DailyRecord()
        self._shots_left = DAILY_SHOTS_CAP
        self._active = True
        self.shots_remaining_changed.emit(self._shots_left)
        return generate_daily_grid()

    def on_shot_fired(self):
        if not self._active:
            return
        self._shots_left = max(0, self._shots_left - 1)
        self.shots_remaining_changed.emit(self._shots_left)

    def on_match(self, points: int):
        if self._record and self._active:
            self._record.score += points

    def on_drop(self, points: int):
        if self._record and self._active:
            self._record.score += points

    def on_complete(self, shots_used: int, time_sec: int):
        """Call when the grid is fully cleared."""
        if not self._record:
            return
        self._record.completed  = True
        self._record.shots_used = shots_used
        self._record.time_sec   = time_sec
        self._active = False
        self._save()
        self.challenge_completed.emit(self._record.score)

    def on_timeout(self, shots_used: int, time_sec: int):
        """Call when shots run out without clearing the grid."""
        if not self._record:
            return
        self._record.shots_used = shots_used
        self._record.time_sec   = time_sec
        self._active = False
        self._save()

    @property
    def shots_left(self) -> int:
        return self._shots_left

    @property
    def record(self) -> DailyRecord | None:
        return self._record

    @property
    def today_score(self) -> int:
        return self._record.score if self._record else 0

    def get_share_text(self) -> str:
        """Generate a shareable result string (no external service needed)."""
        if not self._record:
            return ""
        r = self._record
        status = "✅ Cleared!" if r.completed else f"⚠ {r.shots_used}/{DAILY_SHOTS_CAP} shots"
        mins, secs = divmod(r.time_sec, 60)
        return (
            f"🐯 Macan Bubble Shooter — Daily Challenge {r.date_str}\n"
            f"Score: {r.score:,}  |  {status}  |  Time: {mins:02d}:{secs:02d}\n"
            f"Play at: github.com/danx123/macan-bubble-shooter"
        )

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self):
        if not self._record:
            return
        try:
            path = self.save_dir / "daily.json"
            with open(path, "w") as f:
                json.dump(self._record.to_dict(), f, indent=2)
        except Exception as e:
            print(f"DailyChallenge save error: {e}")

    def _load(self):
        try:
            path = self.save_dir / "daily.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                rec = DailyRecord.from_dict(data)
                # Only keep if it's today's record
                if rec.date_str == date.today().isoformat():
                    self._record = rec
        except Exception as e:
            print(f"DailyChallenge load error: {e}")


# ── Singleton ─────────────────────────────────────────────────────────────────

_manager: DailyChallengeManager | None = None


def get_daily_manager(save_dir: Path | None = None) -> DailyChallengeManager:
    global _manager
    if _manager is None:
        if save_dir is None:
            save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6" / "saves"
        _manager = DailyChallengeManager(save_dir)
    return _manager
