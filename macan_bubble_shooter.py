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
                               QGraphicsRectItem, QDialog, QGraphicsDropShadowEffect, QStackedWidget, QCheckBox, QFrame, QGridLayout, QGraphicsTextItem)
from PySide6.QtCore import (Qt, QTimer, QPointF, QRectF, QPropertyAnimation, 
                            Signal, QObject, QEasingCurve, QVariantAnimation)
from PySide6.QtGui import (QColor, QPen, QBrush, QLinearGradient, QRadialGradient, 
                          QPainter, QPolygonF, QFont, QPainterPath, QIcon, QPalette)
from bubble_fx import get_sound_manager, play_shoot, play_burst, play_clear, play_combo, start_bgm
from bubble_power import (get_power_manager, PowerUpType, PowerUpBubble, 
                          PowerUpVisualEffect, try_spawn_powerup, 
                          add_powerup, use_powerup, get_all_powers_info)
from bubble_gfx import get_bubble_pixmap, get_launcher_pixmap, get_background_pixmap, has_custom_graphics, get_custom_cursor

# --- Game Configuration ---
BUBBLE_RADIUS = 22
ROWS = 14
COLS = 14
SHOTS_PER_DROP = 6  # CONFIG: Langit-langit turun setiap 6 tembakan (kena/tidak)

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
        self.anim = None # Simpan referensi animasi agar tidak di-garbage collect
        
    def setup_appearance(self):
        # === HANDLE RAINBOW BUBBLE (color_index = -1) ===
        if self.color_index == -1:
            # Buat gradien pelangi untuk rainbow bubble
            gradient = QRadialGradient(-self.radius_val * 0.3, -self.radius_val * 0.3, self.radius_val * 1.5)
            # Warna pelangi (Rainbow gradient)
            gradient.setColorAt(0, QColor(255, 255, 255))    # Putih terang di tengah
            gradient.setColorAt(0.2, QColor(255, 0, 0))      # Merah
            gradient.setColorAt(0.4, QColor(255, 255, 0))    # Kuning
            gradient.setColorAt(0.6, QColor(0, 255, 0))      # Hijau
            gradient.setColorAt(0.8, QColor(0, 0, 255))      # Biru
            gradient.setColorAt(1, QColor(255, 0, 255))      # Magenta
            
            self.setBrush(QBrush(gradient))
            self.setPen(QPen(QColor(255, 255, 255), 3))  # Border putih tebal
            
            # Tambahkan emoji/icon rainbow
            rainbow_text = QGraphicsTextItem("🌈", self)
            rainbow_text.setDefaultTextColor(Qt.white)
            font = QFont("Segoe UI Emoji", int(self.radius_val * 0.8), QFont.Bold)
            rainbow_text.setFont(font)
            text_rect = rainbow_text.boundingRect()
            rainbow_text.setPos(-text_rect.width()/2, -text_rect.height()/2)
            return
        
        # === LOGIC NORMAL (warna biasa) ===
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
        # PERBAIKAN: Menggunakan QVariantAnimation agar animasi pos lebih stabil di semua versi PySide
        if self.anim:
            self.anim.stop()
            
        self.anim = QVariantAnimation()
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPointF(x, y))
        self.anim.setDuration(500) # Durasi animasi 0.5 detik
        self.anim.setEasingCurve(QEasingCurve.OutBounce) # Efek memantul sedikit saat turun
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
        # === HANDLE RAINBOW ===
        if self.current_color == -1:
            # Gradien pelangi
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
        
        # === LOGIC NORMAL ===
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
                    # Indentasi hex yang benar
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
    power_collected = Signal(str)  # Emit saat dapat power
    power_used = Signal(str)        # Emit saat gunakan power
    power_updated = Signal()        # Emit saat ada perubahan power status
    game_over = Signal()
    
    def __init__(self):
        super().__init__()
        self.scene_width = 1200
        self.scene_height = 800        
        self.setSceneRect(0, 0, self.scene_width, self.scene_height)
        
        # --- PERBAIKAN DI SINI (Pindahkan Variabel ke Atas) ---
        self.score = 0
        self.high_score = 0
        self.level = 1  # Variabel ini harus ada sebelum setup_background dipanggil
        self.level_threshold = 1000
        # ------------------------------------------------------

        self.setup_background() # Sekarang aman dipanggil karena self.level sudah ada
        
        self.grid = BubbleGrid()
        self.bubbles = []
        self.shooter = Shooter()
        self.shooter.setPos(self.scene_width / 2, self.scene_height - 150)
        self.addItem(self.shooter)
        
        self.flying_bubble = None
        self.particles = []
        
        # (Baris inisialisasi score/level yang lama di sini sudah dipindah ke atas)
        
        # LOGIKA BARU: Drop setiap X tembakan
        self.shots_until_drop = SHOTS_PER_DROP 
        
        self.shooting = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)
        
        self.create_bubbles_visuals()    

        # Power Up
        self.power_manager = get_power_manager()
        self.active_power = None  # Power yang sedang aktif
        self.freeze_shots_remaining = 0  # Untuk freeze power
        
    def setup_background(self):
        self.bg_rect = QGraphicsRectItem(0, 0, self.scene_width, self.scene_height)
        self.bg_rect.setPen(Qt.NoPen)
        self.bg_rect.setZValue(-100)
        self.addItem(self.bg_rect)
        self.update_background_color()
    
    def update_background_color(self):
        """Update warna background berdasarkan level"""
        # Palette warna background untuk setiap level
        bg_colors = [
            # Level 1: Dark Green
            [(10, 30, 20), (5, 20, 15), (0, 10, 5)],
            # Level 2: Dark Blue
            [(10, 20, 40), (5, 15, 30), (0, 5, 20)],
            # Level 3: Dark Purple
            [(30, 10, 40), (20, 5, 30), (10, 0, 20)],
            # Level 4: Dark Red
            [(40, 10, 10), (30, 5, 5), (20, 0, 0)],
            # Level 5: Dark Orange
            [(40, 25, 10), (30, 15, 5), (20, 10, 0)],
            # Level 6+: Dark Teal (cycle)
            [(10, 40, 40), (5, 30, 30), (0, 20, 20)]
        ]
        
        # Pilih palet berdasarkan level (cycle jika lebih dari 6)
        color_idx = min(self.level - 1, len(bg_colors) - 1)
        colors = bg_colors[color_idx]
        
        gradient = QLinearGradient(0, 0, 0, self.scene_height)
        gradient.setColorAt(0, QColor(*colors[0]))
        gradient.setColorAt(0.5, QColor(*colors[1]))
        gradient.setColorAt(1, QColor(*colors[2]))
        self.bg_rect.setBrush(QBrush(gradient))
            
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

    def swap_shooter_bubble(self):
        if not self.shooting and not self.flying_bubble:
            self.shooter.swap_colors()
            self.next_bubble_changed.emit(self.shooter.next_color)
        
    def update_game(self):
        self.particles = [p for p in self.particles if p.update_particle()]
        
        if self.flying_bubble:
            new_x = self.flying_bubble.x() + self.bubble_vx
            new_y = self.flying_bubble.y() + self.bubble_vy
            
            if new_x - BUBBLE_RADIUS < 0 or new_x + BUBBLE_RADIUS > self.scene_width:
                self.bubble_vx *= -1
                new_x = self.flying_bubble.x() + self.bubble_vx
                
            self.flying_bubble.setPos(new_x, new_y)
            
            if new_y - BUBBLE_RADIUS < 0:
                self.attach_bubble()
                return

            for bubble in self.bubbles:
                if abs(bubble.y() - new_y) < BUBBLE_RADIUS * 2.5:
                    dx = new_x - bubble.x()
                    dy = new_y - bubble.y()
                    dist_sq = dx*dx + dy*dy
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

        # === TAMBAHAN BARU: HANDLE RAINBOW ===
        # Jika bubble yang ditembak adalah rainbow (-1), ubah jadi warna mayoritas tetangga
        if self.grid.grid[best_row][best_col] == -1:
            # Hitung warna tetangga terbanyak
            neighbors = self.grid.get_neighbors(best_row, best_col)
            color_counts = {}
            
            for nr, nc in neighbors:
                neighbor_color = self.grid.grid[nr][nc]
                if neighbor_color is not None and neighbor_color != -1:  # Ignore rainbow
                    color_counts[neighbor_color] = color_counts.get(neighbor_color, 0) + 1
            
            # Pilih warna mayoritas
            if color_counts:
                most_common_color = max(color_counts, key=color_counts.get)
                self.grid.grid[best_row][best_col] = most_common_color
                
                # Update visual bubble
                for bubble in self.bubbles:
                    if bubble.row == best_row and bubble.col == best_col:
                        bubble.color_index = most_common_color
                        bubble.setup_appearance()
                        break
        # === END RAINBOW HANDLING ===

        # === MODIFIKASI: Handle Power Effects ===
        if self.active_power == PowerUpType.BOMB:
        # Ledakkan area 3x3
            self.apply_bomb_effect(best_row, best_col)
            self.active_power = None
        
        elif self.active_power == PowerUpType.LASER:
            # Hancurkan 1 kolom
            self.apply_laser_effect(best_col)
            self.active_power = None
        
        elif self.active_power == PowerUpType.FIREBALL:
        # Ledakan besar
            self.apply_fireball_effect(best_row, best_col)
            self.active_power = None
    
        else:
            # Logic normal
            match_found = self.check_matches(best_row, best_col)
            if not match_found:
                self.check_and_drop_neighbors(best_row, best_col)
    
        # === UPDATE COOLDOWN ===
        self.power_manager.update_all_cooldowns()
        self.power_updated.emit()
    
        # Kurangi counter DROP (kecuali jika freeze aktif)
        if self.freeze_shots_remaining > 0:
            self.freeze_shots_remaining -= 1
            # Update UI Drop Counter (opsional: biar user tau lagi freeze)
            # self.drop_counter_changed.emit(self.shots_until_drop) 
        else:
            self.shots_until_drop -= 1
            self.drop_counter_changed.emit(self.shots_until_drop)
            
            # Jika counter habis, turunkan langit-langit
            if self.shots_until_drop <= 0:
                QTimer.singleShot(100, self.add_ceiling_row)
                self.shots_until_drop = SHOTS_PER_DROP
                self.drop_counter_changed.emit(self.shots_until_drop)       
        
        # Cek Matches dulu
        match_found = self.check_matches(best_row, best_col)
        
        # LOGIC BARU: Jika tidak ada match 3+, cek apakah ada bubble yang bisa jatuh
        if not match_found:
            self.check_and_drop_neighbors(best_row, best_col)
        
        # Kurangi counter setiap kali tembak
        #self.shots_until_drop -= 1
        #self.drop_counter_changed.emit(self.shots_until_drop)
        
        # Jika counter habis, turunkan langit-langit
        if self.shots_until_drop <= 0:
            QTimer.singleShot(100, self.add_ceiling_row)
            self.shots_until_drop = SHOTS_PER_DROP
            self.drop_counter_changed.emit(self.shots_until_drop)

        # Cek Game Over
        if self.check_game_over_condition():
            self.game_over.emit()

        # === PERBAIKAN UTAMA DI SINI ===
        # Reset flag shooting agar pemain bisa menembak lagi
        self.shooting = False 
        # ===============================

    # --- TAMBAHKAN FUNGSI HELPER BARU ---
    def apply_bomb_effect(self, center_row, center_col):
        """Ledakkan area 3x3 di sekitar center"""
        destroyed = []

        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = center_row + dr, center_col + dc
                if 0 <= r < len(self.grid.grid) and 0 <= c < len(self.grid.grid[r]):
                    if self.grid.grid[r][c] is not None:
                        destroyed.append((r, c))
                        self.grid.grid[r][c] = None
                        self.remove_bubble_visual(r, c)

        # Visual effect
        x, y = self.grid.get_position(center_row, center_col)
        # Pastikan PowerUpVisualEffect sudah di-import
        PowerUpVisualEffect.create_explosion_effect(
            self, x, y, BUBBLE_RADIUS * 3, QColor(255, 69, 0)
        )

        self.add_score(len(destroyed) * 15)
        play_burst()
        self.remove_floating_bubbles()

    def apply_laser_effect(self, col):
        """Hancurkan semua bubble di kolom"""
        destroyed = []
        for row in range(len(self.grid.grid)):
            # Cek range agar tidak error index out of bound
            if col < len(self.grid.grid[row]) and self.grid.grid[row][col] is not None:
                destroyed.append((row, col))
                self.grid.grid[row][col] = None
                self.remove_bubble_visual(row, col)

        # Visual effect
        x, _ = self.grid.get_position(0, col)
        PowerUpVisualEffect.create_laser_effect(
            self, x, 0, self.scene_height - 200, QColor(0, 255, 255)
        )

        self.add_score(len(destroyed) * 20)
        play_clear()
        self.remove_floating_bubbles()

    def apply_fireball_effect(self, center_row, center_col):
        """Ledakan besar 5x5"""
        destroyed = []

        for dr in range(-2, 3):
            for dc in range(-2, 3):
                r, c = center_row + dr, center_col + dc
                if 0 <= r < len(self.grid.grid) and 0 <= c < len(self.grid.grid[r]):
                    if self.grid.grid[r][c] is not None:
                        destroyed.append((r, c))
                        self.grid.grid[r][c] = None
                        self.remove_bubble_visual(r, c)

        # Visual effect
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
            self.high_score_changed.emit(self.high_score) # Update UI real-time
        self.score_changed.emit(self.score)
    # ------------------------------------

    def check_matches(self, row, col):
        color = self.grid.grid[row][col]
        matched = set()
        self.find_matching(row, col, color, matched)
        
        if len(matched) >= 3:
            play_clear()
            if len(matched) >= 6:
                play_combo()

                # === TAMBAHAN BARU: Try spawn power-up ===
            power_type = try_spawn_powerup(len(matched))
            if power_type:
                add_powerup(power_type)
                # Emit signal untuk update UI (akan dibuat nanti)
                self.power_collected.emit(power_type)  # Tambahkan signal ini
            # =========================================
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
        # 1. Cek Game Over sebelum geser
        if any(c is not None for c in self.grid.grid[ROWS-1]):
            self.game_over.emit()
            return

        # 2. Geser Logic Grid
        self.grid.grid.pop() 
        new_row = []
        for col in range(COLS):
            # Cek indentasi baris paling atas (akan jadi baris genap/ganjil)
            # Karena insert di 0, dia jadi baris 0 (genap)
            if col < COLS: 
                new_row.append(random.randint(0, len(BUBBLE_PALETTE) - 1))
            else:
                new_row.append(None)
        self.grid.grid.insert(0, new_row)

        # 3. Update Visual Bubble yang sudah ada (Geser Turun)
        for bubble in self.bubbles:
            bubble.row += 1
            new_x, new_y = self.grid.get_position(bubble.row, bubble.col)
            # Panggil animasi turun
            bubble.move_to_grid_pos(new_x, new_y)
            
        # 4. Buat Visual untuk Baris Baru
        for col in range(len(new_row)):
            if new_row[col] is not None:
                x, y = self.grid.get_position(0, col)
                bubble = Bubble(new_row[col], x, y)
                bubble.row = 0
                bubble.col = col
                # Mulai dari atas layar sedikit agar terlihat masuk
                bubble.setPos(x, y - BUBBLE_RADIUS*2)
                bubble.move_to_grid_pos(x, y)
                self.bubbles.append(bubble)
                self.addItem(bubble)

    def check_level_up(self):
        if self.score >= self.level_threshold * self.level:
            self.level += 1
            self.level_changed.emit(self.level)
            # Update background color saat naik level
            self.update_background_color()

    def find_matching(self, row, col, color, matched):
        if (row, col) in matched: 
            return
        
        cell_color = self.grid.grid[row][col]
        
        # Bubble tidak ada
        if cell_color is None:
            return
        
        # === HANDLE RAINBOW: Rainbow cocok dengan warna apapun ===
        # Jika target adalah rainbow ATAU cell adalah rainbow, anggap match
        if cell_color == color or cell_color == -1 or color == -1:
            matched.add((row, col))
            
            # Lanjutkan rekursi dengan warna asli (bukan rainbow)
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
        
        # Bonus untuk menjatuhkan banyak bubble sekaligus
        if dropped_count >= 3:
            play_combo()
            
        self.score_changed.emit(self.score)
    
    def check_and_drop_neighbors(self, impact_row, impact_col):
        """
        Cek bubble tetangga yang bisa jatuh karena kehilangan support.
        Logic: Bubble jatuh jika tidak ada koneksi ke langit-langit (baris 0)
        """
        # Dapatkan semua tetangga dari bubble yang baru menempel
        neighbors = self.grid.get_neighbors(impact_row, impact_col)
        
        # Untuk setiap tetangga, cek apakah masih connected ke langit-langit
        for nr, nc in neighbors:
            if self.grid.grid[nr][nc] is not None:
                # Cek apakah bubble ini masih connected ke top
                connected = set()
                for col in range(len(self.grid.grid[0])):
                    if self.grid.grid[0][col] is not None:
                        self.find_connected(0, col, connected)
                
                # Jika bubble tetangga tidak connected, jatuhkan
                if (nr, nc) not in connected:
                    # Jatuhkan bubble ini dan semua yang connected dengannya
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
        """
        Temukan semua bubble yang connected dengan bubble di (row, col)
        Berbeda dengan find_connected, ini tidak peduli dengan langit-langit
        """
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
        """Aktifkan power-up tertentu"""
        if not use_powerup(power_type):
            return False  # Tidak bisa digunakan

        self.active_power = power_type
        self.power_used.emit(power_type)

        if power_type == PowerUpType.FREEZE:
            self.freeze_shots_remaining = 5
            PowerUpVisualEffect.create_freeze_effect(self, self.sceneRect())
            play_combo()

        elif power_type == PowerUpType.RAINBOW:
            # Set bubble berikutnya jadi rainbow
            self.shooter.current_color = -1
            self.shooter.update_loaded_bubble_visual()
            # Reset active power karena rainbow langsung diload
            self.active_power = None
            play_combo()  # Sound effect

        # Power lain akan diproses saat tembak
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
        # Reset background color ke level 1
        self.update_background_color()

