import sys
import math
import random
import json
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                               QLabel, QVBoxLayout, QHBoxLayout, QGraphicsView, 
                               QGraphicsScene, QGraphicsEllipseItem, QGraphicsPolygonItem,
                               QGraphicsRectItem, QDialog, QDialogButtonBox)
from PySide6.QtCore import (Qt, QTimer, QPointF, QRectF, QPropertyAnimation, 
                            QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup,
                            Property, Signal, QObject)
from PySide6.QtGui import (QColor, QPen, QBrush, QLinearGradient, QRadialGradient, 
                          QPainter, QPolygonF, QPainterPath, QFont)

# Game Constants
BUBBLE_RADIUS = 25
BUBBLE_COLORS = [
    (255, 100, 100), (100, 255, 100), (100, 100, 255),
    (255, 255, 100), (255, 100, 255), (100, 255, 255)
]
ROWS = 10
COLS = 12
INITIAL_LIVES = 5

class Particle(QGraphicsEllipseItem):
    def __init__(self, x, y, color, scene):
        size = random.randint(3, 8)
        super().__init__(-size/2, -size/2, size, size)
        self.setPos(x, y)
        self.setBrush(QBrush(color))
        self.setPen(Qt.NoPen)
        
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-5, -2)
        self.life = 60
        self.scene_ref = scene
        scene.addItem(self)
        
    def update_particle(self):
        self.life -= 1
        if self.life <= 0:
            self.scene_ref.removeItem(self)
            return False
        
        self.setPos(self.x() + self.vx, self.y() + self.vy)
        self.vy += 0.2
        opacity = self.life / 60
        self.setOpacity(opacity)
        return True

class Bubble(QGraphicsEllipseItem):
    def __init__(self, color_index, x, y):
        super().__init__(-BUBBLE_RADIUS, -BUBBLE_RADIUS, 
                        BUBBLE_RADIUS * 2, BUBBLE_RADIUS * 2)
        self.color_index = color_index
        self.setPos(x, y)
        self.setup_appearance()
        self.matched = False
        self.row = 0
        self.col = 0
        
    def setup_appearance(self):
        color = QColor(*BUBBLE_COLORS[self.color_index])
        
        gradient = QRadialGradient(0, 0, BUBBLE_RADIUS)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(0.6, color)
        gradient.setColorAt(1, color.darker(120))
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(color.darker(150), 2))
        
    def highlight(self):
        self.setScale(1.15)
        
    def unhighlight(self):
        self.setScale(1.0)

class Shooter(QGraphicsPolygonItem):
    def __init__(self):
        super().__init__()
        self.angle = 90
        self.create_paw_shape()
        self.current_color = random.randint(0, len(BUBBLE_COLORS) - 1)
        self.next_color = random.randint(0, len(BUBBLE_COLORS) - 1)
        
    def create_paw_shape(self):
        # Tiger paw shape
        paw = QPolygonF([
            QPointF(0, -40), QPointF(-15, -25), QPointF(-20, -10),
            QPointF(-15, 5), QPointF(-5, 15), QPointF(5, 15),
            QPointF(15, 5), QPointF(20, -10), QPointF(15, -25)
        ])
        self.setPolygon(paw)
        
        gradient = QLinearGradient(0, -40, 0, 15)
        gradient.setColorAt(0, QColor(255, 140, 0))
        gradient.setColorAt(0.5, QColor(255, 165, 0))
        gradient.setColorAt(1, QColor(255, 120, 0))
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(QColor(139, 69, 19), 3))
        
    def set_angle(self, angle):
        self.angle = max(15, min(165, angle))
        self.setRotation(-self.angle + 90)

