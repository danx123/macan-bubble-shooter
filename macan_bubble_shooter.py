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
        x = col * BUBBLE_RADIUS * 2 + BUBBLE_RADIUS + offset
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
    
    def __init__(self):
        super().__init__()
        self.scene_width = 1200
        self.scene_height = 800        
        self.setSceneRect(0, 0, self.scene_width, self.scene_height)
        
        self.score = 0
        self.high_score = 0
        self.level = 1
        self.level_threshold = 1000

        self.setup_background()
        
        self.grid = BubbleGrid()
        self.bubbles = []
        self.shooter = Shooter()
        self.shooter.setPos(self.scene_width / 2, self.scene_height - 150)
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
            
            # 4. Pantulan Dinding (Wall Bounce)
            if new_x - BUBBLE_RADIUS <= 0:
                self.bubble_vx = abs(self.bubble_vx)  # Pantul ke kanan
                new_x = BUBBLE_RADIUS
            elif new_x + BUBBLE_RADIUS >= self.scene_width:
                self.bubble_vx = -abs(self.bubble_vx)  # Pantul ke kiri
                new_x = self.scene_width - BUBBLE_RADIUS
                
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
        PowerUpVisualEffect.create_explosion_effect(
            self, x, y, BUBBLE_RADIUS * 3, QColor(255, 69, 0)
        )

        self.add_score(len(destroyed) * 15)
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
        PowerUpVisualEffect.create_laser_effect(
            self, x, 0, self.scene_height - 200, QColor(0, 255, 255)
        )

        self.add_score(len(destroyed) * 20)
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
        PowerUpVisualEffect.create_explosion_effect(
            self, x, y, BUBBLE_RADIUS * 5, QColor(255, 140, 0)
        )

        self.add_score(len(destroyed) * 25)
        play_combo()
        self.remove_floating_bubbles()

    def add_score(self, points):
        self.score += points
        if self.score > self.high_score:
            self.high_score = self.score
            self.high_score_changed.emit(self.high_score)
        self.score_changed.emit(self.score)

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
            
            points = len(matched) * 10 + (self.level * 5)
            self.add_score(points)
            self.score_changed.emit(self.score)
            
            for r, c in matched:
                self.grid.grid[r][c] = None
                self.remove_bubble_visual(r, c)
                        
            self.remove_floating_bubbles()
            self.check_level_up()
            return True
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
        if self.score >= self.level_threshold * self.level:
            self.level += 1
            self.level_changed.emit(self.level)
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
        for row in range(len(self.grid.grid)):
            for col in range(len(self.grid.grid[row])):
                if self.grid.grid[row][col] is not None and (row, col) not in connected:
                    self.grid.grid[row][col] = None
                    self.remove_bubble_visual(row, col)
                    self.add_score(20)
                    dropped_count += 1
        
        if dropped_count >= 3:
            play_combo()
            
        self.score_changed.emit(self.score)
    
    def check_and_drop_neighbors(self, impact_row, impact_col):
        neighbors = self.grid.get_neighbors(impact_row, impact_col)
        
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
                            self.grid.grid[dr][dc] = None
                            self.remove_bubble_visual(dr, dc)
                            self.add_score(20)
                    
                    if len(to_drop) >= 3:
                        play_combo()
                    
                    self.score_changed.emit(self.score)
    
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
            play_combo()

        elif power_type == PowerUpType.RAINBOW:
            self.shooter.current_color = -1
            self.shooter.update_loaded_bubble_visual()
            self.active_power = None
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
    
    # === AIM ASSIST METHODS ===
    def update_aim_line(self, angle):
        """Update garis aim dengan pantulan"""
        self.clear_aim_line()
        
        if self.shooting or self.flying_bubble:
            return
        
        rad = math.radians(angle)
        start_dist = 40
        start_x = self.shooter.x() + math.cos(rad) * start_dist
        start_y = self.shooter.y() - math.sin(rad) * start_dist
        
        dx = math.cos(rad)
        dy = -math.sin(rad)
        
        max_distance = 1000
        step = 5
        
        points = [(start_x, start_y)]
        current_x, current_y = start_x, start_y
        current_dx, current_dy = dx, dy
        bounced = False
        
        for _ in range(int(max_distance / step)):
            next_x = current_x + current_dx * step
            next_y = current_y + current_dy * step
            
            if next_x - BUBBLE_RADIUS <= 0:
                next_x = BUBBLE_RADIUS
                current_dx = abs(current_dx)
                bounced = True
            elif next_x + BUBBLE_RADIUS >= self.scene_width:
                next_x = self.scene_width - BUBBLE_RADIUS
                current_dx = -abs(current_dx)
                bounced = True
            
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
            # Gunakan DotLine agar lebih terlihat seperti guide game modern
            # Warna putih dengan transparansi 150 (sedikit lebih terang dari sebelumnya)
            pen = QPen(QColor(255, 255, 255, 150), 3, Qt.DotLine)
            
            for i in range(len(points) - 1):
                line = QGraphicsLineItem(points[i][0], points[i][1], 
                                        points[i+1][0], points[i+1][1])
                line.setPen(pen)
                line.setZValue(50) # Pastikan di atas background tapi di bawah UI
                self.addItem(line)
                
                if not self.aim_line:
                    self.aim_line = []
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
        
    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        shooter_pos = self.scene_ref.shooter.pos()
        dx = pos.x() - shooter_pos.x()
        dy = shooter_pos.y() - pos.y()
        
        # Batasi agar tidak error saat kursor sejajar/di bawah shooter
        if dy > 0:
            angle = math.degrees(math.atan2(dy, dx))
            # 1. Putar shooter
            self.scene_ref.shooter.set_angle(angle)
            # 2. Update garis aim (INI YANG HILANG SEBELUMNYA)
            self.scene_ref.update_aim_line(self.scene_ref.shooter.angle)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.scene_ref.shoot_bubble(self.scene_ref.shooter.angle)
        elif event.button() == Qt.RightButton:
            self.scene_ref.swap_shooter_bubble()