class GameView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
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
        if dy > 0:
            angle = math.degrees(math.atan2(dy, dx))
            self.scene_ref.shooter.set_angle(angle)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.scene_ref.shoot_bubble(self.scene_ref.shooter.angle)
        elif event.button() == Qt.RightButton:
            self.scene_ref.swap_shooter_bubble()

class WelcomeScreen(QWidget):
    def __init__(self, start_callback, load_callback, quit_callback, music_callback, sfx_callback, custom_cursor=None):
        super().__init__()

        print(f"🔍 DEBUG WelcomeScreen: Received cursor = {type(custom_cursor)}")
        print(f"🔍 DEBUG WelcomeScreen: cursor value = {custom_cursor}")
        # Store custom cursor
        self.custom_cursor = custom_cursor if custom_cursor else Qt.PointingHandCursor
        self.setup_ui(start_callback, load_callback, quit_callback, music_callback, sfx_callback)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setup_ui(start_callback, load_callback, quit_callback, music_callback, sfx_callback)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def setup_ui(self, start_cb, load_cb, quit_cb, music_cb, sfx_cb):
        if has_custom_graphics():
            bg_pixmap = get_background_pixmap(1920, 1080) 

            if bg_pixmap:
                palette = QPalette()
                palette.setBrush(QPalette.Window, QBrush(bg_pixmap))
                self.setPalette(palette)
                self.setAutoFillBackground(True)
            else:
            # Fallback stylesheet yang lebih spesifik agar tidak merusak tombol
                self.setStyleSheet("""
                    WelcomeScreen {
                        background: qradialgradient(cx:0.5, cy:0.5, radius: 1.0,
                            fx:0.5, fy:0.5, stop:0 #1e293b, stop:1 #020617);
                    }
                """)
        else:
            # Default gradient
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
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 30px;
                padding: 40px;
            }
        """)
        
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
        title.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI Black', 'Arial Black', sans-serif;
                font-size: 28px;
                font-weight: 900;
                color: #FFD700;
                background: transparent;
                margin-bottom: 10px;
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
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); max-height: 1px;")
        card_layout.addWidget(line)
        card_layout.addSpacing(10)

        # --- BUTTON STYLES ---
        # Kita menggunakan CSS modern dengan hover state
        btn_base_style = """
            QPushButton {
                color: white;
                border: none;
                border-radius: 25px; /* Pill Shape */
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
        
        # 1. Start Button (Orange/Gold Gradient)
        btn_start = QPushButton("🚀  NEW GAME")
        btn_start.setCursor(self.custom_cursor)
        print(f"🔍 DEBUG: btn_start cursor set to {btn_start.cursor()}")
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

        # 2. Load Button (Blue/Cyan Gradient)
        btn_load = QPushButton("💾  CONTINUE")
        btn_start.setCursor(self.custom_cursor)
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

        # 3. Quit Button (Red/Rose Gradient) - Sedikit lebih kecil/transparan
        btn_quit = QPushButton("EXIT GAME")
        btn_start.setCursor(self.custom_cursor)
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
                color: #94a3b8;
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
                background: #10b981; /* Emerald Green */
                border-color: #10b981;
            }
            QCheckBox:hover {
                color: white;
            }
        """

        self.music_toggle = QCheckBox("MUSIC")
        self.music_toggle.setChecked(True)
        self.music_toggle.setStyleSheet(checkbox_style)
        btn_start.setCursor(self.custom_cursor)
        self.music_toggle.toggled.connect(music_cb)

        self.sfx_toggle = QCheckBox("SOUND FX")
        self.sfx_toggle.setChecked(True)
        self.sfx_toggle.setStyleSheet(checkbox_style)
        btn_start.setCursor(self.custom_cursor)
        self.sfx_toggle.toggled.connect(sfx_cb)

        toggles_layout.addWidget(self.music_toggle)
        toggles_layout.addSpacing(30)
        toggles_layout.addWidget(self.sfx_toggle)

        card_layout.addSpacing(10)
        card_layout.addWidget(toggles_frame)
        
        # Version
        ver = QLabel("v3.0 Dynamic Edition")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color: rgba(255,255,255,0.2); font-size: 11px; margin-top: 10px; background: transparent;")
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


        # === SETUP CUSTOM CURSOR ===
        self.custom_cursor = get_custom_cursor()
        self.custom_hand_cursor = get_custom_cursor()  # Untuk button hover
        
        if self.custom_cursor:
            self.setCursor(self.custom_cursor)
            print("✅ Custom cursor loaded successfully!")
        else:
            # Fallback ke default cursor
            self.custom_cursor = Qt.CrossCursor
            self.custom_hand_cursor = Qt.PointingHandCursor
            self.setCursor(Qt.CrossCursor)
            print("⚠️ Using default cursors (cursor.png not found)")
        # ===========================
        
        # --- LOGIC SAVE DATA ---
        self.save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        # -------------------------------------

        # Sound Manager
        self.sound_manager = get_sound_manager()
        self.music_enabled = True
        self.sfx_enabled = True

        # --- SETUP STACKED WIDGET ---
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # 1. Setup Welcome Screen (Index 0)
        self.welcome_screen = WelcomeScreen(
            self.start_new_game,
            self.load_saved_game,
            self.close,
            self.toggle_music,
            self.toggle_sfx
        )
        self.central_stack.addWidget(self.welcome_screen)

        # 2. Setup Game Screen Container (Index 1)
        # Kita harus membuat container ini dulu agar bisa dimasukkan ke stack
        self.game_container = QWidget()
        self.setup_game_ui() # Fungsi ini akan mengisi self.game_container
        self.central_stack.addWidget(self.game_container)

        # === AUDIO START ===
        start_bgm()  # Mulai background music

        # Load High Score saja saat awal (Game data diload nanti lewat menu)
        self.load_high_score_data()
        
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

    def toggle_sfx(self, checked):
        self.sfx_enabled = checked
        # Catatan: Logic untuk mute SFX (shoot, burst) harus diimplementasikan
        # di file bubble_fx.py atau kita override fungsinya di sini jika memungkinkan.
        # Karena kita tidak punya akses ubah bubble_fx, kita simpan flag ini.
        # Idealnya: Kirim flag ini ke GameScene agar Scene tidak memanggil play_shoot()

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
        save_data = {
            'score': self.scene.score,
            'level': self.scene.level,
            'shots_until_drop': self.scene.shots_until_drop,
            'grid': self.scene.grid.grid,
            'shooter_current': self.scene.shooter.current_color,
            'shooter_next': self.scene.shooter.next_color
        }
        try:
            with open(self.save_dir / "save_v6.json", 'w') as f: json.dump(save_data, f)
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
                    
                    # Refresh UI
                    self.scene.score_changed.emit(self.scene.score)
                    self.scene.level_changed.emit(self.scene.level)
                    self.scene.drop_counter_changed.emit(self.scene.shots_until_drop)
                    self.scene.next_bubble_changed.emit(self.scene.shooter.next_color)
                    self.scene.update_background_color()
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