class BubbleGrid:
    def __init__(self):
        self.grid = []
        self.initialize_grid()
        
    def initialize_grid(self):
        self.grid = []
        for row in range(6):
            row_bubbles = []
            for col in range(COLS):
                if row % 2 == 1 and col == COLS - 1:
                    row_bubbles.append(None)
                else:
                    color = random.randint(0, len(BUBBLE_COLORS) - 1)
                    row_bubbles.append(color)
            self.grid.append(row_bubbles)
            
    def get_position(self, row, col):
        offset = BUBBLE_RADIUS if row % 2 == 1 else 0
        x = col * BUBBLE_RADIUS * 2 + BUBBLE_RADIUS + offset
        y = row * BUBBLE_RADIUS * 1.732 + BUBBLE_RADIUS
        return x, y
        
    def get_neighbors(self, row, col):
        neighbors = []
        directions = [(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]
        
        if row % 2 == 1:
            directions = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]
            
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if 0 <= nr < len(self.grid) and 0 <= nc < len(self.grid[nr]):
                if self.grid[nr][nc] is not None:
                    neighbors.append((nr, nc))
        return neighbors

class GameScene(QGraphicsScene):
    score_changed = Signal(int)
    lives_changed = Signal(int)
    level_changed = Signal(int)
    game_over = Signal()
    
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 1200, 800)
        self.setup_background()
        
        self.grid = BubbleGrid()
        self.bubbles = []
        self.shooter = Shooter()
        self.shooter.setPos(600, 750)
        self.addItem(self.shooter)
        
        self.flying_bubble = None
        self.particles = []
        
        self.score = 0
        self.lives = INITIAL_LIVES
        self.level = 1
        self.shooting = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)
        
        self.create_bubbles()
        
    def setup_background(self):
        # Dark jungle background
        bg = QGraphicsRectItem(0, 0, 1200, 800)
        gradient = QLinearGradient(0, 0, 0, 800)
        gradient.setColorAt(0, QColor(15, 40, 25))
        gradient.setColorAt(1, QColor(10, 25, 15))
        bg.setBrush(QBrush(gradient))
        bg.setPen(Qt.NoPen)
        bg.setZValue(-100)
        self.addItem(bg)
        
        # Add some decorative elements
        for _ in range(20):
            leaf = QGraphicsEllipseItem(random.randint(0, 1200), 
                                       random.randint(0, 800), 15, 25)
            leaf.setBrush(QBrush(QColor(34, 139, 34, 50)))
            leaf.setPen(Qt.NoPen)
            leaf.setZValue(-50)
            self.addItem(leaf)
            
    def create_bubbles(self):
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
            
        self.shooting = True
        color = self.shooter.current_color
        
        self.flying_bubble = Bubble(color, self.shooter.x(), self.shooter.y())
        self.addItem(self.flying_bubble)
        
        rad = math.radians(angle)
        self.bubble_vx = math.cos(rad) * 10
        self.bubble_vy = -math.sin(rad) * 10
        
        self.shooter.current_color = self.shooter.next_color
        self.shooter.next_color = random.randint(0, len(BUBBLE_COLORS) - 1)
        
    def update_game(self):
        # Update particles
        self.particles = [p for p in self.particles if p.update_particle()]
        
        # Update flying bubble
        if self.flying_bubble:
            new_x = self.flying_bubble.x() + self.bubble_vx
            new_y = self.flying_bubble.y() + self.bubble_vy
            
            # Wall collision
            if new_x - BUBBLE_RADIUS < 0 or new_x + BUBBLE_RADIUS > 1200:
                self.bubble_vx *= -1
                new_x = self.flying_bubble.x() + self.bubble_vx
                
            self.flying_bubble.setPos(new_x, new_y)
            
            # Check collision with bubbles
            for bubble in self.bubbles:
                dx = self.flying_bubble.x() - bubble.x()
                dy = self.flying_bubble.y() - bubble.y()
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist < BUBBLE_RADIUS * 1.8:
                    self.attach_bubble()
                    return
                    
            # Top collision
            if new_y - BUBBLE_RADIUS < 0:
                self.attach_bubble()
                
    def attach_bubble(self):
        if not self.flying_bubble:
            return
            
        # Find closest grid position
        min_dist = float('inf')
        best_row, best_col = 0, 0
        
        for row in range(len(self.grid.grid)):
            for col in range(len(self.grid.grid[row])):
                if self.grid.grid[row][col] is None:
                    x, y = self.grid.get_position(row, col)
                    dx = self.flying_bubble.x() - x
                    dy = self.flying_bubble.y() - y
                    dist = dx*dx + dy*dy
                    
                    if dist < min_dist:
                        min_dist = dist
                        best_row, best_col = row, col
                        
        # Place bubble
        self.grid.grid[best_row][best_col] = self.flying_bubble.color_index
        self.removeItem(self.flying_bubble)
        
        x, y = self.grid.get_position(best_row, best_col)
        new_bubble = Bubble(self.flying_bubble.color_index, x, y)
        new_bubble.row = best_row
        new_bubble.col = best_col
        self.bubbles.append(new_bubble)
        self.addItem(new_bubble)
        
        self.flying_bubble = None
        self.shooting = False
        
        # Check for matches
        self.check_matches(best_row, best_col)
        
        # Check game over
        if self.check_game_over():
            self.game_over.emit()
            
    def check_matches(self, row, col):
        color = self.grid.grid[row][col]
        matched = set()
        self.find_matching(row, col, color, matched)
        
        if len(matched) >= 3:
            points = len(matched) * 10
            if len(matched) >= 5:
                points *= 2
            self.score += points
            self.score_changed.emit(self.score)
            
            # Remove matched bubbles
            for r, c in matched:
                self.grid.grid[r][c] = None
                for bubble in self.bubbles[:]:
                    if bubble.row == r and bubble.col == c:
                        self.create_particles(bubble.x(), bubble.y(), 
                                            QColor(*BUBBLE_COLORS[bubble.color_index]))
                        self.bubbles.remove(bubble)
                        self.removeItem(bubble)
                        
            # Check for floating bubbles
            self.remove_floating_bubbles()
        else:
            self.lives -= 1
            self.lives_changed.emit(self.lives)
            if self.lives <= 0:
                self.game_over.emit()
                
    def find_matching(self, row, col, color, matched):
        if (row, col) in matched:
            return
        if self.grid.grid[row][col] != color:
            return
            
        matched.add((row, col))
        
        for nr, nc in self.grid.get_neighbors(row, col):
            self.find_matching(nr, nc, color, matched)
            
    def remove_floating_bubbles(self):
        connected = set()
        for col in range(len(self.grid.grid[0])):
            if self.grid.grid[0][col] is not None:
                self.find_connected(0, col, connected)
                
        for row in range(len(self.grid.grid)):
            for col in range(len(self.grid.grid[row])):
                if self.grid.grid[row][col] is not None and (row, col) not in connected:
                    self.grid.grid[row][col] = None
                    for bubble in self.bubbles[:]:
                        if bubble.row == row and bubble.col == col:
                            self.create_particles(bubble.x(), bubble.y(),
                                                QColor(*BUBBLE_COLORS[bubble.color_index]))
                            self.bubbles.remove(bubble)
                            self.removeItem(bubble)
                            self.score += 20
                    self.score_changed.emit(self.score)
                    
    def find_connected(self, row, col, connected):
        if (row, col) in connected:
            return
        if self.grid.grid[row][col] is None:
            return
            
        connected.add((row, col))
        
        for nr, nc in self.grid.get_neighbors(row, col):
            self.find_connected(nr, nc, connected)
            
    def create_particles(self, x, y, color):
        for _ in range(15):
            particle = Particle(x, y, color, self)
            self.particles.append(particle)
            
    def check_game_over(self):
        for bubble in self.bubbles:
            if bubble.y() > 700:
                return True
        return False
        
    def reset_game(self):
        self.grid.initialize_grid()
        self.create_bubbles()
        self.score = 0
        self.lives = INITIAL_LIVES
        self.level = 1
        self.shooting = False
        self.flying_bubble = None
        self.score_changed.emit(self.score)
        self.lives_changed.emit(self.lives)
        self.level_changed.emit(self.level)