class WelcomeScreen(QWidget):      
    def __init__(self, start_callback, load_callback, quit_callback, music_callback, sfx_callback, custom_cursor=None, music_on=True, sfx_on=True):
        super().__init__()

        # --- LOGIC WALLPAPER BARU ---
        # Siapkan path gambar
        bg_path = Path(__file__).parent / "ui" / "bubble_bgn.webp"
        
        self.bg_pixmap = None
        if bg_path.exists():
            self.bg_pixmap = QPixmap(str(bg_path))
        else:
            print(f"⚠️ Wallpaper not found at: {bg_path}")
        # ----------------------------

        # Simpan status awal ke variabel class
        self.initial_music_on = music_on
        self.initial_sfx_on = sfx_on

        self.custom_cursor = custom_cursor if custom_cursor else Qt.PointingHandCursor
        self.setup_ui(start_callback, load_callback, quit_callback, music_callback, sfx_callback)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # JIKA GAMBAR ADA, PAKAI GAMBAR
        if self.bg_pixmap:
            # Menggambar gambar memenuhi layar (Stretch)
            painter.drawPixmap(self.rect(), self.bg_pixmap)
            
            # Opsional: Tambah lapisan hitam transparan biar teks lebih terbaca
            painter.fillRect(self.rect(), QColor(0, 0, 0, 80)) 
            
        else:
            # FALLBACK: Kalau gambar gak ketemu, pakai warna lama
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0.0, QColor("#0f172a"))
            grad.setColorAt(1.0, QColor("#1e293b"))
            painter.fillRect(self.rect(), grad)

    def setup_ui(self, start_cb, load_cb, quit_cb, music_cb, sfx_cb):
        if has_custom_graphics():
            bg_pixmap = get_background_pixmap(1920, 1080) 

            if bg_pixmap:
                palette = QPalette()
                palette.setBrush(QPalette.Window, QBrush(bg_pixmap))
                self.setPalette(palette)
                self.setAutoFillBackground(True)
            else:
                self.setStyleSheet("""
                    WelcomeScreen {
                        background: qradialgradient(cx:0.5, cy:0.5, radius: 1.0,
                            fx:0.5, fy:0.5, stop:0 #1e293b, stop:1 #020617);
                    }
                """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background: qradialgradient(cx:0.5, cy:0.5, radius: 1.0,
                        fx:0.5, fy:0.5, stop:0 #1e293b, stop:1 #020617);
                }
            """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- CONTAINER KARTU (GLASS EFFECT) ---
        card = QFrame()
        card.setFixedWidth(450)
        
        # --- PERBAIKAN DI SINI ---
        # 1. Kita beri nama ID khusus untuk kartu ini agar style tidak bocor ke anak-anaknya (Title/Footer)
        card.setObjectName("MainCard") 
        
        # 2. Ubah selector dari 'QFrame' menjadi '#MainCard' (hanya berlaku untuk kartu ini)
        card.setStyleSheet("""
            #MainCard {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 30px;
                padding: 40px;
            }
        """)
        # -------------------------
        
        # Efek Shadow pada kartu
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 15)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setAlignment(Qt.AlignCenter)

        # --- TITLE ---
        title = QLabel("MACAN\nBUBBLE SHOOTER")
        title.setAlignment(Qt.AlignCenter)
        # --- PERBAIKAN DI SINI: Tambahkan border: none; ---
        title.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI Black', 'Arial Black', sans-serif;
                font-size: 28px;
                font-weight: 900;
                color: #FFD700;
                background: transparent;
                margin-bottom: 10px;
                border: none; 
            }
        """)
        # Shadow Teks Emas
        text_shadow = QGraphicsDropShadowEffect()
        text_shadow.setBlurRadius(15)
        text_shadow.setColor(QColor(255, 215, 0, 120))
        text_shadow.setOffset(0, 0)
        title.setGraphicsEffect(text_shadow)
        
        card_layout.addWidget(title)

        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        # Pastikan garis ini tetap terlihat tapi tanpa border bawaan
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); max-height: 1px; border: none;")
        card_layout.addWidget(line)
        card_layout.addSpacing(10)

        # --- BUTTON STYLES ---
        btn_base_style = """
            QPushButton {
                color: white;
                border: none;
                border-radius: 25px;
                padding: 15px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:pressed {
                margin-top: 2px;
            }
        """
        
        # 1. Start Button
        btn_start = QPushButton("🚀  NEW GAME")
        btn_start.setCursor(self.custom_cursor)
        btn_start.setStyleSheet(btn_base_style + """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #d97706);
                border-bottom: 4px solid #b45309;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fbbf24, stop:1 #f59e0b);
                border-bottom: 4px solid #d97706;
            }
        """)
        btn_start.clicked.connect(start_cb)

        # 2. Load Button
        btn_load = QPushButton("💾  CONTINUE")
        btn_load.setCursor(self.custom_cursor)
        btn_load.setStyleSheet(btn_base_style + """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
                border-bottom: 4px solid #1d4ed8;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6);
            }
        """)
        btn_load.clicked.connect(load_cb)

        # 3. Quit Button
        btn_quit = QPushButton("EXIT GAME")
        btn_quit.setCursor(self.custom_cursor)
        btn_quit.setStyleSheet(btn_base_style + """
            QPushButton {
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.5);
                color: #fca5a5;
                font-size: 14px;
                padding: 12px;
                border-radius: 20px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.4);
                color: white;
            }
        """)
        btn_quit.clicked.connect(quit_cb)

        card_layout.addWidget(btn_start)
        card_layout.addWidget(btn_load)
        card_layout.addSpacing(10)
        card_layout.addWidget(btn_quit)

        # --- TOGGLES ROW ---
        toggles_frame = QFrame()
        toggles_frame.setStyleSheet("background: transparent; border: none;")
        toggles_layout = QHBoxLayout(toggles_frame)
        toggles_layout.setAlignment(Qt.AlignCenter)
        
        checkbox_style = """
            QCheckBox {
                color: white;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #475569;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background: #10b981;
                border-color: #10b981;
            }
            QCheckBox:hover {
                color: white;
            }
        """

        self.music_toggle = QCheckBox("MUSIC")
        self.music_toggle.setStyleSheet(checkbox_style)
        self.music_toggle.setCursor(self.custom_cursor)
        
        # === PERBAIKAN UTAMA DI SINI ===
        # Gunakan variabel self.initial_music_on, JANGAN True manual
        self.music_toggle.setChecked(self.initial_music_on) 
        self.music_toggle.toggled.connect(music_cb)

        self.sfx_toggle = QCheckBox("SOUND FX")
        self.sfx_toggle.setStyleSheet(checkbox_style)
        self.sfx_toggle.setCursor(self.custom_cursor)
        
        # Gunakan variabel self.initial_sfx_on
        self.sfx_toggle.setChecked(self.initial_sfx_on)
        self.sfx_toggle.toggled.connect(sfx_cb)
        # ===============================

        toggles_layout.addWidget(self.music_toggle)
        toggles_layout.addSpacing(30)
        toggles_layout.addWidget(self.sfx_toggle)

        card_layout.addSpacing(10)
        card_layout.addWidget(toggles_frame)
        
        # Version
        ver = QLabel("v4.0.0 Dynamic Edition")
        ver.setAlignment(Qt.AlignCenter)
        # --- PERBAIKAN DI SINI: Tambahkan border: none; ---
        ver.setStyleSheet("color: white; font-size: 12px; margin-top: 10px; background: transparent; border: none;")
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
        
        # 2. LOAD SETTINGS DATA (Variable Only)
        # Kita load dulu status on/off ke memory sebelum bikin UI
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
            # (Optional) Anda bisa memodifikasi WelcomeScreen untuk menerima status awal,
            # tapi cara di bawah (sync_ui_settings) lebih mudah tanpa ubah class lain.
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
        """Hanya memuat data JSON ke variabel self.music/sfx_enabled"""
        settings_path = self.save_dir / "settings.json"
        
        # Default Values
        self.music_enabled = True
        self.sfx_enabled = True

        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                    self.music_enabled = data.get('music_enabled', True)
                    self.sfx_enabled = data.get('sfx_enabled', True)
                print(f"📂 Loaded Settings: Music={self.music_enabled}, SFX={self.sfx_enabled}")
            except Exception as e:
                print(f"❌ Error reading settings file: {e}")
        else:
            print("⚠️ No settings file, using defaults (ON)")

    def sync_ui_with_settings(self):
        """Sinkronisasi Checkbox UI dengan variabel yang sudah di-load"""
        try:
            # Block signal agar tidak memicu toggle_music/sfx saat kita set status awal
            self.welcome_screen.music_toggle.blockSignals(True)
            self.welcome_screen.sfx_toggle.blockSignals(True)
            
            # Set Checkbox state
            self.welcome_screen.music_toggle.setChecked(self.music_enabled)
            self.welcome_screen.sfx_toggle.setChecked(self.sfx_enabled)
            
            # Unblock signal
            self.welcome_screen.music_toggle.blockSignals(False)
            self.welcome_screen.sfx_toggle.blockSignals(False)
        except Exception as e:
            print(f"⚠️ UI Sync Warning: {e}")

    def save_settings(self):
        """Simpan status saat ini ke JSON"""
        # Pastikan folder ada (safety check)
        if not self.save_dir.exists():
            try:
                self.save_dir.mkdir(parents=True, exist_ok=True)
            except:
                pass

        data = {
            'music_enabled': self.music_enabled,
            'sfx_enabled': self.sfx_enabled
        }
        
        try:
            with open(self.save_dir / "settings.json", 'w') as f:
                json.dump(data, f)
            print(f"💾 Settings Saved: {data}")
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
        """Membuat layout game (HUD + Scene View)"""
        # Background container game
        self.game_container.setStyleSheet("background-color: #05100a;")
    
        # Gunakan Stacked Layout agar HUD bisa "mengambang" di atas Game View
        # Namun untuk kemudahan, kita tetap pakai VBox tapi dengan style transparan
        main_layout = QVBoxLayout(self.game_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
    
        # --- HUD (HEADS UP DISPLAY) ---
        hud_container = QWidget()
        # Gradient transparan ke hitam agar teks terbaca tapi tidak menutupi game total
        hud_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,0.8), stop:1 rgba(0,0,0,0));
            }
        """)
        hud_container.setFixedHeight(80) # Tinggi fix
    
        hud_layout = QHBoxLayout(hud_container)
        hud_layout.setContentsMargins(20, 10, 20, 20)
        hud_layout.setSpacing(10)

        # Style untuk "Pills" (Kotak informasi)
        pill_style = """
            QLabel {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 15px;
                padding: 5px 15px;
                color: white;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 14px;
            }
        """

        # Label Components dengan HTML formatting untuk warna ganda
        self.high_score_label = QLabel("🏆 BEST <span style='color:#00FF00;'>0</span>")
        self.high_score_label.setStyleSheet(pill_style)
    
        self.score_label = QLabel("💎 SCORE <span style='color:#FFD700;'>0</span>")
        self.score_label.setStyleSheet(pill_style)
    
        self.level_label = QLabel("⚡ LEVEL <span style='color:#00ffff;'>1</span>")
        self.level_label.setStyleSheet(pill_style)
    
        self.drop_label = QLabel(f"💀 DROP <span style='color:#ff4757;'>{SHOTS_PER_DROP}</span>")
        self.drop_label.setStyleSheet(pill_style)
    
        hud_layout.addWidget(self.high_score_label)
        hud_layout.addWidget(self.score_label)
        hud_layout.addWidget(self.level_label)
        hud_layout.addWidget(self.drop_label)
    
        hud_layout.addStretch()
    
        # --- POWER PANEL (SEJAJAR DENGAN HUD) ---
        power_panel = self.create_power_panel()
        hud_layout.addWidget(power_panel)
    
        hud_layout.addSpacing(20)
    
        # --- CONTROL BUTTONS (Small & Iconic) ---
        btn_control_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                color: #e2e8f0;
                font-weight: bold;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
                border-color: white;
            }
        """
    
        #self.pause_btn = QPushButton("⏸ PAUSE")
        #self.pause_btn.setStyleSheet(btn_control_style)
        #self.pause_btn.setCursor(Qt.PointingHandCursor)
        #self.pause_btn.clicked.connect(self.toggle_pause)

        self.menu_btn = QPushButton("🏠 MENU")
        self.menu_btn.setStyleSheet(btn_control_style)
        self.menu_btn.setCursor(self.custom_cursor)
        self.menu_btn.clicked.connect(self.back_to_menu)
    
        #hud_layout.addWidget(self.pause_btn)
        hud_layout.addWidget(self.menu_btn)
    
        main_layout.addWidget(hud_container)
    
        # --- SCENE & VIEW ---
        self.scene = GameScene()
        self.view = GameView(self.scene)
        main_layout.addWidget(self.view)
    
        # Connect Signals
        self.scene.score_changed.connect(self.update_score)
        self.scene.drop_counter_changed.connect(self.update_drop_counter)
        self.scene.level_changed.connect(self.update_level)
        self.scene.game_over.connect(self.show_game_over)
        self.scene.next_bubble_changed.connect(self.update_next_bubble_ui)
        self.scene.high_score_changed.connect(self.update_high_score)
        self.scene.power_collected.connect(self.on_power_collected)
        self.scene.power_updated.connect(self.update_all_power_buttons)

        # Stop timer initially
        self.scene.timer.stop()
    
    def start_new_game(self):
        """Memulai game baru dari nol"""
        self.scene.reset_game()
        self.scene.timer.start()
        self.central_stack.setCurrentIndex(1) # Pindah ke halaman game
        # Load high score saja
        self.load_high_score_data()

    def load_saved_game(self):
        """Load game dari file"""
        self.load_game_data() # Memanggil logika load JSON
        self.scene.timer.start()
        self.central_stack.setCurrentIndex(1) # Pindah ke halaman game

    def back_to_menu(self):
        """Kembali ke menu utama, pause game dan simpan"""
        self.scene.timer.stop()
        self.save_game() # Auto save saat kembali ke menu
        self.central_stack.setCurrentIndex(0)
        #self.pause_btn.setText("⏸ PAUSE") # Reset tombol pause

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
        # === POWER UPS CONTAINER ===
        # Kita buat container (Frame) untuk membungkus tombol-tombol
        power_frame = QFrame()
        power_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        # Style transparan tapi ada border halus
        power_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        
        # --- LAYOUT PILIHAN: GRID (KOTAK) ---
        # Menggunakan Grid agar tersusun rapi (misal 5 kolom ke samping, atau 2 baris)
        # Jika ingin memanjang ke samping (sejajar 1 baris), ganti QGridLayout dengan QHBoxLayout
        power_layout = QHBoxLayout(power_frame) 
        power_layout.setSpacing(3)
        power_layout.setContentsMargins(5, 3, 5, 3)
        power_layout.setAlignment(Qt.AlignCenter) # Tengah

        # Label Judul Kecil (Optional - bisa dihapus jika ingin lebih ringkas)
        lbl_power = QLabel("SKILLS:")
        lbl_power.setStyleSheet("font-weight: bold; color: #FFD700; margin-right: 5px;")
        power_layout.addWidget(lbl_power)

        self.power_buttons = {}
        manager = get_power_manager()
        
        # Daftar Power Up
        power_types = [
            PowerUpType.BOMB, 
            PowerUpType.LASER, 
            PowerUpType.RAINBOW, 
            PowerUpType.FIREBALL,
            PowerUpType.FREEZE
        ]

        for p_type in power_types:
            info = manager.get_power_info(p_type)
            # Ambil nama pendek
            full_desc = manager.get_power_description(p_type)
            # Format Text: Nama (atas) Jumlah (bawah)
            name_only = full_desc.split('\n')[0].replace(" ", "") # Hapus spasi biar pendek
            btn_text = f"{name_only}\n{info['charges']}"
            
            btn = QPushButton(btn_text)
            btn.setCursor(self.custom_hand_cursor)
            btn.setFixedSize(65, 42)  # Ukuran tombol fix agar seragam
            
            # Hubungkan klik tombol
            # Gunakan lambda dengan checked=False agar p_type terikat benar
            btn.clicked.connect(lambda checked=False, t=p_type: self.activate_powerup(t))
            
            # Style tombol default (abu-abu jika 0)
            self.update_power_button_style(btn, p_type)
            
            self.power_buttons[p_type] = btn
            
            # Masukkan ke Layout
            power_layout.addWidget(btn)
            
        # PENTING: Kembalikan frame ini ke setup_game_ui
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
        if info and info['can_use']:
            btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: 2px solid #34d399;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #34d399; }
            """)
        else:
            btn.setStyleSheet("""
            QPushButton {
                background: rgba(100,100,100,0.3);
                color: #64748b;
                border: 1px solid #475569;
                border-radius: 10px;
            }
        """)

    def update_next_bubble_ui(self, color_idx):
        """Update tampilan bubble berikutnya (Preview)"""
        # Hapus indikator lama jika ada
        if hasattr(self, 'next_bubble_indicator'):
            self.scene.removeItem(self.next_bubble_indicator)
            self.scene.removeItem(self.next_text_item)
            
        # --- POSISI BARU YANG LEBIH TINGGI ---
        # Kita samakan ketinggiannya (Y) dengan area shooter agar sejajar
        # scene_height - 150 (sama dengan shooter)
        base_y = self.scene.scene_height - 150 
        base_x = 100  # Geser sedikit ke kanan dari pojok kiri (sebelumnya 60)

        # 1. Setup Text Label
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.next_text_item = self.scene.addText("NEXT", font)
        self.next_text_item.setDefaultTextColor(QColor("#a0aec0")) # Warna abu terang
        
        # Posisikan teks sedikit di atas bolanya
        # boundingRect().width() digunakan agar teks berada di tengah relatif terhadap bola
        text_width = self.next_text_item.boundingRect().width()
        self.next_text_item.setPos(base_x - (text_width / 2), base_y + 30)
        
        # 2. Setup Bubble Preview
        # is_preview=True membuat ukurannya sedikit lebih kecil (0.8x)
        self.next_bubble_indicator = Bubble(color_idx, base_x, base_y, is_preview=True)
        
        # Tambahkan efek glow/shadow agar terlihat premium
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.next_bubble_indicator.setGraphicsEffect(shadow)

        self.scene.addItem(self.next_bubble_indicator)

    def on_power_collected(self, power_type):
        """Slot saat player mendapatkan power-up"""
        # Update tampilan tombol karena charges bertambah
        self.update_all_power_buttons()
        
        # Optional: Flash effect pada tombol yang bertambah (bisa ditambahkan nanti)

    def update_all_power_buttons(self):
        """Refresh text dan style semua tombol power"""
        manager = get_power_manager()
        
        # Pastikan self.power_buttons sudah ada
        if not hasattr(self, 'power_buttons'):
            return

        for p_type, btn in self.power_buttons.items():
            info = manager.get_power_info(p_type)
            if info:
                # 1. Ambil Nama Power (Parsing dari deskripsi)
                # Format deskripsi di bubble_power.py: "💣 BOMB\n..."
                desc = manager.get_power_description(p_type)
                # Ambil baris pertama, misal: "💣 BOMB"
                header = desc.split('\n')[0] 
                # Hapus emoji jika ingin lebih bersih, atau biarkan saja
                # Kita set text button: "NAMA\nJUMLAH"
                btn.setText(f"{header}\n{info['charges']}")
                
                # 2. Update Style (Warna hijau jika bisa dipakai, abu jika tidak)
                self.update_power_button_style(btn, p_type)

    # --- UI UPDATE SLOT ---
    def update_high_score(self, val):
        self.high_score_label.setText(f"🏆 BEST <span style='color:#00FF00;'>{val}</span>")
        self.save_high_score_data()

    def update_score(self, score):
        self.score_label.setText(f"💎 SCORE <span style='color:#FFD700;'>{score}</span>")
        
    def update_level(self, level):
        self.level_label.setText(f"⚡ LEVEL <span style='color:#00ffff;'>{level}</span>")

    def update_drop_counter(self, count):
        # Menggunakan simbol yang lebih bersih
        balls = "● " * count
        empty = "○ " * (SHOTS_PER_DROP - count)
        self.drop_label.setText(f"💀 DROP <span style='color:#ff4757;'>{balls}</span>")
        
    def toggle_pause(self):
        if self.scene.timer.isActive():
            self.scene.timer.stop()
            self.pause_btn.setText("▶ RESUME")            
            self.sound_manager.pause_bgm()
        else:
            self.scene.timer.start()
            self.pause_btn.setText("⏸ PAUSE")
            if self.music_enabled:
                self.sound_manager.resume_bgm()
            
    def show_game_over(self):
        self.scene.timer.stop()
        self.save_high_score_data()
        
        # === PERBAIKAN: JANGAN HAPUS SAVE FILE ===
        # Save file tetap dipertahankan agar bisa continue
        # Hanya hapus jika pemain memilih "New Game" dari menu
        # save_file = self.save_dir / "save_v6.json"
        # if save_file.exists():
        #     try: save_file.unlink()
        #     except: pass
        # ==========================================
        
        # Setup Dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Game Over")
        dialog.setFixedSize(400, 420)
        dialog.setWindowFlags(Qt.FramelessWindowHint)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        
        # Layout Utama Dialog
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Frame Konten (Container Utama)
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 2px solid #334155;
                border-radius: 25px;
            }
        """)
        
        # Shadow Effect untuk pop-up
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0,0,0,200))
        shadow.setOffset(0, 10)
        content_frame.setGraphicsEffect(shadow)
        
        inner_layout = QVBoxLayout(content_frame)
        inner_layout.setSpacing(5)
        inner_layout.setContentsMargins(30, 40, 30, 40)
        
        # --- 1. TITLE ---
        title = QLabel("GAME OVER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            border: none;
            font-family: 'Segoe UI Black', Arial;
            font-size: 36px; 
            font-weight: 900; 
            color: #ef4444;
            margin-bottom: 10px;
        """)
        inner_layout.addWidget(title)
        
        # --- 2. STATS CONTAINER (Kotak Nilai) ---
        stats_box = QFrame()
        stats_box.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        stats_layout = QVBoxLayout(stats_box)
        stats_layout.setSpacing(2)
        stats_layout.setContentsMargins(0, 15, 0, 15)

        # Level Label
        lbl_lvl = QLabel(f"LEVEL {self.scene.level}")
        lbl_lvl.setAlignment(Qt.AlignCenter)
        lbl_lvl.setStyleSheet("border: none; color: #94a3b8; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        
        # Score Label (Angka Besar)
        lbl_score = QLabel(f"{self.scene.score}")
        lbl_score.setAlignment(Qt.AlignCenter)
        lbl_score.setStyleSheet("border: none; color: #fbbf24; font-size: 48px; font-weight: 900; margin: 5px 0;")
        
        # High Score Label
        lbl_best = QLabel(f"BEST SCORE: {self.scene.high_score}")
        lbl_best.setAlignment(Qt.AlignCenter)
        lbl_best.setStyleSheet("border: none; color: #38bdf8; font-size: 14px; font-weight: bold;")

        stats_layout.addWidget(lbl_lvl)
        stats_layout.addWidget(lbl_score)
        stats_layout.addWidget(lbl_best)
        
        inner_layout.addWidget(stats_box)
        inner_layout.addSpacing(20)
        
        # --- 3. BUTTONS ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        btn_style = """
            QPushButton {
                border-radius: 10px;
                padding: 10px;
                font-family: 'Segoe UI';
                font-weight: bold;
                font-size: 12px;
                color: white;
                border: none;
            }
            QPushButton:pressed { margin-top: 2px; }
        """
        
        # === PERBAIKAN: Tombol Continue (Bukan Try Again) ===
        continue_btn = QPushButton("↺ CONTINUE")
        continue_btn.setCursor(self.custom_hand_cursor)
        continue_btn.setStyleSheet(btn_style + """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                border-bottom: 3px solid #047857;
            }
            QPushButton:hover { background: #34d399; }
        """)
        
        # Tombol New Game (Merah)
        new_game_btn = QPushButton("🆕 NEW GAME")
        new_game_btn.setCursor(self.custom_hand_cursor)
        new_game_btn.setStyleSheet(btn_style + """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #dc2626);
                border-bottom: 3px solid #b91c1c;
            }
            QPushButton:hover { background: #f87171; }
        """)
        
        # Tombol Menu (Abu-abu)
        menu_btn = QPushButton("🏠 MENU")
        menu_btn.setCursor(self.custom_cursor)
        menu_btn.setStyleSheet(btn_style + """
            QPushButton {
                background-color: #475569;
                border-bottom: 3px solid #334155;
            }
            QPushButton:hover { background-color: #64748b; }
        """)
        
        # === CONNECT BUTTONS ===
        # Continue: Load game terakhir (dari save file)
        continue_btn.clicked.connect(lambda: [dialog.accept(), self.continue_from_save()])
        
        # New Game: Hapus save dan mulai fresh
        new_game_btn.clicked.connect(lambda: [dialog.accept(), self.start_new_game_fresh()])
        
        # Menu: Kembali ke menu utama
        menu_btn.clicked.connect(lambda: [dialog.accept(), self.back_to_menu()])
        
        btn_layout.addWidget(continue_btn)
        btn_layout.addWidget(new_game_btn)
        btn_layout.addWidget(menu_btn)
        
        inner_layout.addLayout(btn_layout)
        
        layout.addWidget(content_frame)
        dialog.exec()


# ============================================
# TAMBAHKAN 2 METHOD BARU di MainWindow
# ============================================
# Letakkan SEBELUM method closeEvent() (sekitar baris 1250)

    def continue_from_save(self):
        """Load game dari save terakhir dan lanjutkan"""
        # Load game dari file
        self.load_game_data()
        
        # Mulai timer
        self.scene.timer.start()
        
        # Pastikan di halaman game
        self.central_stack.setCurrentIndex(1)


    def start_new_game_fresh(self):
        """Mulai game baru dari nol (hapus save)"""
        # Hapus save file
        save_file = self.save_dir / "save_v6.json"
        if save_file.exists():
            try:
                save_file.unlink()
            except Exception as e:
                print(f"Error deleting save: {e}")
        
        # Reset game
        self.scene.reset_game()
        self.scene.timer.start()
        self.central_stack.setCurrentIndex(1)

    # --- UI UPDATES & HELPER ---
    
    def update_next_bubble_ui(self, color_idx):
        """Update tampilan bubble berikutnya (Preview)"""
        # Hapus indikator lama jika ada
        if hasattr(self, 'next_bubble_indicator'):
            self.scene.removeItem(self.next_bubble_indicator)
            self.scene.removeItem(self.next_text_item)
            
        # --- POSISI BARU YANG LEBIH TINGGI ---
        # Kita samakan ketinggiannya (Y) dengan area shooter agar sejajar
        # scene_height - 150 (sama dengan shooter)
        base_y = self.scene.scene_height - 150 
        base_x = 100  # Geser sedikit ke kanan dari pojok kiri (sebelumnya 60)

        # 1. Setup Text Label
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.next_text_item = self.scene.addText("NEXT", font)
        self.next_text_item.setDefaultTextColor(QColor("#a0aec0")) # Warna abu terang
        
        # Posisikan teks sedikit di atas bolanya
        # boundingRect().width() digunakan agar teks berada di tengah relatif terhadap bola
        text_width = self.next_text_item.boundingRect().width()
        self.next_text_item.setPos(base_x - (text_width / 2), base_y + 30)
        
        # 2. Setup Bubble Preview
        # is_preview=True membuat ukurannya sedikit lebih kecil (0.8x)
        self.next_bubble_indicator = Bubble(color_idx, base_x, base_y, is_preview=True)
        
        # Tambahkan efek glow/shadow agar terlihat premium
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.next_bubble_indicator.setGraphicsEffect(shadow)

        self.scene.addItem(self.next_bubble_indicator)

    def update_high_score(self, val):
        self.high_score_label.setText(f"🏆 BEST: {val}")
        self.save_high_score_data()

    def update_score(self, score):
        self.score_label.setText(f"💎 SCORE: {score}")
        
    def update_drop_counter(self, count):
        balls = "⚫" * count
        empty = "⚪" * (SHOTS_PER_DROP - count)
        self.drop_label.setText(f"💀 DROP IN: {balls}{empty}")
        
    def update_level(self, level):
        self.level_label.setText(f"⚡ LEVEL: {level}")

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
        
        # 1. Ambil data Power Up saat ini
        power_manager = get_power_manager()
        power_data = {}
        
        # Loop semua power yang ada di manager dan simpan jumlah charges-nya
        for p_type, p_obj in power_manager.powers.items():
            power_data[p_type] = p_obj.charges

        save_data = {
            'score': self.scene.score,
            'level': self.scene.level,
            'shots_until_drop': self.scene.shots_until_drop,
            'grid': self.scene.grid.grid,
            'shooter_current': self.scene.shooter.current_color,
            'shooter_next': self.scene.shooter.next_color,
            'powerups': power_data  # <--- INI BAGIAN PENTING YANG DITAMBAHKAN
        }
        
        try:
            with open(self.save_dir / "save_v6.json", 'w') as f: json.dump(save_data, f)
            print("✅ Game Saved with Skills!")
        except Exception as e: print(f"Save Fail: {e}")

    def load_game_data(self):
        # Load High Score dulu
        self.load_high_score_data()
        
        save_file = self.save_dir / "save_v6.json"
        if save_file.exists():
            try:
                with open(save_file, 'r') as f:
                    data = json.load(f)
                    self.scene.score = data.get('score', 0)
                    self.scene.level = data.get('level', 1)
                    self.scene.shots_until_drop = data.get('shots_until_drop', SHOTS_PER_DROP)
                    
                    if 'grid' in data:
                        self.scene.grid.grid = data['grid']
                        self.scene.create_bubbles_visuals()
                    
                    self.scene.shooter.current_color = data.get('shooter_current', 0)
                    self.scene.shooter.next_color = data.get('shooter_next', 1)
                    self.scene.shooter.update_loaded_bubble_visual()
                    
                    # === FIX: LOAD POWER UPS / SKILLS ===
                    if 'powerups' in data:
                        power_manager = get_power_manager()
                        saved_powers = data['powerups']
                        
                        # Reset dan Update charges sesuai save file
                        for p_type, count in saved_powers.items():
                            if p_type in power_manager.powers:
                                power_manager.powers[p_type].charges = count
                        
                        # Update tampilan tombol di UI (Agar angka di tombol berubah)
                        self.update_all_power_buttons()
                    # ====================================

                    # Refresh UI Scene
                    self.scene.score_changed.emit(self.scene.score)
                    self.scene.level_changed.emit(self.scene.level)
                    self.scene.drop_counter_changed.emit(self.scene.shots_until_drop)
                    self.scene.next_bubble_changed.emit(self.scene.shooter.next_color)
                    self.scene.update_background_color()
                    
                    print("✅ Game Loaded Successfully!")
                    
            except Exception as e:
                print(f"Load Fail: {e}")
                self.start_new_game() # Fallback jika file rusak
        else:
            self.start_new_game()    
           
    def closeEvent(self, event):
        # Hanya auto-save jika sedang di dalam game (index 1)
        if self.central_stack.currentIndex() == 1:
            self.save_game()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())