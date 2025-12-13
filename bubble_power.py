"""
bubble_power.py - Power-Up System untuk Macan Bubble Shooter
Modul untuk mengelola berbagai power-up yang membantu pemain
"""

from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsRectItem
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPen, QBrush, QRadialGradient, QFont, QPainterPath
import random
import math

class PowerUpType:
    """Enum-like class untuk tipe power-up"""
    BOMB = "bomb"           # Meledakkan area 3x3
    LASER = "laser"         # Tembakan laser vertikal
    RAINBOW = "rainbow"     # Bubble rainbow (cocok dengan warna apapun)
    FIREBALL = "fireball"   # Tembakan yang menembus dan meledak
    FREEZE = "freeze"       # Freeze drop counter untuk 5 tembakan
    
class PowerUp:
    """
    Base class untuk semua power-up.
    Setiap power-up memiliki cooldown dan durasi.
    """
    def __init__(self, power_type, cooldown=10):
        self.type = power_type
        self.cooldown = cooldown  # Berapa tembakan hingga bisa digunakan lagi
        self.current_cooldown = 0
        self.active = False
        self.charges = 0  # Jumlah charges tersedia
        
    def can_use(self):
        """Cek apakah power bisa digunakan"""
        return self.charges > 0 and self.current_cooldown == 0
    
    def use(self):
        """Gunakan power"""
        if self.can_use():
            self.charges -= 1
            self.current_cooldown = self.cooldown
            self.active = True
            return True
        return False
    
    def update_cooldown(self):
        """Update cooldown setiap tembakan"""
        if self.current_cooldown > 0:
            self.current_cooldown -= 1
    
    def add_charge(self, amount=1):
        """Tambah charge"""
        self.charges += amount

class PowerUpManager:
    """
    Manager untuk mengelola semua power-up dalam game.
    Handles spawning, activation, dan visual effects.
    """
    
    def __init__(self):
        # Dictionary untuk menyimpan semua power-up yang tersedia
        self.powers = {
            PowerUpType.BOMB: PowerUp(PowerUpType.BOMB, cooldown=8),
            PowerUpType.LASER: PowerUp(PowerUpType.LASER, cooldown=10),
            PowerUpType.RAINBOW: PowerUp(PowerUpType.RAINBOW, cooldown=6),
            PowerUpType.FIREBALL: PowerUp(PowerUpType.FIREBALL, cooldown=12),
            PowerUpType.FREEZE: PowerUp(PowerUpType.FREEZE, cooldown=15),
        }
        
        # Visual indicators untuk power-up
        self.power_icons = {}
        
        # Chance untuk drop power-up setelah match (dalam persen)
        self.drop_chance = 15  # 15% chance per match 3+
        
    def update_all_cooldowns(self):
        """Update cooldown semua power setiap tembakan"""
        for power in self.powers.values():
            power.update_cooldown()
    
    def try_drop_powerup(self, match_size):
        """
        Coba drop power-up berdasarkan ukuran match.
        Semakin besar match, semakin besar chance.
        
        Args:
            match_size: Jumlah bubble yang match
            
        Returns:
            PowerUpType atau None
        """
        if match_size < 3:
            return None
        
        # Bonus chance untuk match besar
        adjusted_chance = self.drop_chance + (match_size - 3) * 5
        adjusted_chance = min(adjusted_chance, 50)  # Max 50%
        
        if random.randint(1, 100) <= adjusted_chance:
            # Random power-up
            power_type = random.choice(list(PowerUpType.__dict__.values()))
            if isinstance(power_type, str) and not power_type.startswith('_'):
                return power_type
        
        return None
    
    def add_powerup_charge(self, power_type):
        """Tambah charge untuk power-up tertentu"""
        if power_type in self.powers:
            self.powers[power_type].add_charge(1)
            return True
        return False
    
    def use_power(self, power_type):
        """Aktifkan power-up"""
        if power_type in self.powers:
            return self.powers[power_type].use()
        return False
    
    def get_power_info(self, power_type):
        """Dapatkan info power (charges, cooldown, dll)"""
        if power_type in self.powers:
            power = self.powers[power_type]
            return {
                'charges': power.charges,
                'cooldown': power.current_cooldown,
                'can_use': power.can_use()
            }
        return None
    
    def get_power_description(self, power_type):
        """Dapatkan deskripsi power-up"""
        descriptions = {
            PowerUpType.BOMB: "💣 BOMB\nMeledakkan area 3x3\ndi sekitar impact",
            PowerUpType.LASER: "⚡ LASER\nTembakan laser vertikal\nmenghancurkan 1 kolom",
            PowerUpType.RAINBOW: "🌈 RAINBOW\nBubble universal\ncocok dengan warna apapun",
            PowerUpType.FIREBALL: "🔥 FIREBALL\nTembakan penetrasi\nmeledak saat berhenti",
            PowerUpType.FREEZE: "❄️ FREEZE\nFreeze drop counter\nuntuk 5 tembakan",
        }
        return descriptions.get(power_type, "Unknown Power")
    
    def get_power_color(self, power_type):
        """Dapatkan warna khas untuk setiap power"""
        colors = {
            PowerUpType.BOMB: QColor(255, 69, 0),      # Red-Orange
            PowerUpType.LASER: QColor(0, 255, 255),    # Cyan
            PowerUpType.RAINBOW: QColor(255, 0, 255),  # Magenta
            PowerUpType.FIREBALL: QColor(255, 140, 0), # Dark Orange
            PowerUpType.FREEZE: QColor(135, 206, 250), # Light Blue
        }
        return colors.get(power_type, QColor(255, 255, 255))

