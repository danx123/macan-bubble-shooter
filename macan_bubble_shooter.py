import sys
import os
import math
import random
import json
import base64
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                               QLabel, QVBoxLayout, QHBoxLayout, QGraphicsView, 
                               QGraphicsScene, QGraphicsEllipseItem, QGraphicsPolygonItem,
                               QGraphicsRectItem, QDialog, QGraphicsDropShadowEffect, QStackedWidget, QCheckBox, QFrame, QGridLayout, QGraphicsTextItem, QGraphicsLineItem)
from PySide6.QtCore import (Qt, QTimer, QPointF, QRectF, QPropertyAnimation, 
                            Signal, QObject, QEasingCurve, QVariantAnimation)
from PySide6.QtGui import (QColor, QPen, QBrush, QLinearGradient, QRadialGradient, 
                          QPainter, QPolygonF, QFont, QPainterPath, QIcon, QPalette, QPixmap)
from bubble_fx import get_sound_manager, play_shoot, play_burst, play_clear, play_combo, start_bgm
from PySide6.QtMultimedia import QMediaPlayer
from bubble_power import (get_power_manager, PowerUpType, PowerUpBubble, 
                          PowerUpVisualEffect, try_spawn_powerup, 
                          add_powerup, use_powerup, get_all_powers_info)
from bubble_gfx import get_bubble_pixmap, get_launcher_pixmap, get_background_pixmap, has_custom_graphics, get_custom_cursor

# === MODUL BARU ===
from bubble_timer import (
    ShotTimer, RushModeManager, GameTimer, TimerBar, CountdownFlash,
    get_shot_timer, get_rush_manager, get_game_timer, reset_all_timers,
    SHOT_TIME_LIMIT
)
from bubble_score import (
    ScoreManager, ScoreEvent, spawn_score_popup,
    get_score_manager, get_leaderboard
)
from bubble_achievement import (
    get_achievement_manager, show_achievement_toast, ALL_ACHIEVEMENTS
)
from bubble_ui import LeaderboardDialog, AchievementDialog, GameOverDialog

# === SPECIAL FEATURES ===
from bubble_special import (
    BossBubble, ObstacleBubble, OBSTACLE_COLOR_INDEX,
    should_spawn_boss, create_boss_bubble, obstacle_chance,
    is_colorblind_mode, set_colorblind_mode, get_cb_symbol,
    apply_colorblind_to_bubble,
    get_replay_manager, get_replay_recorder,
    ReplayPlayer,
)
from bubble_daily import get_daily_manager, DAILY_SHOTS_CAP

# --- Game Configuration ---
BUBBLE_RADIUS = 22
ROWS = 14
COLS = 20  # FIXED: Tambah kolom agar memenuhi layar (1200px)
SHOTS_PER_DROP = 7  # CONFIG: Langit-langit turun setiap 7 tembakan (kena/tidak)

# Warna Palet Premium
BUBBLE_PALETTE = [
    {"base": QColor(255, 69, 58),  "light": QColor(255, 134, 124), "dark": QColor(160, 20, 10)},   # Ruby Red
    {"base": QColor(50, 215, 75),  "light": QColor(120, 255, 140), "dark": QColor(20, 120, 40)},   # Emerald Green
    {"base": QColor(10, 132, 255), "light": QColor(100, 180, 255), "dark": QColor(0, 60, 140)},    # Sapphire Blue
    {"base": QColor(255, 214, 10), "light": QColor(255, 240, 100), "dark": QColor(180, 140, 0)},   # Topaz Yellow
    {"base": QColor(191, 90, 242), "light": QColor(220, 150, 255), "dark": QColor(100, 30, 140)},  # Amethyst Purple
    {"base": QColor(100, 210, 255), "light": QColor(180, 240, 255), "dark": QColor(0, 100, 140)}    # Diamond Cyan
]

class Particle(QGraphicsEllipseItem):
    def __init__(self, x, y, color, scene):
        size = random.uniform(4, 9)
        super().__init__(-size/2, -size/2, size, size)
        self.setPos(x, y)
        self.setBrush(QBrush(color))
        self.setPen(Qt.NoPen)
        
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
        self.life = 40
        self.max_life = 40
        self.scene_ref = scene
        scene.addItem(self)
        
    def update_particle(self):
        self.life -= 1
        if self.life <= 0:
            self.scene_ref.removeItem(self)
            return False
        
        self.setPos(self.x() + self.vx, self.y() + self.vy)
        self.vx *= 0.95
        self.vy *= 0.95
        self.vy += 0.3
        
        opacity = self.life / self.max_life
        self.setOpacity(opacity)
        self.setScale(self.scale() * 0.95)
        return True

class Bubble(QObject, QGraphicsEllipseItem):
    def __init__(self, color_index, x, y, is_preview=False):
        QObject.__init__(self)
        radius = BUBBLE_RADIUS if not is_preview else BUBBLE_RADIUS * 0.8
        QGraphicsEllipseItem.__init__(self, -radius, -radius, radius * 2, radius * 2)
        
        self.color_index = color_index
        self.radius_val = radius
        self.setPos(x, y)
        self.setup_appearance()
        self.row = 0
        self.col = 0
        self.setTransformOriginPoint(0, 0)
        self.anim = None
        
    def setup_appearance(self):
        if self.color_index == -1:
            gradient = QRadialGradient(-self.radius_val * 0.3, -self.radius_val * 0.3, self.radius_val * 1.5)
            gradient.setColorAt(0, QColor(255, 255, 255))
            gradient.setColorAt(0.2, QColor(255, 0, 0))
            gradient.setColorAt(0.4, QColor(255, 255, 0))
            gradient.setColorAt(0.6, QColor(0, 255, 0))
            gradient.setColorAt(0.8, QColor(0, 0, 255))
            gradient.setColorAt(1, QColor(255, 0, 255))
            self.setBrush(QBrush(gradient))
            self.setPen(QPen(QColor(255, 255, 255), 3))
            rainbow_text = QGraphicsTextItem("🌈", self)
            rainbow_text.setDefaultTextColor(Qt.white)
            font = QFont("Segoe UI Emoji", int(self.radius_val * 0.8), QFont.Bold)
            rainbow_text.setFont(font)
            text_rect = rainbow_text.boundingRect()
            rainbow_text.setPos(-text_rect.width()/2, -text_rect.height()/2)
            return

        if self.color_index >= len(BUBBLE_PALETTE):
            self.color_index = 0

        palette = BUBBLE_PALETTE[self.color_index]

        # Color-blind mode: swap to high-contrast color
        if is_colorblind_mode():
            from bubble_special import get_cb_color
            cb_col = get_cb_color(self.color_index)
            cb_light = cb_col.lighter(140)
            cb_dark  = cb_col.darker(140)
            gradient = QRadialGradient(-self.radius_val * 0.3, -self.radius_val * 0.3, self.radius_val * 1.5)
            gradient.setColorAt(0, cb_light)
            gradient.setColorAt(0.3, cb_col)
            gradient.setColorAt(1, cb_dark)
            self.setBrush(QBrush(gradient))
            self.setPen(QPen(cb_dark.darker(150), 1.5))
            # Overlay symbol
            from bubble_special import get_cb_symbol
            sym = get_cb_symbol(self.color_index)
            sym_label = QGraphicsTextItem(sym, self)
            sym_font  = QFont("Segoe UI", int(self.radius_val * 0.55), QFont.Bold)
            sym_label.setFont(sym_font)
            sym_label.setDefaultTextColor(QColor(255, 255, 255))
            bw = sym_label.boundingRect().width()
            bh = sym_label.boundingRect().height()
            sym_label.setPos(-bw / 2, -bh / 2)
        else:
            gradient = QRadialGradient(-self.radius_val * 0.3, -self.radius_val * 0.3, self.radius_val * 1.5)
            gradient.setColorAt(0, palette["light"])
            gradient.setColorAt(0.3, palette["base"])
            gradient.setColorAt(1, palette["dark"])
            self.setBrush(QBrush(gradient))
            self.setPen(QPen(palette["dark"].darker(150), 1.5))

    def move_to_grid_pos(self, x, y):
        if self.anim:
            self.anim.stop()
            
        self.anim = QVariantAnimation()
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPointF(x, y))
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.OutBounce)
        self.anim.valueChanged.connect(self.setPos)
        self.anim.start()

class Shooter(QGraphicsPolygonItem):
    def __init__(self):
        super().__init__()
        self.angle = 90
        self.create_paw_shape()
        
        self.loaded_bubble_item = QGraphicsEllipseItem(-BUBBLE_RADIUS + 5, -BUBBLE_RADIUS + 5, 
                                                      (BUBBLE_RADIUS * 2) - 10, (BUBBLE_RADIUS * 2) - 10, self)
        self.loaded_bubble_item.setPos(0, -10)
        self.loaded_bubble_item.setPen(Qt.NoPen)
        
        self.current_color = random.randint(0, len(BUBBLE_PALETTE) - 1)
        self.next_color = random.randint(0, len(BUBBLE_PALETTE) - 1)
        self.update_loaded_bubble_visual()
        
    def create_paw_shape(self):
        poly = QPolygonF([
            QPointF(-25, 20), QPointF(25, 20),
            QPointF(15, -40), QPointF(-15, -40)
        ])
        self.setPolygon(poly)
        
        gradient = QLinearGradient(0, 20, 0, -40)
        gradient.setColorAt(0, QColor(218, 165, 32))
        gradient.setColorAt(0.5, QColor(255, 215, 0))
        gradient.setColorAt(1, QColor(255, 223, 0)) 
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(QColor(100, 70, 0), 2))
        
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(15)
        effect.setColor(QColor(0,0,0,150))
        effect.setOffset(0, 5)
        self.setGraphicsEffect(effect)
        
    def set_angle(self, angle):
        self.angle = max(15, min(165, angle))
        self.setRotation(-self.angle + 90)

    def update_loaded_bubble_visual(self):
        if self.current_color == -1:
            gradient = QRadialGradient(-5, -5, BUBBLE_RADIUS)
            gradient.setColorAt(0, QColor(255, 255, 255))
            gradient.setColorAt(0.2, QColor(255, 0, 0))
            gradient.setColorAt(0.4, QColor(255, 255, 0))
            gradient.setColorAt(0.6, QColor(0, 255, 0))
            gradient.setColorAt(0.8, QColor(0, 0, 255))
            gradient.setColorAt(1, QColor(255, 0, 255))
            
            self.loaded_bubble_item.setBrush(QBrush(gradient))
            self.loaded_bubble_item.setPen(QPen(QColor(255, 255, 255), 2))
            return
        
        palette = BUBBLE_PALETTE[self.current_color]
        gradient = QRadialGradient(-5, -5, BUBBLE_RADIUS)
        gradient.setColorAt(0, palette["light"])
        gradient.setColorAt(1, palette["base"])
        self.loaded_bubble_item.setBrush(QBrush(gradient))

    def reload(self):
        self.current_color = self.next_color
        self.next_color = random.randint(0, len(BUBBLE_PALETTE) - 1)
        self.update_loaded_bubble_visual()

    def swap_colors(self):
        self.current_color, self.next_color = self.next_color, self.current_color
        self.update_loaded_bubble_visual()

class BubbleGrid:
    def __init__(self):
        self.grid = []
        self.grid_offset_x = 0  # Offset horizontal agar grid di tengah scene lebar
        self.initialize_grid()
        
    def initialize_grid(self):
        self.grid = []
        initial_rows = 5
        for row in range(ROWS):
            row_bubbles = []
            for col in range(COLS):
                if row < initial_rows:
                    is_indented = (row % 2 == 1)
                    if is_indented and col == COLS - 1:
                        row_bubbles.append(None)
                    else:
                        color = random.randint(0, len(BUBBLE_PALETTE) - 1)
                        row_bubbles.append(color)
                else:
                    row_bubbles.append(None)
            self.grid.append(row_bubbles)
            
    def get_position(self, row, col):
        offset = BUBBLE_RADIUS if row % 2 == 1 else 0
        x = col * BUBBLE_RADIUS * 2 + BUBBLE_RADIUS + offset + self.grid_offset_x
        y = row * BUBBLE_RADIUS * 1.732 + BUBBLE_RADIUS
        return x, y
        
    def get_neighbors(self, row, col):
        neighbors = []
        if row % 2 == 0:
             directions = [(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]
        else:
            directions = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]
            
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if 0 <= nr < len(self.grid) and 0 <= nc < len(self.grid[nr]):
                if self.grid[nr][nc] is not None:
                    neighbors.append((nr, nc))
        return neighbors