class GameView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene_ref = scene
        
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macan Bubble Shooter")
        self.showFullScreen()
        
        self.save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.setup_ui()
        self.load_game()
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # HUD
        hud = QWidget()
        hud.setStyleSheet("""
            QWidget { background: rgba(20, 40, 30, 200); }
            QLabel { color: #FFD700; font-size: 20px; font-weight: bold; padding: 10px; }
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF8C00, stop:1 #FF6500);
                color: white; border: 2px solid #8B4513;
                border-radius: 5px; padding: 8px 15px;
                font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background: #FFA500; }
            QPushButton:pressed { background: #FF6500; }
        """)
        
        hud_layout = QHBoxLayout(hud)
        
        self.score_label = QLabel("Score: 0")
        self.level_label = QLabel("Level: 1")
        self.lives_label = QLabel("❤ Lives: 5")
        
        hud_layout.addWidget(self.score_label)
        hud_layout.addWidget(self.level_label)
        hud_layout.addWidget(self.lives_label)
        hud_layout.addStretch()
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.restart_btn = QPushButton("↻ Restart")
        self.quit_btn = QPushButton("✕ Quit")
        
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.restart_btn.clicked.connect(self.restart_game)
        self.quit_btn.clicked.connect(self.close)
        
        hud_layout.addWidget(self.pause_btn)
        hud_layout.addWidget(self.restart_btn)
        hud_layout.addWidget(self.quit_btn)
        
        layout.addWidget(hud)
        
        # Game view
        self.scene = GameScene()
        self.view = GameView(self.scene)
        layout.addWidget(self.view)
        
        self.scene.score_changed.connect(self.update_score)
        self.scene.lives_changed.connect(self.update_lives)
        self.scene.level_changed.connect(self.update_level)
        self.scene.game_over.connect(self.show_game_over)
        
    def update_score(self, score):
        self.score_label.setText(f"Score: {score}")
        
    def update_lives(self, lives):
        self.lives_label.setText(f"❤ Lives: {lives}")
        
    def update_level(self, level):
        self.level_label.setText(f"Level: {level}")
        
    def toggle_pause(self):
        if self.scene.timer.isActive():
            self.scene.timer.stop()
            self.pause_btn.setText("▶ Resume")
        else:
            self.scene.timer.start()
            self.pause_btn.setText("⏸ Pause")
            
    def restart_game(self):
        self.scene.reset_game()
        if not self.scene.timer.isActive():
            self.scene.timer.start()
            self.pause_btn.setText("⏸ Pause")
            
    def show_game_over(self):
        self.scene.timer.stop()
        dialog = QDialog(self)
        dialog.setWindowTitle("Game Over")
        dialog.setStyleSheet("""
            QDialog { background: #1a3a2a; }
            QLabel { color: #FFD700; font-size: 24px; font-weight: bold; }
            QPushButton { 
                background: #FF8C00; color: white;
                border: 2px solid #8B4513; border-radius: 5px;
                padding: 10px 20px; font-size: 18px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Game Over!\nFinal Score: {self.scene.score}"))
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        
        dialog.exec()
        self.restart_game()
        
    def save_game(self):
        save_data = {
            'score': self.scene.score,
            'lives': self.scene.lives,
            'level': self.scene.level,
            'grid': self.scene.grid.grid
        }
        
        save_file = self.save_dir / "save.json"
        with open(save_file, 'w') as f:
            json.dump(save_data, f)
            
    def load_game(self):
        save_file = self.save_dir / "save.json"
        if save_file.exists():
            try:
                with open(save_file, 'r') as f:
                    data = json.load(f)
                    self.scene.score = data['score']
                    self.scene.lives = data['lives']
                    self.scene.level = data['level']
                    self.scene.grid.grid = data['grid']
                    self.scene.create_bubbles()
                    self.update_score(self.scene.score)
                    self.update_lives(self.scene.lives)
                    self.update_level(self.scene.level)
            except:
                pass
                
    def closeEvent(self, event):
        self.save_game()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())