class PowerUpBubble(QGraphicsEllipseItem):
    """
    Visual representation untuk power-up bubble.
    Bubble khusus yang bisa ditembak dan memberikan power.
    """
    
    def __init__(self, power_type, x, y, radius=22):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.power_type = power_type
        self.radius_val = radius
        self.setPos(x, y)
        self.setup_appearance()
        self.row = 0
        self.col = 0
        
        # Animation timer untuk efek berkedip
        self.blink_timer = QTimer()
        self.blink_state = 0
        self.blink_timer.timeout.connect(self.animate_blink)
        self.blink_timer.start(200)  # Blink setiap 200ms
    
    def setup_appearance(self):
        """Setup visual appearance power-up bubble"""
        # Dapatkan warna khas power
        manager = PowerUpManager()
        base_color = manager.get_power_color(self.power_type)
        
        # Gradient radial dengan efek glow
        gradient = QRadialGradient(-self.radius_val * 0.3, -self.radius_val * 0.3, self.radius_val * 1.8)
        gradient.setColorAt(0, QColor(255, 255, 255, 200))  # Putih terang di tengah
        gradient.setColorAt(0.3, base_color)
        gradient.setColorAt(1, base_color.darker(150))
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(QColor(255, 255, 255), 2))  # Border putih tebal
        
        # Tambahkan icon/text di tengah
        self.icon_text = QGraphicsTextItem(self)
        self.icon_text.setPlainText(self.get_icon_emoji())
        self.icon_text.setDefaultTextColor(Qt.white)
        font = QFont("Segoe UI Emoji", 14, QFont.Bold)
        self.icon_text.setFont(font)
        
        # Center the text
        text_rect = self.icon_text.boundingRect()
        self.icon_text.setPos(-text_rect.width()/2, -text_rect.height()/2)
    
    def get_icon_emoji(self):
        """Dapatkan emoji icon untuk power type"""
        icons = {
            PowerUpType.BOMB: "💣",
            PowerUpType.LASER: "⚡",
            PowerUpType.RAINBOW: "🌈",
            PowerUpType.FIREBALL: "🔥",
            PowerUpType.FREEZE: "❄️",
        }
        return icons.get(self.power_type, "⭐")
    
    def animate_blink(self):
        """Animasi berkedip untuk menarik perhatian"""
        self.blink_state = (self.blink_state + 1) % 2
        if self.blink_state == 0:
            self.setOpacity(1.0)
        else:
            self.setOpacity(0.7)