class DangerZoneOverlay:
    """
    Visual danger zone that appears when bubbles get too close to the shooter.

    Features:
    - Pulsing red horizontal line at the danger threshold
    - Increasingly intense red screen overlay as danger grows
    - "DANGER ZONE" text warning label
    - 4 levels: hidden → warning (yellow) → danger (orange) → critical (red)
    - Pulsing animation on the line and overlay
    """

    # Y-distance thresholds from shooter (pixels)
    WARN_DIST     = 220   # Level 1 — yellow line appears
    DANGER_DIST   = 150   # Level 2 — orange, overlay starts
    CRITICAL_DIST = 90    # Level 3 — red pulsing, text label

    def __init__(self, scene, scene_width: int, scene_height: int, shooter_y: float):
        self.scene = scene
        self.scene_width = scene_width
        self.shooter_y = shooter_y

        # Danger threshold Y position (shown as a horizontal line)
        self._warn_y     = shooter_y - self.WARN_DIST
        self._danger_y   = shooter_y - self.DANGER_DIST
        self._critical_y = shooter_y - self.CRITICAL_DIST

        # ── Warning line (dashed, spans full arena width) ──
        self._line = QGraphicsRectItem(0, self._danger_y, scene_width, 3)
        self._line.setBrush(QBrush(QColor(255, 160, 0, 180)))
        self._line.setPen(QPen(Qt.NoPen))
        self._line.setZValue(90)
        self._line.setVisible(False)
        scene.addItem(self._line)

        # ── Screen overlay (semi-transparent red tint) ──
        self._overlay = QGraphicsRectItem(0, 0, scene_width, scene_height)
        self._overlay.setBrush(QBrush(QColor(255, 0, 0, 0)))
        self._overlay.setPen(QPen(Qt.NoPen))
        self._overlay.setZValue(88)
        self._overlay.setVisible(False)
        scene.addItem(self._overlay)

        # ── Bottom edge highlight bar (critical only) ──
        self._edge_bar = QGraphicsRectItem(0, self._critical_y, scene_width, 6)
        self._edge_bar.setBrush(QBrush(QColor(255, 30, 30, 220)))
        self._edge_bar.setPen(QPen(Qt.NoPen))
        self._edge_bar.setZValue(91)
        self._edge_bar.setVisible(False)
        scene.addItem(self._edge_bar)

        # ── "DANGER ZONE" text ──
        self._label = QGraphicsTextItem("⚠ DANGER ZONE")
        font = QFont("Segoe UI Black", 14, QFont.Black)
        self._label.setFont(font)
        self._label.setDefaultTextColor(QColor(255, 60, 60))
        self._label.setZValue(92)
        lw = self._label.boundingRect().width()
        self._label.setPos(scene_width / 2 - lw / 2, self._critical_y - 30)
        self._label.setVisible(False)
        scene.addItem(self._label)

        # Pulse animation state
        self._pulse_frame = 0
        self._pulse_timer = QTimer()
        self._pulse_timer.setInterval(40)   # ~25fps pulse
        self._pulse_timer.timeout.connect(self._pulse)

        self._current_level = 0

    def update_danger(self, bubbles: list):
        """Call after every bubble attach. Determines danger level from lowest bubble."""
        if not bubbles:
            self._set_level(0)
            return

        lowest_y = max(b.y() for b in bubbles)
        dist = self.shooter_y - lowest_y

        if dist <= self.CRITICAL_DIST:
            self._set_level(3)
        elif dist <= self.DANGER_DIST:
            self._set_level(2)
        elif dist <= self.WARN_DIST:
            self._set_level(1)
        else:
            self._set_level(0)

    def _set_level(self, level: int):
        if level == self._current_level:
            return
        self._current_level = level

        if level == 0:
            self._line.setVisible(False)
            self._overlay.setVisible(False)
            self._edge_bar.setVisible(False)
            self._label.setVisible(False)
            self._pulse_timer.stop()

        elif level == 1:
            # Warning — yellow/amber line only
            self._line.setPos(0, self._warn_y)
            self._line.setRect(0, 0, self.scene_width, 2)
            self._line.setBrush(QBrush(QColor(255, 200, 0, 160)))
            self._line.setVisible(True)
            self._overlay.setVisible(False)
            self._edge_bar.setVisible(False)
            self._label.setVisible(False)
            self._pulse_timer.start()

        elif level == 2:
            # Danger — orange line + faint overlay
            self._line.setPos(0, self._danger_y)
            self._line.setRect(0, 0, self.scene_width, 3)
            self._line.setBrush(QBrush(QColor(255, 120, 0, 200)))
            self._line.setVisible(True)
            self._overlay.setRect(0, 0, self.scene_width, self.shooter_y)
            self._overlay.setVisible(True)
            self._edge_bar.setVisible(False)
            self._label.setVisible(False)
            self._pulse_timer.start()

        elif level == 3:
            # Critical — red pulsing line + overlay + edge bar + text
            self._line.setPos(0, self._critical_y)
            self._line.setRect(0, 0, self.scene_width, 5)
            self._line.setBrush(QBrush(QColor(255, 40, 40, 230)))
            self._line.setVisible(True)
            self._overlay.setRect(0, 0, self.scene_width, self.shooter_y)
            self._overlay.setVisible(True)
            self._edge_bar.setVisible(True)
            self._label.setVisible(True)
            self._pulse_timer.start()

    def _pulse(self):
        """Animate pulsing opacity on all danger elements."""
        self._pulse_frame += 1
        t = self._pulse_frame * 0.12
        # sin oscillation 0..1
        import math
        pulse = (math.sin(t) + 1.0) / 2.0   # 0.0 .. 1.0

        level = self._current_level
        if level >= 1:
            line_alpha = int(80 + pulse * 160)
            if level == 1:
                self._line.setBrush(QBrush(QColor(255, 200, 0, line_alpha)))
            elif level == 2:
                self._line.setBrush(QBrush(QColor(255, 120, 0, line_alpha)))
                ov_alpha = int(pulse * 28)
                self._overlay.setBrush(QBrush(QColor(255, 80, 0, ov_alpha)))
            elif level == 3:
                self._line.setBrush(QBrush(QColor(255, 40, 40, line_alpha)))
                ov_alpha = int(15 + pulse * 40)
                self._overlay.setBrush(QBrush(QColor(255, 0, 0, ov_alpha)))
                edge_alpha = int(120 + pulse * 120)
                self._edge_bar.setBrush(QBrush(QColor(255, 30, 30, edge_alpha)))
                # Pulse label opacity
                self._label.setOpacity(0.5 + pulse * 0.5)

    def remove(self):
        """Clean up all items from scene."""
        self._pulse_timer.stop()
        for item in [self._line, self._overlay, self._edge_bar, self._label]:
            try:
                if item.scene():
                    self.scene.removeItem(item)
            except Exception:
                pass


class GameScene(QGraphicsScene):
    score_changed = Signal(int)
    high_score_changed = Signal(int)
    drop_counter_changed = Signal(int)
    level_changed = Signal(int)
    next_bubble_changed = Signal(int)
    power_collected = Signal(str)
    power_used = Signal(str)
    power_updated = Signal()
    game_over = Signal()
    # === SINYAL BARU ===
    combo_changed    = Signal(int)    # Combo count
    timer_tick       = Signal(float)  # Sisa waktu tembak
    multiplier_changed = Signal(float) # Speed multiplier
    danger_level_changed = Signal(int) # 0-3
    playtime_changed = Signal(str)    # "mm:ss"
    achievement_earned = Signal(object)  # AchievementDef
    
    def __init__(self):
        super().__init__()
        # Hitung ukuran grid aktual terlebih dulu
        GRID_PADDING = 10
        grid_width = int(COLS * BUBBLE_RADIUS * 2 + BUBBLE_RADIUS * 2 + GRID_PADDING * 2)
        ROWS_HEIGHT = int(ROWS * BUBBLE_RADIUS * 1.732 + BUBBLE_RADIUS)
        self.scene_height = ROWS_HEIGHT + 220

        # FIX GEPENG: Perlebar scene_width ke aspect ratio 16:9 agar tidak distorsi
        # Dengan KeepAspectRatio, scene harus proporsional dengan layar widescreen
        self.scene_width = int(self.scene_height * (16 / 9))

        # Simpan offset horizontal agar grid bubble tetap di TENGAH scene yang lebih lebar
        self.grid_offset_x = (self.scene_width - grid_width) // 2

        self.setSceneRect(0, 0, self.scene_width, self.scene_height)
        
        self.score = 0
        self.high_score = 0
        self.level = 1
        self.level_threshold = 1000

        self.setup_background()
        
        self.grid = BubbleGrid()
        self.grid.grid_offset_x = self.grid_offset_x  # Sinkronkan offset ke grid
        self.bubbles = []
        self.shooter = Shooter()
        self.shooter.setPos(self.scene_width / 2, self.scene_height - 130)
        self.addItem(self.shooter)
        
        self.flying_bubble = None
        self.particles = []
        
        self.shots_until_drop = SHOTS_PER_DROP 
        
        self.shooting = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)
        
        self.create_bubbles_visuals()    

        self.power_manager = get_power_manager()
        self.active_power = None
        self.freeze_shots_remaining = 0
        
        # === AIM LINE (Garis Aim) ===
        self.aim_line = None
        self.aim_bounce_line = None

        # === SISTEM BARU: Timer, Score, Achievement ===
        self._save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6" / "saves"
        self._save_dir.mkdir(parents=True, exist_ok=True)

        # Score Manager
        self.score_mgr = get_score_manager(self._save_dir)
        self.score_mgr.score_updated.connect(self._on_score_updated)
        self.score_mgr.combo_updated.connect(self.combo_changed.emit)
        self.score_mgr.score_event.connect(self._on_score_event)
        self.score_mgr.highscore_beaten.connect(self._on_highscore_beaten)

        # Shot Timer
        self.shot_timer = get_shot_timer()
        self.shot_timer.tick.connect(self.timer_tick.emit)
        self.shot_timer.tick.connect(self._update_timer_bar)
        self.shot_timer.multiplier_changed.connect(self.multiplier_changed.emit)
        self.shot_timer.time_up.connect(self._on_shot_time_up)

        # Rush Mode Manager
        self.rush_mgr = get_rush_manager()
        self.rush_mgr.danger_level_changed.connect(self._on_danger_level_changed)
        self.rush_mgr.rush_started.connect(self._on_rush_started)
        self.rush_mgr.rush_ended.connect(self._on_rush_ended)

        # Game Timer (total waktu bermain)
        self.game_timer = get_game_timer()
        self.game_timer.elapsed_changed.connect(self._on_elapsed_tick)

        # Achievement Manager
        self.ach_mgr = get_achievement_manager(self._save_dir)
        self.ach_mgr.achievement_unlocked.connect(self._on_achievement_unlocked)

        # Timer Bar visual di scene (di bawah shooter)
        timer_bar_y = self.scene_height - 175
        timer_bar_x = self.grid_offset_x
        timer_bar_w = COLS * BUBBLE_RADIUS * 2 + BUBBLE_RADIUS * 2
        self.timer_bar = TimerBar(self, timer_bar_x, timer_bar_y, timer_bar_w, 12)

        # Countdown flash
        self.countdown_flash = CountdownFlash(self, self.scene_width, self.scene_height)

        # === DANGER ZONE SYSTEM ===
        self._danger_zone = DangerZoneOverlay(self, self.scene_width, self.scene_height, self.shooter.y())
        self._last_danger_level = 0

        # === BOSS / OBSTACLE TRACKING ===
        self.boss_bubbles: list = []      # BossBubble items in scene
        self.obstacle_bubbles: list = []  # ObstacleBubble items in scene

        # === REPLAY RECORDER ===
        self.recorder = get_replay_recorder()
        self.recorder.start()

        # === DAILY CHALLENGE ===
        self.daily_mode   = False
        self.daily_shots  = 0

        # Tracking state
        self._no_miss_streak    = 0
        self._speed_shot_streak = 0
        self._last_shot_bounced = False
        self._chain_count       = 0
        self._was_in_rush       = False
        self._current_shot_multiplier = 1.0

        # Mulai shot timer untuk tembakan pertama
        self.shot_timer.start(rush_mode=False)
        self.game_timer.start()
    
    def setup_background(self):
        # 1. Hapus background lama jika ada (untuk reset)
        if hasattr(self, 'bg_item') and self.bg_item:
            self.removeItem(self.bg_item)
            self.bg_item = None

        # 2. Tentukan Path Gambar Wallpaper
        bg_path = Path(__file__).parent / "ui" / "bubble_scn.webp"
        final_pixmap = None

        # 3. Coba Load Gambar Wallpaper
        if bg_path.exists():
            original_pixmap = QPixmap(str(bg_path))
            if not original_pixmap.isNull():
                # Scale gambar agar memenuhi seluruh Scene (1200x800)
                # Menggunakan IgnoreAspectRatio agar gambar ditarik penuh (stretch)
                final_pixmap = original_pixmap.scaled(
                    self.scene_width, 
                    self.scene_height,
                    Qt.IgnoreAspectRatio, 
                    Qt.SmoothTransformation
                )

        # 4. Fallback: Jika gambar tidak ada, pakai Generator Nebula (lama)
        if not final_pixmap:
            final_pixmap = get_background_pixmap(self.scene_width, self.scene_height)

        # 5. Tambahkan ke Scene
        if final_pixmap:
            self.bg_item = self.addPixmap(final_pixmap)
            self.bg_item.setZValue(-100) # Layer paling belakang
            self.bg_item.setPos(0, 0)
        else:
            # Fallback terakhir (Layar Hitam) jika semua gagal
            self.bg_item = QGraphicsRectItem(0, 0, self.scene_width, self.scene_height)
            self.bg_item.setBrush(QBrush(Qt.black))
            self.bg_item.setZValue(-100)
            self.addItem(self.bg_item)

        # 6. Overlay Layer (Tetap dipertahankan untuk efek Level Tint)        
        if hasattr(self, 'bg_overlay') and self.bg_overlay:
            self.removeItem(self.bg_overlay)
            
        self.bg_overlay = QGraphicsRectItem(0, 0, self.scene_width, self.scene_height)
        self.bg_overlay.setPen(Qt.NoPen)
        self.bg_overlay.setZValue(-99) # Di atas wallpaper, di bawah bubble
        self.addItem(self.bg_overlay)
        
        # Terapkan warna awal
        self.update_background_color()
    
    def update_background_color(self):
        # Format: (R, G, B, Alpha) 
        # Alpha 100 sebelumnya cukup pekat. Ubah ke 60-80 agar wallpaper lebih terlihat.
        tints = [
            QColor(0, 0, 0, 0),       # Level 1: Original (Jernih)
            QColor(50, 0, 20, 60),    # Level 2: Sedikit Merah
            QColor(0, 40, 60, 60),    # Level 3: Sedikit Biru
            QColor(40, 0, 60, 60),    # Level 4: Sedikit Ungu
            QColor(60, 40, 0, 60),    # Level 5: Sedikit Emas
            QColor(0, 60, 20, 60)     # Level 6: Sedikit Hijau
        ]      
                
        # Ambil warna berdasarkan level (looping jika level > 6)
        tint_color = tints[(self.level - 1) % len(tints)]
        self.bg_overlay.setBrush(QBrush(tint_color))

        # Pastikan border tetap mati saat update warna
        self.bg_overlay.setPen(Qt.NoPen)
        self.bg_overlay.setBrush(QBrush(tint_color))
            
    def create_bubbles_visuals(self):
        for bubble in self.bubbles:
            self.removeItem(bubble)
        self.bubbles.clear()
        
        for row in range(len(self.grid.grid)):
            for col in range(len(self.grid.grid[row])):
                if self.grid.grid[row][col] is not None:
                    x, y = self.grid.get_position(row, col)
                    bubble = Bubble(self.grid.grid[row][col], x, y)
                    bubble.row = row
                    bubble.col = col
                    self.bubbles.append(bubble)
                    self.addItem(bubble)

    def shoot_bubble(self, angle):
        if self.shooting or self.flying_bubble:
            return        
        play_shoot()

        # === Ambil multiplier dari shot timer sebelum di-stop ===
        self._current_shot_multiplier = self.shot_timer.get_multiplier()
        self._last_shot_bounced = False
        self.shot_timer.stop()

        # Update achievement tracking
        self.score_mgr.on_shot_fired()
        self.ach_mgr.on_shots(self.score_mgr.total_shots, self._no_miss_streak)

        # === REPLAY: record shot ===
        self.recorder.record_shot(angle, self.shooter.current_color)

        # === DAILY: count shots ===
        if self.daily_mode:
            self.daily_shots += 1
            get_daily_manager().on_shot_fired()
            
        self.shooting = True
        color = self.shooter.current_color
        
        rad = math.radians(angle)
        start_dist = 40
        start_x = self.shooter.x() + math.cos(rad) * start_dist
        start_y = self.shooter.y() - math.sin(rad) * start_dist
        
        self.flying_bubble = Bubble(color, start_x, start_y)
        self.addItem(self.flying_bubble)
        
        speed = 20
        self.bubble_vx = math.cos(rad) * speed
        self.bubble_vy = -math.sin(rad) * speed
        
        self.shooter.reload()
        self.next_bubble_changed.emit(self.shooter.next_color)
        
        # Hapus aim line saat menembak
        self.clear_aim_line()

    def swap_shooter_bubble(self):
        if not self.shooting and not self.flying_bubble:
            self.shooter.swap_colors()
            self.next_bubble_changed.emit(self.shooter.next_color)
        
    def update_game(self):
        # 1. Update semua partikel yang ada (hapus jika sudah mati)
        self.particles = [p for p in self.particles if p.update_particle()]
        
        # 2. Logika Bubble Terbang
        if self.flying_bubble:
            # === START: EFEK METEOR (TRAIL) ===
            # Membuat partikel jejak di setiap frame
            # Warna putih transparan (seperti asap/ekor komet)
            trail_color = QColor(255, 255, 255, 150) 
            
            # Spawn partikel di posisi bubble saat ini
            p = Particle(self.flying_bubble.x(), self.flying_bubble.y(), trail_color, self)
            
            # Kustomisasi partikel agar terlihat seperti jejak
            p.setZValue(self.flying_bubble.zValue() - 1)  # Render di belakang bubble
            p.setScale(0.5)        # Ukuran lebih kecil dari ledakan biasa
            p.life = 10            # Umur sangat pendek (cepat hilang)
            p.max_life = 10
            
            # Gerakan acak sangat kecil agar terlihat seperti asap buangan
            p.vx = random.uniform(-1.5, 1.5)
            p.vy = random.uniform(-1.5, 1.5)
            
            self.particles.append(p)
            # === END: EFEK METEOR ===

            # 3. Hitung posisi baru
            new_x = self.flying_bubble.x() + self.bubble_vx
            new_y = self.flying_bubble.y() + self.bubble_vy
            
            # 4. Pantulan Dinding (Wall Bounce) - dalam area grid, bukan seluruh scene
            wall_left  = self.grid_offset_x + BUBBLE_RADIUS
            wall_right = self.grid_offset_x + (COLS * BUBBLE_RADIUS * 2 + BUBBLE_RADIUS * 2) - BUBBLE_RADIUS
            if new_x <= wall_left:
                overflow = wall_left - new_x
                new_x = wall_left + overflow
                self.bubble_vx = abs(self.bubble_vx)
                self._last_shot_bounced = True   # Track pantulan
            elif new_x >= wall_right:
                overflow = new_x - wall_right
                new_x = wall_right - overflow
                self.bubble_vx = -abs(self.bubble_vx)
                self._last_shot_bounced = True   # Track pantulan
                
            self.flying_bubble.setPos(new_x, new_y)
            
            # 5. Cek Tabrakan dengan Langit-langit (Ceiling)
            if new_y - BUBBLE_RADIUS < 0:
                self.attach_bubble()
                return

            # 6. Cek Tabrakan dengan Bubble Lain
            for bubble in self.bubbles:
                # Optimasi: Cek selisih Y dulu biar cepat
                if abs(bubble.y() - new_y) < BUBBLE_RADIUS * 2.5:
                    dx = new_x - bubble.x()
                    dy = new_y - bubble.y()
                    dist_sq = dx*dx + dy*dy
                    # Jarak toleransi tabrakan (1.8 * radius)
                    if dist_sq < (BUBBLE_RADIUS * 1.8) ** 2:
                        self.attach_bubble()
                        return

            # 6b. Cek Tabrakan dengan Boss Bubbles
            for boss in self.boss_bubbles[:]:
                boss_r = boss.radius_val + BUBBLE_RADIUS
                dx = new_x - boss.x()
                dy = new_y - boss.y()
                if dx*dx + dy*dy < boss_r * boss_r:
                    # Hit boss
                    still_alive = boss.take_hit()
                    if not still_alive:
                        self._on_boss_destroyed(boss)
                    # Flying bubble is consumed
                    self.removeItem(self.flying_bubble)
                    self.flying_bubble = None
                    self.shooting = False
                    self.shot_timer.start(rush_mode=self.rush_mgr.rush_active)
                    return
                
    def attach_bubble(self):
        if not self.flying_bubble:
            return
            
        min_dist = float('inf')
        best_row, best_col = 0, 0
        curr_x = self.flying_bubble.x()
        curr_y = self.flying_bubble.y()
        
        for row in range(len(self.grid.grid)):
            for col in range(len(self.grid.grid[row])):
                if self.grid.grid[row][col] is None:
                    gx, gy = self.grid.get_position(row, col)
                    dx = curr_x - gx
                    dy = curr_y - gy
                    dist = dx*dx + dy*dy
                    if dist < min_dist:
                        min_dist = dist
                        best_row, best_col = row, col
        
        if self.grid.grid[best_row][best_col] is not None:
             return 

        self.grid.grid[best_row][best_col] = self.flying_bubble.color_index
        self.removeItem(self.flying_bubble)
        
        x, y = self.grid.get_position(best_row, best_col)
        new_bubble = Bubble(self.flying_bubble.color_index, x, y)
        new_bubble.row = best_row
        new_bubble.col = best_col
        self.bubbles.append(new_bubble)
        self.addItem(new_bubble)
        
        self.flying_bubble = None

        if self.grid.grid[best_row][best_col] == -1:
            neighbors = self.grid.get_neighbors(best_row, best_col)
            color_counts = {}
            
            for nr, nc in neighbors:
                neighbor_color = self.grid.grid[nr][nc]
                if neighbor_color is not None and neighbor_color != -1:
                    color_counts[neighbor_color] = color_counts.get(neighbor_color, 0) + 1
            
            if color_counts:
                most_common_color = max(color_counts, key=color_counts.get)
                self.grid.grid[best_row][best_col] = most_common_color
                
                for bubble in self.bubbles:
                    if bubble.row == best_row and bubble.col == best_col:
                        bubble.color_index = most_common_color
                        bubble.setup_appearance()
                        break

        if self.active_power == PowerUpType.BOMB:
            self.apply_bomb_effect(best_row, best_col)
            self.active_power = None
        
        elif self.active_power == PowerUpType.LASER:
            self.apply_laser_effect(best_col)
            self.active_power = None
        
        elif self.active_power == PowerUpType.FIREBALL:
            self.apply_fireball_effect(best_row, best_col)
            self.active_power = None
    
        else:
            match_found = self.check_matches(best_row, best_col)
            if not match_found:
                self.check_and_drop_neighbors(best_row, best_col)
    
        self.power_manager.update_all_cooldowns()
        self.power_updated.emit()
    
        if self.freeze_shots_remaining > 0:
            self.freeze_shots_remaining -= 1
        else:
            self.shots_until_drop -= 1
            self.drop_counter_changed.emit(self.shots_until_drop)
            
            if self.shots_until_drop <= 0:
                QTimer.singleShot(100, self.add_ceiling_row)
                self.shots_until_drop = SHOTS_PER_DROP
                self.drop_counter_changed.emit(self.shots_until_drop)       
        
        match_found = self.check_matches(best_row, best_col)
        
        if not match_found:
            self.check_and_drop_neighbors(best_row, best_col)
        
        if self.shots_until_drop <= 0:
            QTimer.singleShot(100, self.add_ceiling_row)
            self.shots_until_drop = SHOTS_PER_DROP
            self.drop_counter_changed.emit(self.shots_until_drop)

        if self.check_game_over_condition():
            self.game_over.emit()

        self.shooting = False

        # === Restart shot timer untuk tembakan berikutnya ===
        rush_mode = self.rush_mgr.rush_active
        self.shot_timer.start(rush_mode=rush_mode)

        # === Evaluasi rush mode ===
        self.rush_mgr.evaluate(self.bubbles, self.scene_height, self.shooter.y())

        # === Update Danger Zone visual ===
        self._danger_zone.update_danger(self.bubbles)
        # Sync HUD danger label with DangerZone level
        self.danger_level_changed.emit(self._danger_zone._current_level)

    def apply_bomb_effect(self, center_row, center_col):
        destroyed = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = center_row + dr, center_col + dc
                if 0 <= r < len(self.grid.grid) and 0 <= c < len(self.grid.grid[r]):
                    if self.grid.grid[r][c] is not None:
                        destroyed.append((r, c))
                        self.grid.grid[r][c] = None
                        self.remove_bubble_visual(r, c)

        x, y = self.grid.get_position(center_row, center_col)
        PowerUpVisualEffect.create_explosion_effect(self, x, y, BUBBLE_RADIUS * 3, QColor(255, 69, 0))
        popup_x = self.grid_offset_x + (COLS * BUBBLE_RADIUS * 2) / 2
        popup_y = self.scene_height * 0.4
        self.score_mgr.on_powerup_effect(len(destroyed), 15, popup_x, popup_y, "💣 BOMB!")
        self.ach_mgr.on_power_used('bomb')
        play_burst()
        self.remove_floating_bubbles()

    def apply_laser_effect(self, col):
        destroyed = []
        for row in range(len(self.grid.grid)):
            if col < len(self.grid.grid[row]) and self.grid.grid[row][col] is not None:
                destroyed.append((row, col))
                self.grid.grid[row][col] = None
                self.remove_bubble_visual(row, col)

        x, _ = self.grid.get_position(0, col)
        PowerUpVisualEffect.create_laser_effect(self, x, 0, self.scene_height - 200, QColor(0, 255, 255))
        popup_x = self.grid_offset_x + (COLS * BUBBLE_RADIUS * 2) / 2
        popup_y = self.scene_height * 0.4
        self.score_mgr.on_powerup_effect(len(destroyed), 20, popup_x, popup_y, "⚡ LASER!")
        self.ach_mgr.on_power_used('laser')
        play_clear()
        self.remove_floating_bubbles()

    def apply_fireball_effect(self, center_row, center_col):
        destroyed = []
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                r, c = center_row + dr, center_col + dc
                if 0 <= r < len(self.grid.grid) and 0 <= c < len(self.grid.grid[r]):
                    if self.grid.grid[r][c] is not None:
                        destroyed.append((r, c))
                        self.grid.grid[r][c] = None
                        self.remove_bubble_visual(r, c)

        x, y = self.grid.get_position(center_row, center_col)
        PowerUpVisualEffect.create_explosion_effect(self, x, y, BUBBLE_RADIUS * 5, QColor(255, 140, 0))
        popup_x = self.grid_offset_x + (COLS * BUBBLE_RADIUS * 2) / 2
        popup_y = self.scene_height * 0.4
        self.score_mgr.on_powerup_effect(len(destroyed), 25, popup_x, popup_y, "🔥 FIREBALL!")
        self.ach_mgr.on_power_used('fireball')
        play_combo()
        self.remove_floating_bubbles()

    def add_score(self, points):
        """Legacy helper — tambah skor via score_mgr agar konsisten."""
        # Pakai ScoreManager sebagai single source of truth
        if points > 0:
            evt = ScoreEvent(points, 1.0, 1, "", 0, 0, QColor(180, 255, 180))
            self.score_mgr._add_score(points)
        # Sync score lama agar backward-compatible
        self.score = self.score_mgr.score
        if self.score > self.high_score:
            self.high_score = self.score
            self.high_score_changed.emit(self.high_score)
        self.score_changed.emit(self.score)

    def _on_score_updated(self, new_score: int):
        """Callback dari ScoreManager saat score berubah."""
        self.score = new_score
        if new_score > self.high_score:
            self.high_score = new_score
            self.high_score_changed.emit(self.high_score)
        self.score_changed.emit(new_score)

    def _on_highscore_beaten(self, val: int):
        self.high_score = val
        self.high_score_changed.emit(val)

    def _on_score_event(self, event):
        """Tampilkan popup skor di scene."""
        spawn_score_popup(self, event)

    def _update_timer_bar(self, remaining: float):
        """Update visual timer bar."""
        if hasattr(self, 'timer_bar'):
            progress = self.shot_timer.get_progress()
            mult = self.shot_timer.get_multiplier()
            self.timer_bar.update(progress, mult)
            # Flash saat waktu < 2 detik
            if remaining <= 2.0 and remaining > 1.9:
                self.countdown_flash.flash("2", QColor(255, 200, 50))
            elif remaining <= 1.0 and remaining > 0.9:
                self.countdown_flash.flash("1", QColor(255, 80, 80))

    def _on_shot_time_up(self):
        """Penalti saat waktu tembak habis."""
        # Kurangi score sebagai penalti kecil
        penalty = 50
        self.score_mgr._add_score(-penalty)
        self.countdown_flash.flash("SLOW!", QColor(255, 60, 60))

    def _on_danger_level_changed(self, level: int):
        self.danger_level_changed.emit(level)
        # Sync danger zone overlay with rush manager level
        # (DangerZoneOverlay has its own evaluation, this keeps HUD in sync)

    def _on_rush_started(self):
        self._was_in_rush = True
        self.countdown_flash.flash("RUSH!", QColor(255, 80, 0))

    def _on_rush_ended(self):
        if self._was_in_rush:
            self.ach_mgr.on_rush_survived()
            self._was_in_rush = False

    def _on_elapsed_tick(self, seconds: int):
        self.playtime_changed.emit(self.game_timer.format())
        self.ach_mgr.on_survive_time(seconds)

    def _on_achievement_unlocked(self, ach_def):
        """Show toast dan emit signal ke MainWindow."""
        show_achievement_toast(self, ach_def, self.scene_width)
        # Tambah reward score
        if ach_def.reward_score > 0:
            self.score_mgr._add_score(ach_def.reward_score)
        self.achievement_earned.emit(ach_def)

    def _on_boss_destroyed(self, boss):
        """Called when a boss bubble's HP reaches 0."""
        # Award score
        bonus = 200 + boss.max_hp * 50
        popup_x = boss.x()
        popup_y = boss.y()
        self.score_mgr.on_powerup_effect(1, bonus, popup_x, popup_y, "👑 BOSS!")
        play_combo()
        self.create_explosion(boss.x(), boss.y(), QColor(255, 215, 0))
        # Remove from scene and lists
        boss.cleanup()
        self.removeItem(boss)
        if boss in self.boss_bubbles:
            self.boss_bubbles.remove(boss)
        # Also remove from grid if tracked
        for row in range(len(self.grid.grid)):
            for col in range(len(self.grid.grid[row])):
                if self.grid.grid[row][col] == -3:   # boss sentinel
                    gx, gy = self.grid.get_position(row, col)
                    if abs(gx - boss.x()) < 5 and abs(gy - boss.y()) < 5:
                        self.grid.grid[row][col] = None

    def try_spawn_boss_after_match(self, match_size: int, x: float, y: float):
        """Possibly spawn a boss bubble near the match site after a big match."""
        if should_spawn_boss(self.level, match_size):
            color = random.randint(0, len(BUBBLE_PALETTE) - 1)
            boss  = create_boss_bubble(color, x + random.randint(-40, 40),
                                       max(BUBBLE_RADIUS * 2, y - BUBBLE_RADIUS * 3),
                                       self.level)
            boss.destroyed.connect(lambda b: self._on_boss_destroyed(b))
            self.addItem(boss)
            self.boss_bubbles.append(boss)

    def check_matches(self, row, col):
        color = self.grid.grid[row][col]
        matched = set()
        self.find_matching(row, col, color, matched)

        if len(matched) >= 3:
            play_clear()
            if len(matched) >= 6:
                play_combo()

            power_type = try_spawn_powerup(len(matched))
            if power_type:
                add_powerup(power_type)
                self.power_collected.emit(power_type)

            # === Scoring via ScoreManager (baru) ===
            mx, my = self.grid.get_position(row, col)
            mult = getattr(self, '_current_shot_multiplier', 1.0)
            bounced = getattr(self, '_last_shot_bounced', False)
            rush_bonus = self.rush_mgr.get_score_bonus()

            self.score_mgr.on_match(
                match_size=len(matched),
                time_multiplier=mult,
                was_bounced=bounced,
                x=mx, y=my,
                rush_bonus=rush_bonus,
            )

            # Achievement tracking
            self._no_miss_streak += 1
            if mult >= 2.8:
                self._speed_shot_streak += 1
                self.ach_mgr.on_speed_shot(self._speed_shot_streak, mult)
            else:
                self._speed_shot_streak = 0

            self.ach_mgr.on_pop(self.score_mgr.total_pops, len(matched))
            self.ach_mgr.on_combo(self.score_mgr.combo)
            self.ach_mgr.on_streak(self.score_mgr.streak)
            self.ach_mgr.on_score(self.score_mgr.score)

            # === REPLAY: record match ===
            self.recorder.record_match(len(matched), self.score_mgr.score)

            # === DAILY: record points ===
            if self.daily_mode:
                get_daily_manager().on_match(self.score_mgr.score)

            # === BOSS SPAWN: chance after big matches ===
            self.try_spawn_boss_after_match(len(matched), mx, my)

            for r, c in matched:
                self.grid.grid[r][c] = None
                self.remove_bubble_visual(r, c)

            self.remove_floating_bubbles()
            self.check_level_up()
            return True

        # No match — reset no-miss streak
        self._no_miss_streak = 0
        return False

    def remove_bubble_visual(self, r, c):
        for bubble in self.bubbles[:]:
            if bubble.row == r and bubble.col == c:
                color = BUBBLE_PALETTE[bubble.color_index]["base"]
                self.create_explosion(bubble.x(), bubble.y(), color)
                play_burst()
                self.bubbles.remove(bubble)
                self.removeItem(bubble)
                break

    def add_ceiling_row(self):
        if any(c is not None for c in self.grid.grid[ROWS-1]):
            self.game_over.emit()
            return

        self.grid.grid.pop() 
        new_row = []
        for col in range(COLS):
            if col < COLS: 
                new_row.append(random.randint(0, len(BUBBLE_PALETTE) - 1))
            else:
                new_row.append(None)
        self.grid.grid.insert(0, new_row)

        for bubble in self.bubbles:
            bubble.row += 1
            new_x, new_y = self.grid.get_position(bubble.row, bubble.col)
            bubble.move_to_grid_pos(new_x, new_y)
            
        for col in range(len(new_row)):
            if new_row[col] is not None:
                x, y = self.grid.get_position(0, col)
                bubble = Bubble(new_row[col], x, y)
                bubble.row = 0
                bubble.col = col
                bubble.setPos(x, y - BUBBLE_RADIUS*2)
                bubble.move_to_grid_pos(x, y)
                self.bubbles.append(bubble)
                self.addItem(bubble)

    def check_level_up(self):
        if self.score_mgr.score >= self.level_threshold * self.level:
            self.level += 1
            self.score_mgr.set_level(self.level)
            self.level_changed.emit(self.level)
            self.ach_mgr.on_level(self.level)
            self.update_background_color()

    def find_matching(self, row, col, color, matched):
        if (row, col) in matched: 
            return
        
        cell_color = self.grid.grid[row][col]
        
        if cell_color is None:
            return
        
        if cell_color == color or cell_color == -1 or color == -1:
            matched.add((row, col))
            
            search_color = color if color != -1 else cell_color
            for nr, nc in self.grid.get_neighbors(row, col):
                self.find_matching(nr, nc, search_color, matched)
            
    def remove_floating_bubbles(self):
        connected = set()
        for col in range(len(self.grid.grid[0])):
            if self.grid.grid[0][col] is not None:
                self.find_connected(0, col, connected)

        dropped_count = 0
        # Posisi popup di tengah horizontal arena, sepertiga atas scene
        popup_x = self.grid_offset_x + (COLS * BUBBLE_RADIUS * 2) / 2
        popup_y = self.scene_height * 0.35

        for row in range(len(self.grid.grid)):
            for col in range(len(self.grid.grid[row])):
                if self.grid.grid[row][col] is not None and (row, col) not in connected:
                    self.grid.grid[row][col] = None
                    self.remove_bubble_visual(row, col)
                    dropped_count += 1

        if dropped_count > 0:
            self.score_mgr.on_drops(dropped_count, popup_x, popup_y)
            self.ach_mgr.on_drop(self.score_mgr._total_drops)

        if dropped_count >= 3:
            play_combo()
            self._chain_count += 1
            self.ach_mgr.on_chain_reaction(self._chain_count)
        else:
            self._chain_count = 0

        self.score_changed.emit(self.score_mgr.score)
    
    def check_and_drop_neighbors(self, impact_row, impact_col):
        neighbors = self.grid.get_neighbors(impact_row, impact_col)
        total_dropped = 0
        last_x, last_y = self.grid.get_position(impact_row, impact_col)

        for nr, nc in neighbors:
            if self.grid.grid[nr][nc] is not None:
                connected = set()
                for col in range(len(self.grid.grid[0])):
                    if self.grid.grid[0][col] is not None:
                        self.find_connected(0, col, connected)

                if (nr, nc) not in connected:
                    to_drop = set()
                    self.find_connected_cluster(nr, nc, to_drop)

                    for dr, dc in to_drop:
                        if self.grid.grid[dr][dc] is not None:
                            gx, gy = self.grid.get_position(dr, dc)
                            last_x, last_y = gx, gy
                            self.grid.grid[dr][dc] = None
                            self.remove_bubble_visual(dr, dc)
                            total_dropped += 1

        # Satu popup drop di akhir, bukan per-bubble
        if total_dropped > 0:
            self.score_mgr.on_drops(total_dropped, last_x, last_y)
            self.ach_mgr.on_drop(self.score_mgr._total_drops)
            if total_dropped >= 3:
                play_combo()
            self.score_changed.emit(self.score_mgr.score)
    
    def find_connected_cluster(self, row, col, cluster):
        if (row, col) in cluster:
            return
        if self.grid.grid[row][col] is None:
            return
        
        cluster.add((row, col))
        
        for nr, nc in self.grid.get_neighbors(row, col):
            self.find_connected_cluster(nr, nc, cluster)
                    
    def find_connected(self, row, col, connected):
        if (row, col) in connected: return
        if self.grid.grid[row][col] is None: return
        connected.add((row, col))
        for nr, nc in self.grid.get_neighbors(row, col):
            self.find_connected(nr, nc, connected)
            
    def create_explosion(self, x, y, color):
        for _ in range(8): 
            particle = Particle(x, y, color, self)
            self.particles.append(particle)

    def activate_power(self, power_type):
        if not use_powerup(power_type):
            return False

        self.active_power = power_type
        self.power_used.emit(power_type)

        if power_type == PowerUpType.FREEZE:
            self.freeze_shots_remaining = 5
            PowerUpVisualEffect.create_freeze_effect(self, self.sceneRect())
            self.ach_mgr.on_power_used('freeze')
            play_combo()

        elif power_type == PowerUpType.RAINBOW:
            self.shooter.current_color = -1
            self.shooter.update_loaded_bubble_visual()
            self.active_power = None
            self.ach_mgr.on_power_used('rainbow')
            play_combo()

        return True
            
    def check_game_over_condition(self):
        limit_y = self.shooter.y() - 50
        for bubble in self.bubbles:
            if bubble.y() > limit_y:
                return True
        return False
        
    def reset_game(self):
        self.grid.initialize_grid()
        self.grid.grid_offset_x = self.grid_offset_x
        self.create_bubbles_visuals()
        self.score = 0
        self.shots_until_drop = SHOTS_PER_DROP
        self.level = 1
        self.shooting = False
        self.flying_bubble = None
        self.shooter.current_color = random.randint(0, len(BUBBLE_PALETTE) - 1)
        self.shooter.next_color = random.randint(0, len(BUBBLE_PALETTE) - 1)
        self.shooter.update_loaded_bubble_visual()
        self.next_bubble_changed.emit(self.shooter.next_color)
        self.score_changed.emit(self.score)
        self.drop_counter_changed.emit(self.shots_until_drop)
        self.level_changed.emit(self.level)
        self.update_background_color()
        self.clear_aim_line()

        # === Reset semua sistem baru ===
        self.score_mgr.reset()
        reset_all_timers()
        # Re-bind setelah reset singleton
        self.shot_timer = get_shot_timer()
        self.shot_timer.tick.connect(self.timer_tick.emit)
        self.shot_timer.tick.connect(self._update_timer_bar)
        self.shot_timer.multiplier_changed.connect(self.multiplier_changed.emit)
        self.shot_timer.time_up.connect(self._on_shot_time_up)

        self.rush_mgr = get_rush_manager()
        self.rush_mgr.danger_level_changed.connect(self._on_danger_level_changed)
        self.rush_mgr.rush_started.connect(self._on_rush_started)
        self.rush_mgr.rush_ended.connect(self._on_rush_ended)

        self.game_timer = get_game_timer()
        self.game_timer.elapsed_changed.connect(self._on_elapsed_tick)
        self.game_timer.start()

        self._no_miss_streak    = 0
        self._speed_shot_streak = 0
        self._last_shot_bounced = False
        self._chain_count       = 0
        self._was_in_rush       = False
        self._current_shot_multiplier = 1.0

        self.shot_timer.start(rush_mode=False)

        # === Reset Danger Zone ===
        self._danger_zone.update_danger([])   # clears all danger visuals

        # === Reset Boss / Obstacle lists ===
        for boss in self.boss_bubbles:
            boss.cleanup()
            try: self.removeItem(boss)
            except: pass
        self.boss_bubbles.clear()
        self.obstacle_bubbles.clear()

        # === Reset Replay Recorder ===
        self.recorder.start()

        # === Reset Daily state ===
        self.daily_mode  = False
        self.daily_shots = 0
    def update_aim_line(self, angle):
        """Update garis aim dengan pantulan - presisi di kedua dinding"""
        self.clear_aim_line()
        
        if self.shooting or self.flying_bubble:
            return
        
        rad = math.radians(angle)
        start_dist = 40
        start_x = self.shooter.x() + math.cos(rad) * start_dist
        start_y = self.shooter.y() - math.sin(rad) * start_dist
        
        dx = math.cos(rad)
        dy = -math.sin(rad)
        
        max_distance = 1200
        step = 8  # Langkah lebih besar untuk performa lebih baik
        
        points = [(start_x, start_y)]
        current_x, current_y = start_x, start_y
        current_dx, current_dy = dx, dy
        
        for _ in range(int(max_distance / step)):
            next_x = current_x + current_dx * step
            next_y = current_y + current_dy * step
            
            # Bounce dalam batas grid (simetris kiri-kanan)
            wall_left  = self.grid_offset_x + BUBBLE_RADIUS
            wall_right = self.grid_offset_x + (COLS * BUBBLE_RADIUS * 2 + BUBBLE_RADIUS * 2) - BUBBLE_RADIUS
            if next_x <= wall_left:
                overflow = wall_left - next_x
                next_x = wall_left + overflow
                current_dx = abs(current_dx)
            elif next_x >= wall_right:
                overflow = next_x - wall_right
                next_x = wall_right - overflow
                current_dx = -abs(current_dx)
            
            if next_y - BUBBLE_RADIUS <= 0:
                points.append((next_x, BUBBLE_RADIUS))
                break
            
            hit_bubble = False
            for bubble in self.bubbles:
                dist_sq = (next_x - bubble.x())**2 + (next_y - bubble.y())**2
                if dist_sq < (BUBBLE_RADIUS * 2) ** 2:
                    points.append((next_x, next_y))
                    hit_bubble = True
                    break
            
            if hit_bubble:
                break
            
            points.append((next_x, next_y))
            current_x, current_y = next_x, next_y
        
        if len(points) >= 2:
            pen = QPen(QColor(255, 255, 255, 150), 3, Qt.DotLine)
            
            self.aim_line = []
            for i in range(len(points) - 1):
                line = QGraphicsLineItem(points[i][0], points[i][1], 
                                        points[i+1][0], points[i+1][1])
                line.setPen(pen)
                line.setZValue(50)
                self.addItem(line)
                self.aim_line.append(line)
    
    def clear_aim_line(self):
        """Hapus garis aim"""
        if self.aim_line:
            for line in self.aim_line:
                self.removeItem(line)
            self.aim_line = None