class PowerUpVisualEffect:
    """
    Class untuk membuat visual effect saat power-up diaktifkan.
    """
    
    @staticmethod
    def create_explosion_effect(scene, x, y, radius, color):
        """Buat efek ledakan melingkar"""
        particles = []
        for i in range(16):
            angle = (i / 16) * 2 * math.pi
            distance = radius * 2
            
            end_x = x + math.cos(angle) * distance
            end_y = y + math.sin(angle) * distance
            
            # Buat particle line
            from PySide6.QtWidgets import QGraphicsLineItem
            line = QGraphicsLineItem(x, y, end_x, end_y)
            line.setPen(QPen(color, 3))
            scene.addItem(line)
            particles.append(line)
            
            # Hapus setelah delay
            QTimer.singleShot(300, lambda l=line: scene.removeItem(l) if l.scene() else None)
        
        return particles
    
    @staticmethod
    def create_laser_effect(scene, x, top_y, bottom_y, color):
        """Buat efek laser vertikal"""
        from PySide6.QtWidgets import QGraphicsRectItem
        
        laser_width = 10
        laser = QGraphicsRectItem(x - laser_width/2, top_y, laser_width, bottom_y - top_y)
        laser.setBrush(QBrush(color))
        laser.setPen(QPen(QColor(255, 255, 255), 2))
        laser.setOpacity(0.8)
        scene.addItem(laser)
        
        # Fade out animation
        opacity = 0.8
        def fade():
            nonlocal opacity
            opacity -= 0.1
            if opacity > 0:
                laser.setOpacity(opacity)
                QTimer.singleShot(50, fade)
            else:
                scene.removeItem(laser)
        
        QTimer.singleShot(100, fade)
        return laser
    
    @staticmethod
    def create_freeze_effect(scene, scene_rect):
        """Buat efek freeze pada seluruh layar"""
        from PySide6.QtWidgets import QGraphicsRectItem
        
        freeze_overlay = QGraphicsRectItem(scene_rect)
        freeze_overlay.setBrush(QBrush(QColor(135, 206, 250, 50)))  # Light blue transparent
        freeze_overlay.setPen(Qt.NoPen)
        freeze_overlay.setZValue(100)  # Di atas semua
        scene.addItem(freeze_overlay)
        
        # Blink effect
        blink_count = [0]
        def blink():
            blink_count[0] += 1
            if blink_count[0] % 2 == 0:
                freeze_overlay.setOpacity(0.3)
            else:
                freeze_overlay.setOpacity(0.6)
            
            if blink_count[0] < 6:
                QTimer.singleShot(200, blink)
            else:
                scene.removeItem(freeze_overlay)
        
        blink()
        return freeze_overlay

# === CONVENIENCE FUNCTIONS ===

_power_manager = None

def get_power_manager():
    """Get singleton instance of power manager"""
    global _power_manager
    if _power_manager is None:
        _power_manager = PowerUpManager()
    return _power_manager

def try_spawn_powerup(match_size):
    """Try to spawn a power-up after a match"""
    return get_power_manager().try_drop_powerup(match_size)

def add_powerup(power_type):
    """Add a charge to specific power-up"""
    return get_power_manager().add_powerup_charge(power_type)

def use_powerup(power_type):
    """Use a power-up"""
    return get_power_manager().use_power(power_type)

def get_all_powers_info():
    """Get info for all powers"""
    manager = get_power_manager()
    return {ptype: manager.get_power_info(ptype) for ptype in PowerUpType.__dict__.values() 
            if isinstance(ptype, str) and not ptype.startswith('_')}