class GameView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)

        # --- LOGIC WALLPAPER BARU ---
        bg_path = Path(__file__).parent / "ui" / "bubble_bgn.webp"
        self.bg_pixmap = None
        
        if bg_path.exists():
            # Load gambar
            original_pix = QPixmap(str(bg_path))
            # Opsional: Bisa di-darken sedikit biar bubble terlihat jelas
            self.bg_pixmap = original_pix
        # ----------------------------

        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene_ref = scene
        self.setStyleSheet("border: none; background: transparent;")
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # FIX AIM LAG: Throttle aim update agar tidak dipanggil tiap pixel
        self._last_aim_angle = None
        self._aim_timer = QTimer()
        self._aim_timer.setSingleShot(True)
        self._aim_timer.setInterval(16)  # ~60fps max untuk aim line update
        self._aim_timer.timeout.connect(self._do_aim_update)
        self._pending_angle = None
        
    def _do_aim_update(self):
        """Lakukan update aim line yang sudah di-throttle"""
        if self._pending_angle is not None:
            self.scene_ref.update_aim_line(self._pending_angle)
            
    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        shooter_pos = self.scene_ref.shooter.pos()
        dx = pos.x() - shooter_pos.x()
        dy = shooter_pos.y() - pos.y()
        
        # Batasi agar tidak error saat kursor sejajar/di bawah shooter
        if dy > 0:
            angle = math.degrees(math.atan2(dy, dx))
            clamped_angle = max(15, min(165, angle))
            
            # 1. Putar shooter langsung (smooth, tidak di-throttle)
            self.scene_ref.shooter.set_angle(angle)
            
            # 2. Update aim line dengan throttle - hanya jika sudut berubah > 0.3 derajat
            if self._last_aim_angle is None or abs(clamped_angle - self._last_aim_angle) > 0.3:
                self._last_aim_angle = clamped_angle
                self._pending_angle = clamped_angle
                # Restart timer (debounce) - update setelah mouse berhenti sebentar
                if not self._aim_timer.isActive():
                    self._aim_timer.start()
            
    def resizeEvent(self, event):
        """Auto-fit scene ke ukuran view saat window di-resize / fullscreen"""
        super().resizeEvent(event)
        if self.scene_ref:
            self.fitInView(self.scene_ref.sceneRect(), Qt.KeepAspectRatioByExpanding)

    def showEvent(self, event):
        """Fit saat pertama kali ditampilkan"""
        super().showEvent(event)
        if self.scene_ref:
            self.fitInView(self.scene_ref.sceneRect(), Qt.KeepAspectRatioByExpanding)
        # Trigger HUD repositioning via parent
        parent = self.parent()
        if parent and hasattr(parent.parent() if parent else None, '_position_hud'):
            parent.parent()._position_hud()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.scene_ref.shoot_bubble(self.scene_ref.shooter.angle)
        elif event.button() == Qt.RightButton:
            self.scene_ref.swap_shooter_bubble()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Escape, Qt.Key_P):
            # Find MainWindow ancestor and toggle pause
            p = self.parent()
            while p:
                if hasattr(p, 'toggle_pause'):
                    p.toggle_pause()
                    break
                p = p.parent() if hasattr(p, 'parent') else None
        else:
            super().keyPressEvent(event)

class WelcomeScreen(QWidget):
    def __init__(self, start_callback, load_callback, quit_callback,
                 music_callback, sfx_callback,
                 daily_callback=None, leaderboard_callback=None,
                 achievements_callback=None, colorblind_callback=None,
                 custom_cursor=None, music_on=True, sfx_on=True,
                 colorblind_on=False, continue_daily_callback=None):
        super().__init__()

        bg_path = Path(__file__).parent / "ui" / "bubble_bgn.webp"
        self.bg_pixmap = None
        if bg_path.exists():
            self.bg_pixmap = QPixmap(str(bg_path))

        self.initial_music_on    = music_on
        self.initial_sfx_on      = sfx_on
        self.initial_colorblind  = colorblind_on
        self.custom_cursor       = custom_cursor if custom_cursor else Qt.PointingHandCursor

        self._daily_cb             = daily_callback
        self._lb_cb                = leaderboard_callback
        self._ach_cb               = achievements_callback
        self._cb_cb                = colorblind_callback
        self._load_cb              = load_callback
        self._continue_daily_cb    = continue_daily_callback

        self.setup_ui(start_callback, load_callback, quit_callback,
                      music_callback, sfx_callback)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.bg_pixmap:
            painter.drawPixmap(self.rect(), self.bg_pixmap)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        else:
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0.0, QColor("#0f172a"))
            grad.setColorAt(1.0, QColor("#1e293b"))
            painter.fillRect(self.rect(), grad)

    def _show_continue_menu(self):
        """Show sub-menu: Continue Regular Game or Continue Daily Challenge."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QPushButton
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dlg.setAttribute(Qt.WA_TranslucentBackground)
        dlg.setFixedSize(360, 260)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0a0e1a;
                border: 1px solid #1e3a5f;
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        vl = QVBoxLayout(card)
        vl.setContentsMargins(28, 28, 28, 24)
        vl.setSpacing(12)

        title = QLabel("💾  CONTINUE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #60a5fa; font-size: 20px; font-weight: 900; "
            "font-family: 'Segoe UI Black'; border: none; background: transparent;"
        )
        vl.addWidget(title)

        sub = QLabel("Which game would you like to resume?")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #64748b; font-size: 12px; border: none; background: transparent;")
        vl.addWidget(sub)

        btn_style_regular = """
            QPushButton {
                color: white; border: none; border-radius: 14px; padding: 13px 10px;
                font-family: 'Segoe UI'; font-size: 14px; font-weight: bold;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #3b82f6, stop:1 #2563eb);
                border-bottom: 3px solid #1d4ed8;
            }
            QPushButton:hover { background: #60a5fa; }
            QPushButton:pressed { margin-top: 2px; }
        """
        btn_style_daily = """
            QPushButton {
                color: white; border: none; border-radius: 14px; padding: 13px 10px;
                font-family: 'Segoe UI'; font-size: 14px; font-weight: bold;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #059669, stop:1 #047857);
                border-bottom: 3px solid #065f46;
            }
            QPushButton:hover { background: #34d399; }
            QPushButton:pressed { margin-top: 2px; }
        """

        btn_regular = QPushButton("🎮  Regular Game")
        btn_regular.setStyleSheet(btn_style_regular)
        btn_regular.setCursor(self.custom_cursor)
        btn_regular.clicked.connect(lambda: [dlg.accept(), self._load_cb and self._load_cb()])
        vl.addWidget(btn_regular)

        btn_daily = QPushButton("📅  Daily Challenge")
        btn_daily.setStyleSheet(btn_style_daily)
        btn_daily.setCursor(self.custom_cursor)
        btn_daily.clicked.connect(lambda: [dlg.accept(), self._continue_daily_cb and self._continue_daily_cb()])
        vl.addWidget(btn_daily)

        dlg.exec()

    def setup_ui(self, start_cb, load_cb, quit_cb, music_cb, sfx_cb):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Main card ──────────────────────────────────────────────────
        card = QFrame()
        card.setFixedWidth(480)
        card.setObjectName("MainCard")
        card.setStyleSheet("""
            #MainCard {
                background-color: rgba(10, 15, 30, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 28px;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 18)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(32, 32, 32, 28)
        card_layout.setAlignment(Qt.AlignCenter)

        # ── Title ──────────────────────────────────────────────────────
        title = QLabel("🐯  MACAN\nBUBBLE SHOOTER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI Black', 'Arial Black', sans-serif;
                font-size: 26px; font-weight: 900;
                color: #FFD700; background: transparent; border: none;
                margin-bottom: 4px; letter-spacing: 1px;
            }
        """)
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(18)
        glow.setColor(QColor(255, 215, 0, 110))
        glow.setOffset(0, 0)
        title.setGraphicsEffect(glow)
        card_layout.addWidget(title)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.15); max-height: 1px; border: none;")
        card_layout.addWidget(sep)
        card_layout.addSpacing(6)

        # ── Button helper ──────────────────────────────────────────────
        def _btn(label, grad_start, grad_end, border_col, cb, secondary=False):
            b = QPushButton(label)
            b.setCursor(self.custom_cursor)
            if secondary:
                b.setStyleSheet(f"""
                    QPushButton {{
                        color: white; border: none; border-radius: 22px;
                        padding: 13px 10px;
                        font-family: 'Segoe UI'; font-size: 15px; font-weight: bold;
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 {grad_start}, stop:1 {grad_end});
                        border-bottom: 3px solid {border_col};
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 {grad_end}, stop:1 {grad_start});
                    }}
                    QPushButton:pressed {{ margin-top: 2px; }}
                """)
            else:
                b.setStyleSheet(f"""
                    QPushButton {{
                        color: white; border: none; border-radius: 25px;
                        padding: 15px 10px;
                        font-family: 'Segoe UI'; font-size: 16px; font-weight: bold;
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 {grad_start}, stop:1 {grad_end});
                        border-bottom: 4px solid {border_col};
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 {grad_end}, stop:1 {grad_start});
                    }}
                    QPushButton:pressed {{ margin-top: 2px; }}
                """)
            if cb:
                b.clicked.connect(cb)
            return b

        # ── Primary action buttons ─────────────────────────────────────
        btn_start = _btn("🚀  NEW GAME",   "#f59e0b", "#d97706", "#b45309", start_cb)
        btn_load  = _btn("💾  CONTINUE",   "#3b82f6", "#2563eb", "#1d4ed8", self._show_continue_menu)

        # Daily Challenge — highlight if not yet played today
        daily_mgr = get_daily_manager()
        daily_label = "📅  DAILY CHALLENGE"
        if daily_mgr.is_today_completed():
            daily_label = f"📅  DAILY  ✅  {daily_mgr.today_score:,} pts"
        btn_daily = _btn(daily_label, "#059669", "#047857", "#065f46",
                         self._daily_cb)

        card_layout.addWidget(btn_start)
        card_layout.addWidget(btn_load)
        card_layout.addWidget(btn_daily)

        # ── Secondary row: Leaderboard + Achievements ──────────────────
        sec_row = QHBoxLayout()
        sec_row.setSpacing(8)

        btn_lb  = _btn("🏆  LEADERBOARD", "#78350f", "#92400e", "#451a03",
                       self._lb_cb, secondary=True)
        btn_ach = _btn("🏅  ACHIEVEMENTS", "#4c1d95", "#5b21b6", "#2e1065",
                       self._ach_cb, secondary=True)

        sec_row.addWidget(btn_lb)
        sec_row.addWidget(btn_ach)
        card_layout.addLayout(sec_row)

        # ── Quit ───────────────────────────────────────────────────────
        btn_quit = QPushButton("EXIT GAME")
        btn_quit.setCursor(self.custom_cursor)
        btn_quit.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4);
                color: #fca5a5; font-size: 13px; padding: 10px;
                border-radius: 18px; font-family: 'Segoe UI';
            }
            QPushButton:hover { background: rgba(239,68,68,0.35); color: white; }
        """)
        btn_quit.clicked.connect(quit_cb)
        card_layout.addSpacing(4)
        card_layout.addWidget(btn_quit)

        # ── Toggle row ─────────────────────────────────────────────────
        card_layout.addSpacing(6)
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background: rgba(255,255,255,0.10); max-height: 1px; border: none;")
        card_layout.addWidget(sep2)
        card_layout.addSpacing(6)

        checkbox_style = """
            QCheckBox {
                color: rgba(255,255,255,0.85); font-family: 'Segoe UI';
                font-size: 12px; font-weight: 600; spacing: 7px;
            }
            QCheckBox::indicator {
                width: 16px; height: 16px; border-radius: 4px;
                border: 2px solid #475569; background: transparent;
            }
            QCheckBox::indicator:checked { background: #10b981; border-color: #10b981; }
        """

        toggles_layout = QHBoxLayout()
        toggles_layout.setAlignment(Qt.AlignCenter)
        toggles_layout.setSpacing(18)

        self.music_toggle = QCheckBox("MUSIC")
        self.music_toggle.setStyleSheet(checkbox_style)
        self.music_toggle.setCursor(self.custom_cursor)
        self.music_toggle.setChecked(self.initial_music_on)
        self.music_toggle.toggled.connect(music_cb)

        self.sfx_toggle = QCheckBox("SOUND FX")
        self.sfx_toggle.setStyleSheet(checkbox_style)
        self.sfx_toggle.setCursor(self.custom_cursor)
        self.sfx_toggle.setChecked(self.initial_sfx_on)
        self.sfx_toggle.toggled.connect(sfx_cb)

        self.colorblind_toggle = QCheckBox("COLOR-BLIND")
        self.colorblind_toggle.setStyleSheet(checkbox_style)
        self.colorblind_toggle.setCursor(self.custom_cursor)
        self.colorblind_toggle.setChecked(self.initial_colorblind)
        if self._cb_cb:
            self.colorblind_toggle.toggled.connect(self._cb_cb)

        toggles_layout.addWidget(self.music_toggle)
        toggles_layout.addWidget(self.sfx_toggle)
        toggles_layout.addWidget(self.colorblind_toggle)
        card_layout.addLayout(toggles_layout)

        # ── Version & shortcuts hint ───────────────────────────────────
        ver = QLabel("v6.7.1 — Dynamic Edition  ·  ESC / P to pause")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; "
                          "margin-top: 8px; background: transparent; border: none;")
        card_layout.addWidget(ver)

        layout.addWidget(card)

class MainWindow(QMainWindow):    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macan Bubble Shooter - Dynamic Edition")
        icon_path = "marble.ico"
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, icon_path)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.showFullScreen()

        # 1. SETUP PATH FOLDER (Paling Awal & Pasti)
        self.user_data_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6"
        self.save_dir = self.user_data_dir / "saves"
        
        # Buat folder save jika belum ada (PENTING: dilakukan di awal)
        try:
            self.save_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ Error creating save directory: {e}")

        # === SETUP CUSTOM CURSOR ===
        self.custom_cursor = get_custom_cursor()
        self.custom_hand_cursor = get_custom_cursor()
        
        if self.custom_cursor:
            self.setCursor(self.custom_cursor)
        else:
            self.custom_cursor = Qt.CrossCursor
            self.custom_hand_cursor = Qt.PointingHandCursor
            self.setCursor(Qt.CrossCursor)

        # Sound Manager
        self.sound_manager = get_sound_manager()
        
        # 2. LOAD SETTINGS DATA
        self.load_settings_variables()

        # --- SETUP STACKED WIDGET ---
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # 3. Setup Welcome Screen (Index 0)
        self.welcome_screen = WelcomeScreen(
            self.start_new_game,
            self.load_saved_game,
            self.close,
            self.toggle_music,
            self.toggle_sfx,
            daily_callback=self.start_daily_challenge,
            leaderboard_callback=self.show_leaderboard_menu,
            achievements_callback=self.show_achievements_menu,
            colorblind_callback=self.toggle_colorblind,
            music_on=self.music_enabled,
            sfx_on=self.sfx_enabled,
            colorblind_on=self.colorblind_enabled,
            continue_daily_callback=self.continue_daily_challenge,
        )
        self.central_stack.addWidget(self.welcome_screen)
        
        # 4. TERAPKAN SETTINGS KE UI (Sync)
        # Paksa UI mengikuti data yang sudah di-load
        self.sync_ui_with_settings()

        # 5. Setup Game Screen Container (Index 1)
        self.game_container = QWidget()
        self.setup_game_ui()
        self.central_stack.addWidget(self.game_container)

        # === AUDIO START (CONDITIONAL) ===
        # Hanya nyalakan musik jika settingannya TRUE
        if self.music_enabled:
            start_bgm()
        else:
            # Pastikan mati
            self.sound_manager.pause_bgm()

        # Load High Score
        self.load_high_score_data()

    # --- SETTINGS MANAGEMENT (FIXED) ---

    def load_settings_variables(self):
        """Load settings JSON into self variables."""
        settings_path = self.save_dir / "settings.json"
        self.music_enabled     = True
        self.sfx_enabled       = True
        self.colorblind_enabled = False

        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                    self.music_enabled      = data.get('music_enabled', True)
                    self.sfx_enabled        = data.get('sfx_enabled', True)
                    self.colorblind_enabled = data.get('colorblind_enabled', False)
                print(f"📂 Loaded Settings: Music={self.music_enabled}, SFX={self.sfx_enabled}, CB={self.colorblind_enabled}")
            except Exception as e:
                print(f"❌ Error reading settings file: {e}")
        else:
            print("⚠️ No settings file, using defaults")

        # Apply colorblind mode immediately on load
        set_colorblind_mode(self.colorblind_enabled)

    def sync_ui_with_settings(self):
        """Sync checkbox UI state with loaded variables."""
        try:
            ws = self.welcome_screen
            ws.music_toggle.blockSignals(True)
            ws.sfx_toggle.blockSignals(True)
            ws.colorblind_toggle.blockSignals(True)
            ws.music_toggle.setChecked(self.music_enabled)
            ws.sfx_toggle.setChecked(self.sfx_enabled)
            ws.colorblind_toggle.setChecked(self.colorblind_enabled)
            ws.music_toggle.blockSignals(False)
            ws.sfx_toggle.blockSignals(False)
            ws.colorblind_toggle.blockSignals(False)
        except Exception as e:
            print(f"⚠️ UI Sync Warning: {e}")

    def save_settings(self):
        """Save current settings to JSON."""
        if not self.save_dir.exists():
            try:
                self.save_dir.mkdir(parents=True, exist_ok=True)
            except:
                pass
        data = {
            'music_enabled':      self.music_enabled,
            'sfx_enabled':        self.sfx_enabled,
            'colorblind_enabled': self.colorblind_enabled,
        }
        try:
            with open(self.save_dir / "settings.json", 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"❌ Failed to save settings: {e}")
            
    # Hapus/Ganti method load_settings yang lama dengan ini jika masih ada pemanggilan lain
    def load_settings(self):
        """Wrapper untuk kompatibilitas jika masih ada yang memanggil load_settings()"""
        self.load_settings_variables()
        self.sync_ui_with_settings()
        if self.music_enabled:
            if self.sound_manager.bgm_player.playbackState() != QMediaPlayer.PlayingState:
                self.sound_manager.resume_bgm()
        else:
            self.sound_manager.pause_bgm()
        
    def setup_game_ui(self):
        """Membuat layout game - GameView fullscreen, HUD overlay di atasnya"""
        self.game_container.setStyleSheet("background-color: #000000;")

        self.scene = GameScene()
        self.view = GameView(self.scene)
        self.view.setParent(self.game_container)

        # === LAYER 1: HUD overlay ===
        self.hud_overlay = QWidget(self.game_container)
        self.hud_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.hud_overlay.setStyleSheet("background: transparent;")

        hud_layout = QHBoxLayout(self.hud_overlay)
        hud_layout.setContentsMargins(6, 4, 6, 4)
        hud_layout.setSpacing(4)

        # Style pill
        pill_style = """
            QLabel {
                background-color: rgba(0, 0, 0, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 10px;
                padding: 3px 8px;
                color: white;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 11px;
            }
        """
        combo_pill_style = """
            QLabel {
                background-color: rgba(255, 140, 0, 0.8);
                border: 1px solid rgba(255, 200, 50, 0.6);
                border-radius: 10px;
                padding: 3px 8px;
                color: white;
                font-family: 'Segoe UI Black';
                font-weight: 900;
                font-size: 11px;
            }
        """
        timer_pill_style = """
            QLabel {
                background-color: rgba(16, 185, 129, 0.75);
                border: 1px solid rgba(52, 211, 153, 0.6);
                border-radius: 10px;
                padding: 3px 8px;
                color: white;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 11px;
            }
        """

        self.high_score_label = QLabel("🏆 BEST: 0")
        self.high_score_label.setStyleSheet(pill_style)

        self.score_label = QLabel("💎 SCORE: 0")
        self.score_label.setStyleSheet(pill_style)

        self.level_label = QLabel("⚡ LEVEL: 1")
        self.level_label.setStyleSheet(pill_style)

        self.drop_label = QLabel(f"💀 DROP: {SHOTS_PER_DROP}/{SHOTS_PER_DROP}")
        self.drop_label.setStyleSheet(pill_style)

        # === Combo label (hidden when combo = 0) ===
        self.combo_label = QLabel("🔥 COMBO: 0")
        self.combo_label.setStyleSheet(pill_style)
        self.combo_label.setVisible(False)

        # === Shot timer label ===
        self.timer_label = QLabel("⏱ 8.0s  1.0x")
        self.timer_label.setStyleSheet(timer_pill_style)

        # === Playtime label ===
        self.playtime_label = QLabel("🕐 00:00")
        self.playtime_label.setStyleSheet(pill_style)

        # === Danger label (hidden when safe) ===
        self.danger_label = QLabel("⚠ DANGER")
        self.danger_label.setStyleSheet("""
            QLabel {
                background-color: rgba(239, 68, 68, 0.9);
                border: 1px solid rgba(255, 100, 100, 0.95);
                border-radius: 10px;
                padding: 3px 8px;
                color: white;
                font-family: 'Segoe UI Black';
                font-weight: 900;
                font-size: 11px;
            }
        """)
        self.danger_label.setVisible(False)

        hud_layout.addWidget(self.high_score_label)
        hud_layout.addWidget(self.score_label)
        hud_layout.addWidget(self.level_label)
        hud_layout.addWidget(self.drop_label)
        hud_layout.addWidget(self.combo_label)
        hud_layout.addWidget(self.danger_label)
        hud_layout.addWidget(self.timer_label)
        hud_layout.addWidget(self.playtime_label)

        hud_layout.addStretch(1)

        # Power panel
        power_panel = self.create_power_panel()
        hud_layout.addWidget(power_panel)

        hud_layout.addSpacing(4)

        # === Leaderboard button ===
        self.lb_btn = QPushButton("🏆")
        self.lb_btn.setToolTip("Leaderboard")
        self.lb_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 215, 0, 0.2);
                border: 1px solid rgba(255, 215, 0, 0.5);
                border-radius: 8px; color: #FFD700;
                font-size: 14px; padding: 3px 8px; min-width: 32px;
            }
            QPushButton:hover { background-color: rgba(255, 215, 0, 0.4); }
        """)
        self.lb_btn.setCursor(self.custom_hand_cursor)
        self.lb_btn.clicked.connect(self.show_leaderboard)
        hud_layout.addWidget(self.lb_btn)

        # === Achievements button ===
        self.ach_btn = QPushButton("🏅")
        self.ach_btn.setToolTip("Achievements")
        self.ach_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(139, 92, 246, 0.25);
                border: 1px solid rgba(139, 92, 246, 0.5);
                border-radius: 8px; color: #c4b5fd;
                font-size: 14px; padding: 3px 8px; min-width: 32px;
            }
            QPushButton:hover { background-color: rgba(139, 92, 246, 0.5); }
        """)
        self.ach_btn.setCursor(self.custom_hand_cursor)
        self.ach_btn.clicked.connect(self.show_achievements)
        hud_layout.addWidget(self.ach_btn)

        # === Replay button ===
        self.replay_btn = QPushButton("🎬")
        self.replay_btn.setToolTip("Best Replays")
        self.replay_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(14, 165, 233, 0.2);
                border: 1px solid rgba(14, 165, 233, 0.4);
                border-radius: 8px; color: #7dd3fc;
                font-size: 14px; padding: 3px 8px; min-width: 32px;
            }
            QPushButton:hover { background-color: rgba(14, 165, 233, 0.4); }
        """)
        self.replay_btn.setCursor(self.custom_hand_cursor)
        self.replay_btn.clicked.connect(self.show_replay_list)
        hud_layout.addWidget(self.replay_btn)

        hud_layout.addSpacing(2)

        # Tombol MENU
        self.menu_btn = QPushButton("🏠 MENU")
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 8px;
                color: #e2e8f0;
                font-weight: bold;
                font-size: 11px;
                padding: 3px 10px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
                border-color: white;
            }
        """)
        self.menu_btn.setCursor(self.custom_cursor)
        self.menu_btn.clicked.connect(self.back_to_menu)
        hud_layout.addWidget(self.menu_btn)

        self._position_hud()

        # Connect Signals lama
        self.scene.score_changed.connect(self.update_score)
        self.scene.drop_counter_changed.connect(self.update_drop_counter)
        self.scene.level_changed.connect(self.update_level)
        self.scene.game_over.connect(self.show_game_over)
        self.scene.next_bubble_changed.connect(self.update_next_bubble_ui)
        self.scene.high_score_changed.connect(self.update_high_score)
        self.scene.power_collected.connect(self.on_power_collected)
        self.scene.power_updated.connect(self.update_all_power_buttons)

        # === Connect Sinyal BARU ===
        self.scene.combo_changed.connect(self.update_combo_label)
        self.scene.timer_tick.connect(self.update_timer_label)
        self.scene.multiplier_changed.connect(self.update_multiplier_display)
        self.scene.playtime_changed.connect(self.update_playtime_label)
        self.scene.danger_level_changed.connect(self.on_danger_level_changed)

        # Stop timer initially
        self.scene.timer.stop()

        self.game_container.installEventFilter(self)

    def _position_hud(self):
        """Posisikan HUD overlay di top, GameView mengisi seluruh container"""
        if not hasattr(self, 'hud_overlay') or not hasattr(self, 'view'):
            return
        w = self.game_container.width()
        h = self.game_container.height()
        if w == 0 or h == 0:
            return
        # GameView mengisi SELURUH area (di bawah HUD juga, HUD transparan)
        self.view.setGeometry(0, 0, w, h)
        # HUD tinggi menyesuaikan konten (sizeHint), minimum 48px
        hud_h = max(48, self.hud_overlay.sizeHint().height())
        self.hud_overlay.setGeometry(0, 0, w, hud_h)
        self.hud_overlay.raise_()

    def eventFilter(self, obj, event):
        """Intercept resize event dari game_container"""
        from PySide6.QtCore import QEvent
        if obj == self.game_container and event.type() == QEvent.Type.Resize:
            self._position_hud()
        return super().eventFilter(obj, event)
    
    def start_new_game(self):
        """Memulai game baru dari nol"""
        self.scene.reset_game()
        self.scene.timer.start()
        self.central_stack.setCurrentIndex(1)
        self.load_high_score_data()
        QTimer.singleShot(50, self._position_hud)

    def load_saved_game(self):
        """Load game dari file"""
        self.load_game_data()
        self.scene.timer.start()
        self.scene.shot_timer.start(rush_mode=False)
        self.scene.game_timer.start()
        self.central_stack.setCurrentIndex(1)
        QTimer.singleShot(50, self._position_hud)

    def back_to_menu(self):
        """Return to main menu, pause game and save."""
        self.scene.timer.stop()
        self.scene.shot_timer.stop()
        self.scene.game_timer.stop()
        self._save_replay_after_session()
        self.save_game()
        self.central_stack.setCurrentIndex(0)

    def toggle_music(self, checked):
        self.music_enabled = checked
        if checked:
            start_bgm()
            self.sound_manager.resume_bgm()
        else:
            self.sound_manager.pause_bgm()
        
        # Simpan setiap kali diklik
        self.save_settings()

    def toggle_sfx(self, checked):
        self.sfx_enabled = checked
        # Simpan setiap kali diklik
        self.save_settings()

    def create_power_panel(self):
        """Power panel - 1 baris, autofit, teks tidak terpotong"""
        power_frame = QFrame()
        power_frame.setFrameStyle(QFrame.NoFrame)
        power_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.68);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
            }
        """)

        power_layout = QHBoxLayout(power_frame)
        power_layout.setSpacing(3)
        power_layout.setContentsMargins(6, 3, 6, 3)
        power_layout.setAlignment(Qt.AlignVCenter)

        # Label "SKILLS:" kecil
        lbl_power = QLabel("SKILLS:")
        lbl_power.setStyleSheet("""
            color: #FFD700;
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
            padding: 0px 3px 0px 0px;
        """)
        power_layout.addWidget(lbl_power)

        self.power_buttons = {}
        manager = get_power_manager()

        # Emoji & nama pendek per power type
        power_info_map = {
            PowerUpType.BOMB:     ("💣", "BOMB"),
            PowerUpType.LASER:    ("⚡", "LASER"),
            PowerUpType.RAINBOW:  ("🌈", "RAINBO"),
            PowerUpType.FIREBALL: ("🔥", "FIREBA"),
            PowerUpType.FREEZE:   ("❄️", "FREEZE"),
        }

        power_types = [
            PowerUpType.BOMB,
            PowerUpType.LASER,
            PowerUpType.RAINBOW,
            PowerUpType.FIREBALL,
            PowerUpType.FREEZE,
        ]

        for p_type in power_types:
            info = manager.get_power_info(p_type)
            emoji, short_name = power_info_map[p_type]
            charges = info["charges"]

            btn = QPushButton(emoji + short_name + chr(10) + str(charges))
            btn.setCursor(self.custom_hand_cursor)
            # Biarkan Qt menentukan lebar berdasarkan konten, hanya fix tinggi
            btn.setFixedHeight(40)
            btn.setMinimumWidth(58)
            btn.setSizePolicy(
                btn.sizePolicy().horizontalPolicy(),
                btn.sizePolicy().verticalPolicy()
            )

            btn.clicked.connect(lambda checked=False, t=p_type: self.activate_powerup(t))
            self.update_power_button_style(btn, p_type)
            self.power_buttons[p_type] = btn
            power_layout.addWidget(btn)

        return power_frame
    
    # --- Tambahkan metode ini di dalam class MainWindow ---
    def activate_powerup(self, power_type):
        """Menghubungkan tombol UI dengan logika aktivasi power di Scene"""
        # Cek apakah scene sudah siap (karena panel dibuat sebelum scene diinisialisasi)
        if hasattr(self, 'scene'):
            self.scene.activate_power(power_type)
    
    def create_power_button(self, power_type):
        """Buat tombol power individual"""
        btn = QPushButton(f"{get_power_manager().get_power_description(power_type).split()[0]}\n0")
        btn.setFixedSize(100, 60)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.scene.activate_power(power_type))
        # Style akan di-update berdasarkan status
        self.update_power_button_style(btn, power_type)
        return btn
    
    def update_power_button_style(self, btn, power_type):
        """Update style button berdasarkan status"""
        info = get_power_manager().get_power_info(power_type)
        base = """
            QPushButton {
                font-size: 10px;
                font-weight: bold;
                font-family: 'Segoe UI';
                border-radius: 7px;
                padding: 2px 4px;
                text-align: center;
            }
        """
        if info and info['can_use']:
            btn.setStyleSheet(base + """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: 2px solid #34d399;
            }
            QPushButton:hover { background: #34d399; }
            """)
        else:
            btn.setStyleSheet(base + """
            QPushButton {
                background: rgba(40, 40, 60, 0.7);
                color: #94a3b8;
                border: 1px solid #334155;
            }
            QPushButton:hover { background: rgba(60, 60, 80, 0.8); }
            """)

    def on_power_collected(self, power_type):
        """Slot saat player mendapatkan power-up"""
        self.update_all_power_buttons()

    def update_all_power_buttons(self):
        """Refresh text dan style semua tombol power"""
        manager = get_power_manager()
        
        # Pastikan self.power_buttons sudah ada
        if not hasattr(self, 'power_buttons'):
            return

        power_info_map = {
            PowerUpType.BOMB:     ("💣", "BOMB"),
            PowerUpType.LASER:    ("⚡", "LASER"),
            PowerUpType.RAINBOW:  ("🌈", "RAINBO"),
            PowerUpType.FIREBALL: ("🔥", "FIREBA"),
            PowerUpType.FREEZE:   ("❄️", "FREEZE"),
        }
        for p_type, btn in self.power_buttons.items():
            info = manager.get_power_info(p_type)
            if info:
                emoji, short_name = power_info_map.get(p_type, ("⭐", "PWR"))
                btn.setText(emoji + short_name + chr(10) + str(info['charges']))
                self.update_power_button_style(btn, p_type)

    # --- UI UPDATE SLOTS ---

    def update_score(self, score):
        if hasattr(self, 'score_label'):
            self.score_label.setText(f"💎 SCORE: {score:,}")

    def update_high_score(self, val):
        if hasattr(self, 'high_score_label'):
            self.high_score_label.setText(f"🏆 BEST: {val:,}")
        self.save_high_score_data()

    def update_level(self, level):
        if hasattr(self, 'level_label'):
            self.level_label.setText(f"⚡ LEVEL: {level}")

    def update_drop_counter(self, count):
        if hasattr(self, 'drop_label'):
            self.drop_label.setText(f"💀 DROP: {count}/{SHOTS_PER_DROP}")

    def update_next_bubble_ui(self, color_idx):
        """Update next bubble preview display"""
        if hasattr(self, 'next_bubble_indicator'):
            try:
                self.scene.removeItem(self.next_bubble_indicator)
                self.scene.removeItem(self.next_text_item)
            except Exception:
                pass

        base_y = self.scene.scene_height - 110
        base_x = self.scene.grid_offset_x + 50

        font = QFont("Segoe UI", 10, QFont.Bold)
        self.next_text_item = self.scene.addText("NEXT", font)
        self.next_text_item.setDefaultTextColor(QColor("#a0aec0"))
        text_width = self.next_text_item.boundingRect().width()
        self.next_text_item.setPos(base_x - text_width / 2, base_y + 30)

        self.next_bubble_indicator = Bubble(color_idx, base_x, base_y, is_preview=True)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.next_bubble_indicator.setGraphicsEffect(shadow)
        self.scene.addItem(self.next_bubble_indicator)

    # --- HUD Slots: Timer, Combo, Danger ---

    def update_combo_label(self, combo: int):
        if combo >= 2:
            self.combo_label.setVisible(True)
            color = "#ff4500" if combo >= 5 else "#ffa500"
            self.combo_label.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(255, 100, 0, 0.75);
                    border: 1px solid {color};
                    border-radius: 10px;
                    padding: 3px 8px;
                    color: white;
                    font-family: 'Segoe UI Black';
                    font-weight: 900;
                    font-size: 11px;
                }}
            """)
            self.combo_label.setText(f"🔥 COMBO x{combo}")
        else:
            self.combo_label.setVisible(False)

    def update_timer_label(self, remaining: float):
        if not hasattr(self, 'timer_label'):
            return
        if remaining > 5.0:
            color_style = "background-color: rgba(16, 185, 129, 0.75); border: 1px solid rgba(52, 211, 153, 0.6);"
        elif remaining > 2.5:
            color_style = "background-color: rgba(234, 179, 8, 0.75); border: 1px solid rgba(250, 204, 21, 0.6);"
        else:
            color_style = "background-color: rgba(239, 68, 68, 0.85); border: 1px solid rgba(248, 113, 113, 0.8);"
        self.timer_label.setStyleSheet(f"""
            QLabel {{
                {color_style}
                border-radius: 10px;
                padding: 3px 8px;
                color: white;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 11px;
            }}
        """)
        self.timer_label.setText(f"⏱ {remaining:.1f}s")

    def update_multiplier_display(self, mult: float):
        if not hasattr(self, 'timer_label'):
            return
        current = self.timer_label.text().split("  ")[0]
        suffix = f"  {mult:.1f}x" if mult > 1.0 else ""
        self.timer_label.setText(current + suffix)

    def update_playtime_label(self, time_str: str):
        if hasattr(self, 'playtime_label'):
            self.playtime_label.setText(f"🕐 {time_str}")

    def on_danger_level_changed(self, level: int):
        if not hasattr(self, 'drop_label'):
            return

        # --- Danger label pill (shows/hides based on level) ---
        if hasattr(self, 'danger_label'):
            if level >= 3:
                self.danger_label.setText("⚠ CRITICAL")
                self.danger_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(220, 38, 38, 0.95);
                        border: 1px solid rgba(255, 100, 100, 1.0);
                        border-radius: 10px; padding: 3px 8px;
                        color: white; font-family: 'Segoe UI Black';
                        font-weight: 900; font-size: 11px;
                    }
                """)
                self.danger_label.setVisible(True)
            elif level >= 2:
                self.danger_label.setText("⚠ DANGER")
                self.danger_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(239, 68, 68, 0.85);
                        border: 1px solid rgba(255, 120, 50, 0.9);
                        border-radius: 10px; padding: 3px 8px;
                        color: white; font-family: 'Segoe UI Black';
                        font-weight: 900; font-size: 11px;
                    }
                """)
                self.danger_label.setVisible(True)
            elif level >= 1:
                self.danger_label.setText("⚠ WARNING")
                self.danger_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(234, 179, 8, 0.80);
                        border: 1px solid rgba(250, 204, 21, 0.7);
                        border-radius: 10px; padding: 3px 8px;
                        color: white; font-family: 'Segoe UI Black';
                        font-weight: 900; font-size: 11px;
                    }
                """)
                self.danger_label.setVisible(True)
            else:
                self.danger_label.setVisible(False)

        # --- Drop counter pill color change ---
        if level >= 3:
            self.drop_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(239, 68, 68, 0.85);
                    border: 1px solid rgba(255, 100, 100, 0.9);
                    border-radius: 10px; padding: 3px 8px;
                    color: white; font-family: 'Segoe UI';
                    font-weight: bold; font-size: 11px;
                }
            """)
        elif level >= 2:
            self.drop_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(234, 179, 8, 0.75);
                    border: 1px solid rgba(250, 204, 21, 0.6);
                    border-radius: 10px; padding: 3px 8px;
                    color: white; font-family: 'Segoe UI';
                    font-weight: bold; font-size: 11px;
                }
            """)
        else:
            self.drop_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 0.72);
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    border-radius: 10px; padding: 3px 8px;
                    color: white; font-family: 'Segoe UI';
                    font-weight: bold; font-size: 11px;
                }
            """)

    def show_leaderboard(self):
        was_active = self.scene.timer.isActive()
        if was_active:
            self.scene.timer.stop()
            self.scene.shot_timer.pause()
            self.scene.game_timer.pause()
        dlg = LeaderboardDialog(self, current_score=self.scene.score_mgr.score, current_level=self.scene.level)
        dlg.exec()
        if was_active:
            self.scene.timer.start()
            self.scene.shot_timer.resume()
            self.scene.game_timer.resume()

    def show_achievements(self):
        was_active = self.scene.timer.isActive()
        if was_active:
            self.scene.timer.stop()
            self.scene.shot_timer.pause()
            self.scene.game_timer.pause()
        dlg = AchievementDialog(self)
        dlg.exec()
        if was_active:
            self.scene.timer.start()
            self.scene.shot_timer.resume()
            self.scene.game_timer.resume()

    # --- SAVE / LOAD DATA ---

    def save_high_score_data(self):
        data = {'high_score': self.scene.high_score}
        path = self.save_dir / "highscore.json"
        try:
            with open(path, 'w') as f: json.dump(data, f)
        except Exception as e: print(f"Err HS Save: {e}")

    def load_high_score_data(self):
        path = self.save_dir / "highscore.json"
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.scene.high_score = data.get('high_score', 0)
                    self.update_high_score(self.scene.high_score)
            except: pass

    def save_game(self):
        if self.scene.check_game_over_condition(): return

        power_manager = get_power_manager()
        power_data = {p_type: p_obj.charges for p_type, p_obj in power_manager.powers.items()}

        save_data = {
            'score':            self.scene.score_mgr.score,
            'high_score':       self.scene.score_mgr.high_score,
            'level':            self.scene.level,
            'shots_until_drop': self.scene.shots_until_drop,
            'grid':             self.scene.grid.grid,
            'shooter_current':  self.scene.shooter.current_color,
            'shooter_next':     self.scene.shooter.next_color,
            'powerups':         power_data,
            'playtime':         self.scene.game_timer.elapsed,
            'total_shots':      self.scene.score_mgr.total_shots,
            'total_pops':       self.scene.score_mgr.total_pops,
            'best_combo':       self.scene.score_mgr.best_combo,
        }

        try:
            with open(self.save_dir / "save_v6.json", 'w') as f:
                json.dump(save_data, f)
            print("✅ Game Saved!")
        except Exception as e:
            print(f"Save Fail: {e}")

    def load_game_data(self):
        self.load_high_score_data()

        save_file = self.save_dir / "save_v6.json"
        if save_file.exists():
            try:
                with open(save_file, 'r') as f:
                    data = json.load(f)

                    # Restore scene state
                    self.scene.score = data.get('score', 0)
                    self.scene.level = data.get('level', 1)
                    self.scene.shots_until_drop = data.get('shots_until_drop', SHOTS_PER_DROP)

                    # Restore score_mgr
                    self.scene.score_mgr._score = self.scene.score
                    hs = data.get('high_score', self.scene.high_score)
                    self.scene.score_mgr._high_score = hs
                    self.scene.high_score = hs

                    if 'grid' in data:
                        self.scene.grid.grid = data['grid']
                        self.scene.create_bubbles_visuals()

                    self.scene.shooter.current_color = data.get('shooter_current', 0)
                    self.scene.shooter.next_color = data.get('shooter_next', 1)
                    self.scene.shooter.update_loaded_bubble_visual()

                    if 'powerups' in data:
                        pm = get_power_manager()
                        for p_type, count in data['powerups'].items():
                            if p_type in pm.powers:
                                pm.powers[p_type].charges = count
                        self.update_all_power_buttons()

                    # Refresh UI
                    self.scene.score_changed.emit(self.scene.score)
                    self.scene.level_changed.emit(self.scene.level)
                    self.scene.drop_counter_changed.emit(self.scene.shots_until_drop)
                    self.scene.next_bubble_changed.emit(self.scene.shooter.next_color)
                    self.scene.update_background_color()
                    self.update_high_score(hs)

                    print("✅ Game Loaded Successfully!")

            except Exception as e:
                print(f"Load Fail: {e}")
                self.start_new_game()
        else:
            self.start_new_game()
           
    def show_game_over(self):
        self.scene.timer.stop()
        self.scene.shot_timer.stop()
        self.scene.game_timer.stop()
        self.save_high_score_data()
        self._save_replay_after_session()

        stats = self.scene.score_mgr.get_stats()
        playtime = self.scene.game_timer.elapsed

        # Store stats for leaderboard entry (name filled in by dialog)
        self._pending_lb_stats = {
            'score':       stats['score'],
            'level':       self.scene.level,
            'total_shots': stats['total_shots'],
            'best_combo':  stats['best_combo'],
            'playtime_sec': playtime,
        }

        full_stats = {
            'score':       stats['score'],
            'high_score':  self.scene.score_mgr.high_score,
            'level':       self.scene.level,
            'total_shots': stats['total_shots'],
            'total_pops':  stats['total_pops'],
            'best_combo':  stats['best_combo'],
            'playtime':    playtime,
        }

        dlg = GameOverDialog(
            parent=self,
            stats=full_stats,
            on_continue=self.continue_from_save,
            on_new_game=self.start_new_game_fresh,
            on_menu=self.back_to_menu,
            on_name_entered=self._save_leaderboard_entry,
        )
        dlg.exec()

    def _save_leaderboard_entry(self, name: str):
        """Save leaderboard entry with the player's chosen name."""
        s = getattr(self, '_pending_lb_stats', None)
        if not s:
            return
        leaderboard = get_leaderboard(self.save_dir)
        leaderboard.add_entry(
            score=s['score'],
            level=s['level'],
            name=name or "PLAYER",
            total_shots=s['total_shots'],
            best_combo=s['best_combo'],
            playtime_sec=s['playtime_sec'],
        )
        self._pending_lb_stats = None

    def continue_from_save(self):
        """Load game dari save terakhir dan lanjutkan"""
        self.load_game_data()
        self.scene.timer.start()
        self.scene.shot_timer.start(rush_mode=False)
        self.scene.game_timer.start()
        self.central_stack.setCurrentIndex(1)
        QTimer.singleShot(50, self._position_hud)

    def start_new_game_fresh(self):
        """Mulai game baru dari nol (hapus save)"""
        save_file = self.save_dir / "save_v6.json"
        if save_file.exists():
            try:
                save_file.unlink()
            except Exception as e:
                print(f"Error deleting save: {e}")
        self.scene.reset_game()
        self.scene.timer.start()
        self.central_stack.setCurrentIndex(1)
        QTimer.singleShot(50, self._position_hud)

    def toggle_pause(self):
        """Pause / resume — triggered by HUD button OR Esc/P keyboard shortcut."""
        if not hasattr(self, 'scene'):
            return
        if self.scene.timer.isActive():
            self.scene.timer.stop()
            self.scene.shot_timer.pause()
            self.scene.game_timer.pause()
            self.sound_manager.pause_bgm()
            # Show pause overlay hint on HUD button if it exists
            if hasattr(self, 'menu_btn'):
                self.menu_btn.setText("▶ RESUME  (P)")
        else:
            self.scene.timer.start()
            self.scene.shot_timer.resume()
            self.scene.game_timer.resume()
            if self.music_enabled:
                self.sound_manager.resume_bgm()
            if hasattr(self, 'menu_btn'):
                self.menu_btn.setText("🏠 MENU")

    def toggle_colorblind(self, checked: bool):
        """Toggle color-blind mode and rebuild all visible bubbles."""
        self.colorblind_enabled = checked
        set_colorblind_mode(checked)
        self.save_settings()
        # Rebuild all bubble visuals in-place if game is active
        if hasattr(self, 'scene'):
            for bubble in self.scene.bubbles:
                # Remove old child items (symbol labels) then re-setup
                for child in bubble.childItems():
                    child.setParentItem(None)
                bubble.setup_appearance()

    # ── Menu-accessible Leaderboard / Achievement (from main menu) ───────────

    def show_leaderboard_menu(self):
        """Open leaderboard from the main menu (no game to pause)."""
        dlg = LeaderboardDialog(self, current_score=0, current_level=1)
        dlg.exec()

    def show_achievements_menu(self):
        """Open achievement browser from the main menu."""
        dlg = AchievementDialog(self)
        dlg.exec()

    # ── Daily Challenge ───────────────────────────────────────────────────────

    def start_daily_challenge(self):
        """Start today's daily challenge grid."""
        daily_mgr = get_daily_manager(self.save_dir)

        # Reset scene then inject the daily grid
        self.scene.reset_game()
        self.scene.daily_mode  = True
        self.scene.daily_shots = 0

        try:
            daily_grid = daily_mgr.start()
            # Pad grid to ROWS if needed
            while len(daily_grid) < ROWS:
                daily_grid.append([None] * COLS)
            self.scene.grid.grid = daily_grid
            self.scene.create_bubbles_visuals()
        except Exception as e:
            print(f"Daily grid error: {e}")

        # Update HUD to show shot cap
        if hasattr(self, 'drop_label'):
            self.drop_label.setText(f"📅 DAILY — {DAILY_SHOTS_CAP} shots")

        self.scene.timer.start()
        self.central_stack.setCurrentIndex(1)
        QTimer.singleShot(50, self._position_hud)

        # Connect daily shot-cap signal
        daily_mgr.shots_remaining_changed.connect(self._on_daily_shots_changed)

    def continue_daily_challenge(self):
        """Resume today's daily challenge if it was already started."""
        daily_mgr = get_daily_manager(self.save_dir)

        # If today's challenge was completed, just show a message and start fresh
        if daily_mgr.is_today_completed():
            self.start_daily_challenge()
            return

        # If today's challenge was started (but not completed), resume it
        if daily_mgr.is_today_played():
            self.scene.reset_game()
            self.scene.daily_mode  = True
            self.scene.daily_shots = 0

            try:
                daily_grid = daily_mgr.start()
                while len(daily_grid) < ROWS:
                    daily_grid.append([None] * COLS)
                self.scene.grid.grid = daily_grid
                self.scene.create_bubbles_visuals()
            except Exception as e:
                print(f"Daily grid error: {e}")

            if hasattr(self, 'drop_label'):
                remaining = daily_mgr.shots_left
                self.drop_label.setText(f"📅 SHOTS LEFT: {remaining}")

            self.scene.timer.start()
            self.scene.shot_timer.start(rush_mode=False)
            self.scene.game_timer.start()
            self.central_stack.setCurrentIndex(1)
            QTimer.singleShot(50, self._position_hud)
            daily_mgr.shots_remaining_changed.connect(self._on_daily_shots_changed)
        else:
            # No daily session started yet — start fresh
            self.start_daily_challenge()

    def _on_daily_shots_changed(self, remaining: int):
        if hasattr(self, 'drop_label'):
            self.drop_label.setText(f"📅 SHOTS LEFT: {remaining}")
        if remaining <= 0 and self.scene.daily_mode:
            # Time up — end daily challenge
            daily_mgr = get_daily_manager(self.save_dir)
            daily_mgr.on_timeout(self.scene.daily_shots, self.scene.game_timer.elapsed)
            self.scene.daily_mode = False
            self.show_game_over()

    # ── Replay ────────────────────────────────────────────────────────────────

    def _save_replay_after_session(self):
        """Called at game-over or back-to-menu to persist the replay."""
        try:
            recorder = self.scene.recorder
            recorder.stop()
            recorder.set_final_score(self.scene.score_mgr.score)
            recorder.set_level(self.scene.level)
            get_replay_manager(self.save_dir).save_replay(recorder)
        except Exception as e:
            print(f"Replay save error: {e}")

    def show_replay_list(self):
        """Show a simple dialog listing saved replays — pause game first."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
        was_active = self.scene.timer.isActive()
        if was_active:
            self.scene.timer.stop()
            self.scene.shot_timer.pause()
            self.scene.game_timer.pause()

        dlg = QDialog(self)
        dlg.setWindowTitle("Best Replays")
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dlg.setAttribute(Qt.WA_TranslucentBackground)
        dlg.setFixedSize(420, 480)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(10, 10, 10, 10)
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: #0a0e1a; border: 1px solid #1e2d45;
                     border-radius: 18px; }
        """)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(22, 22, 22, 18)
        vl.setSpacing(10)

        title = QLabel("🎬  BEST REPLAYS")
        title.setStyleSheet("color: #FFD700; font-size: 18px; font-weight: 900; border: none;")
        vl.addWidget(title)

        replays = get_replay_manager(self.save_dir).get_replays()
        if not replays:
            empty = QLabel("No replays saved yet.\nFinish a game session to record one.")
            empty.setStyleSheet("color: #64748b; font-size: 13px; padding: 20px;")
            empty.setAlignment(Qt.AlignCenter)
            vl.addWidget(empty)
        else:
            for i, r in enumerate(replays, 1):
                ts = r.get("timestamp", "")[:10]
                score = r.get("score", 0)
                level = r.get("level", 1)
                shots = r.get("shots", 0)
                row_lbl = QLabel(
                    f"#{i}  Score: {score:,}  ·  Lv.{level}  ·  "
                    f"{shots} shots  ·  {ts}"
                )
                row_lbl.setStyleSheet(
                    "color: #e2e8f0; font-size: 12px; border: none; "
                    "background: rgba(255,255,255,0.04); border-radius: 8px; padding: 8px;"
                )
                vl.addWidget(row_lbl)

        vl.addStretch()
        close_btn = QPushButton("✕  CLOSE")
        close_btn.setStyleSheet("""
            QPushButton { background: #1e293b; color: white; border-radius: 10px;
                          padding: 10px; font-weight: bold; border: none; }
            QPushButton:hover { background: #334155; }
        """)
        close_btn.clicked.connect(dlg.accept)
        vl.addWidget(close_btn)
        outer.addWidget(card)
        dlg.exec()

        if was_active:
            self.scene.timer.start()
            self.scene.shot_timer.resume()
            self.scene.game_timer.resume()

    def resizeEvent(self, event):
        """Trigger HUD repositioning on window resize."""
        super().resizeEvent(event)
        if hasattr(self, '_position_hud'):
            self._position_hud()

    def closeEvent(self, event):
        if self.central_stack.currentIndex() == 1:
            self.scene.shot_timer.stop()
            self.scene.game_timer.stop()
            self._save_replay_after_session()
            self.save_game()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
