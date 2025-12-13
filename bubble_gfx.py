"""
bubble_gfx.py - Graphics Asset Manager (Auto-Gen Version) - FIXED
Membuat grafik secara otomatis jika file tidak ditemukan.
"""

from pathlib import Path
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QBrush, QPen, QRadialGradient, QLinearGradient, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF
import sys
import random

class BubbleGraphicsManager:
    def __init__(self, gfx_folder="bubble_img"):
        # Cek folder (biarkan logic path tetap ada)
        if hasattr(sys, "_MEIPASS"):
            self.gfx_path = Path(sys._MEIPASS) / gfx_folder
        else:
            self.gfx_path = Path(__file__).parent / gfx_folder
        
        self.cache = {}
        
        # Mapping warna
        self.colors = [
            {"base": QColor(255, 69, 58),  "light": QColor(255, 134, 124), "dark": QColor(160, 20, 10)},   # Red
            {"base": QColor(50, 215, 75),  "light": QColor(120, 255, 140), "dark": QColor(20, 120, 40)},   # Green
            {"base": QColor(10, 132, 255), "light": QColor(100, 180, 255), "dark": QColor(0, 60, 140)},    # Blue
            {"base": QColor(255, 214, 10), "light": QColor(255, 240, 100), "dark": QColor(180, 140, 0)},   # Yellow
            {"base": QColor(191, 90, 242), "light": QColor(220, 150, 255), "dark": QColor(100, 30, 140)},  # Purple
            {"base": QColor(100, 210, 255), "light": QColor(180, 240, 255), "dark": QColor(0, 100, 140)}   # Cyan
        ]
        
        # Load atau Generate Assets
        self._load_or_generate_assets()

    def _load_or_generate_assets(self):
        """Mencoba load file, jika gagal, generate grafik via kode"""
        print("🎨 Initializing Graphics (Auto-Generate Mode)...")
        
        # 1. Generate Bubbles (0-5)
        for i in range(6):
            pixmap = self._generate_bubble_graphic(i, 100)
            self.cache[f"bubble_{i}"] = pixmap
            print(f"  ✓ Generated bubble_{i}")

        # 2. Generate Launcher
        self.cache["launcher"] = self._generate_launcher_graphic(100, 160)
        print(f"  ✓ Generated launcher")

        # 3. Generate Background
        self.cache["background"] = self._generate_background_graphic(1920, 1080)
        print(f"  ✓ Generated background")
        
        print("✅ All assets generated successfully!")

    def _generate_bubble_graphic(self, color_index, size):
        """Membuat gambar bubble 3D mengkilap dengan QPainter"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        c = self.colors[color_index % len(self.colors)]
        
        # Shadow (Bayangan di bawah)
        shadow_grad = QRadialGradient(size*0.5, size*0.55, size*0.45)
        shadow_grad.setColorAt(0, QColor(0, 0, 0, 80))
        shadow_grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(size*0.1), int(size*0.1), int(size*0.8), int(size*0.8))
        
        # Main Bubble Body (Gradient 3D)
        grad = QRadialGradient(size*0.35, size*0.35, size*0.6)
        grad.setColorAt(0, c["light"])
        grad.setColorAt(0.4, c["base"])
        grad.setColorAt(0.8, c["dark"])
        grad.setColorAt(1, c["dark"].darker(120))
        
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(c["dark"].darker(150), 2))
        painter.drawEllipse(int(size*0.05), int(size*0.05), int(size*0.9), int(size*0.9))
        
        # Highlight Putih (Kilap)
        glow = QRadialGradient(size*0.3, size*0.25, size*0.3)
        glow.setColorAt(0, QColor(255, 255, 255, 200))
        glow.setColorAt(0.5, QColor(255, 255, 255, 100))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(size*0.15), int(size*0.1), int(size*0.4), int(size*0.4))
        
        # Rim Light (Tepi bawah)
        rim = QRadialGradient(size*0.5, size*0.7, size*0.35)
        rim.setColorAt(0, QColor(255, 255, 255, 0))
        rim.setColorAt(0.7, QColor(255, 255, 255, 60))
        rim.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(rim))
        painter.drawEllipse(int(size*0.2), int(size*0.5), int(size*0.6), int(size*0.4))
        
        painter.end()
        return pixmap

    def _generate_launcher_graphic(self, w, h):
        """Membuat gambar penembak cannon 3D"""
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # === BODY CANNON (Trapezoid) ===
        body = QPolygonF([
            QPointF(w*0.25, h*0.95),  # Kiri bawah
            QPointF(w*0.75, h*0.95),  # Kanan bawah
            QPointF(w*0.65, h*0.3),   # Kanan atas
            QPointF(w*0.35, h*0.3)    # Kiri atas
        ])
        
        # Gradient metalik emas
        body_grad = QLinearGradient(0, h, 0, 0)
        body_grad.setColorAt(0, QColor(184, 134, 11))   # Dark gold
        body_grad.setColorAt(0.3, QColor(218, 165, 32)) # Gold
        body_grad.setColorAt(0.5, QColor(255, 215, 0))  # Bright gold
        body_grad.setColorAt(0.7, QColor(218, 165, 32))
        body_grad.setColorAt(1, QColor(184, 134, 11))
        
        painter.setBrush(QBrush(body_grad))
        painter.setPen(QPen(QColor(139, 69, 19), 2.5))
        painter.drawPolygon(body)
        
        # === MUZZLE (Ujung meriam) ===
        muzzle = QPolygonF([
            QPointF(w*0.35, h*0.3),
            QPointF(w*0.65, h*0.3),
            QPointF(w*0.6, h*0.05),
            QPointF(w*0.4, h*0.05)
        ])
        
        muzzle_grad = QLinearGradient(0, h*0.3, 0, 0)
        muzzle_grad.setColorAt(0, QColor(218, 165, 32))
        muzzle_grad.setColorAt(0.5, QColor(255, 223, 0))
        muzzle_grad.setColorAt(1, QColor(255, 240, 100))
        
        painter.setBrush(QBrush(muzzle_grad))
        painter.setPen(QPen(QColor(139, 69, 19), 2))
        painter.drawPolygon(muzzle)
        
        # === HIGHLIGHT (Kilap) ===
        highlight = QPolygonF([
            QPointF(w*0.4, h*0.9),
            QPointF(w*0.45, h*0.9),
            QPointF(w*0.43, h*0.4),
            QPointF(w*0.41, h*0.4)
        ])
        painter.setBrush(QBrush(QColor(255, 255, 200, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(highlight)
        
        # === BASE (Platform bawah) ===
        painter.setBrush(QBrush(QColor(139, 69, 19)))
        painter.setPen(QPen(QColor(101, 67, 33), 2))
        painter.drawEllipse(int(w*0.15), int(h*0.88), int(w*0.7), int(h*0.12))
        
        painter.end()
        return pixmap

    def _generate_background_graphic(self, w, h):
        """Membuat background luar angkasa dengan nebula"""
        pixmap = QPixmap(w, h)
        painter = QPainter(pixmap)
        
        # === BASE GRADIENT (Deep Space) ===
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(5, 10, 25))      # Dark blue-black
        grad.setColorAt(0.3, QColor(10, 15, 35))
        grad.setColorAt(0.6, QColor(15, 25, 45))
        grad.setColorAt(1, QColor(20, 30, 50))
        painter.fillRect(0, 0, w, h, grad)
        
        # === NEBULA CLOUDS (Multi-layer) ===
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        
        # Purple nebula
        for i in range(8):
            x = random.randint(-w//4, w)
            y = random.randint(-h//4, h)
            radius = random.randint(200, 600)
            nebula = QRadialGradient(x, y, radius)
            nebula.setColorAt(0, QColor(100, 50, 150, 40))
            nebula.setColorAt(0.5, QColor(80, 40, 120, 20))
            nebula.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(nebula))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x-radius, y-radius, radius*2, radius*2)
        
        # Blue nebula
        for i in range(6):
            x = random.randint(-w//4, w)
            y = random.randint(-h//4, h)
            radius = random.randint(250, 700)
            nebula = QRadialGradient(x, y, radius)
            nebula.setColorAt(0, QColor(50, 100, 200, 35))
            nebula.setColorAt(0.5, QColor(30, 70, 150, 18))
            nebula.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(nebula))
            painter.drawEllipse(x-radius, y-radius, radius*2, radius*2)
        
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        # === STARS (Multiple layers untuk depth) ===
        # Distant stars (small, dim)
        painter.setPen(Qt.NoPen)
        for _ in range(300):
            x = random.randint(0, w)
            y = random.randint(0, h)
            size = random.uniform(0.5, 1.5)
            opacity = random.randint(100, 180)
            painter.setBrush(QColor(200, 200, 255, opacity))
            painter.drawEllipse(int(x), int(y), int(size), int(size))
        
        # Mid-distance stars (medium)
        for _ in range(150):
            x = random.randint(0, w)
            y = random.randint(0, h)
            size = random.uniform(1.5, 3)
            opacity = random.randint(150, 220)
            painter.setBrush(QColor(255, 255, 255, opacity))
            painter.drawEllipse(int(x), int(y), int(size), int(size))
        
        # Close stars (large, bright with glow)
        for _ in range(80):
            x = random.randint(0, w)
            y = random.randint(0, h)
            size = random.uniform(2, 4)
            
            # Glow effect
            glow = QRadialGradient(x, y, size*3)
            glow.setColorAt(0, QColor(255, 255, 255, 200))
            glow.setColorAt(0.3, QColor(255, 255, 255, 100))
            glow.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(int(x-size*3), int(y-size*3), int(size*6), int(size*6))
            
            # Core
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(int(x-size/2), int(y-size/2), int(size), int(size))
        
        # === SHOOTING STARS (Optional) ===
        for _ in range(5):
            x1 = random.randint(0, w-200)
            y1 = random.randint(0, h)
            length = random.randint(100, 250)
            angle = random.uniform(-30, 30)
            
            x2 = x1 + length
            y2 = y1 + length * (angle/100)
            
            gradient = QLinearGradient(x1, y1, x2, y2)
            gradient.setColorAt(0, QColor(255, 255, 255, 0))
            gradient.setColorAt(0.7, QColor(255, 255, 255, 180))
            gradient.setColorAt(1, QColor(255, 255, 255, 255))
            
            painter.setPen(QPen(QBrush(gradient), 2))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            
        painter.end()
        return pixmap

    # --- Public Accessors ---
    
    def has_graphics(self):
        """Check if graphics are available"""
        return len(self.cache) > 0
    
    def get_bubble_pixmap(self, color_index, size=None):
        """Get bubble pixmap by color index
        
        Args:
            color_index: Color index (0-5)
            size: Tuple (width, height) or None to use original size
            
        Returns:
            QPixmap or None
        """
        key = f"bubble_{color_index}"
        pixmap = self.cache.get(key)
        
        if pixmap and size:
            if isinstance(size, tuple):
                return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                # size adalah integer (diameter)
                return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap

    def get_launcher_pixmap(self, size=None):
        """Get launcher pixmap
        
        Args:
            size: Tuple (width, height) or None
            
        Returns:
            QPixmap or None
        """
        pixmap = self.cache.get("launcher")
        if pixmap and size:
            if isinstance(size, tuple):
                return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                # Jika size adalah integer, anggap width, height auto
                return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap

    def get_background_pixmap(self, size=None):
        """Get background pixmap
        
        Args:
            size: Tuple (width, height) or None
            
        Returns:
            QPixmap or None
        """
        pixmap = self.cache.get("background")
        if pixmap and size:
            if isinstance(size, tuple):
                return pixmap.scaled(size[0], size[1], Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            else:
                return pixmap.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return pixmap


# --- Singleton & Helpers ---
_gfx_manager = None

def get_graphics_manager():
    """Get singleton graphics manager instance"""
    global _gfx_manager
    if _gfx_manager is None:
        _gfx_manager = BubbleGraphicsManager()
    return _gfx_manager

def get_bubble_pixmap(color_index, diameter):
    """Get bubble pixmap with specific diameter
    
    Args:
        color_index: Color index (0-5)
        diameter: Diameter in pixels
        
    Returns:
        QPixmap or None
    """
    manager = get_graphics_manager()
    return manager.get_bubble_pixmap(color_index, (diameter, diameter))

def get_launcher_pixmap(width, height):
    """Get launcher pixmap with specific size
    
    Args:
        width: Width in pixels
        height: Height in pixels
        
    Returns:
        QPixmap or None
    """
    manager = get_graphics_manager()
    return manager.get_launcher_pixmap((width, height))

def get_background_pixmap(width, height):
    """Get background pixmap with specific size
    
    Args:
        width: Width in pixels
        height: Height in pixels
        
    Returns:
        QPixmap or None
    """
    manager = get_graphics_manager()
    return manager.get_background_pixmap((width, height))

def has_custom_graphics():
    """Check if custom graphics are available
    
    Returns:
        bool: Always True in auto-generate mode
    """
    return get_graphics_manager().has_graphics()

def get_custom_cursor():
    """Load custom cursor from cursor.png
    
    Returns:
        QCursor or None if file not found
    """
    from PySide6.QtGui import QCursor, QPixmap
    from PySide6.QtCore import Qt
    from pathlib import Path
    import sys
    
    # Cari file cursor.png
    if hasattr(sys, "_MEIPASS"):
        cursor_path = Path(sys._MEIPASS) / "cursor.png"
    else:
        cursor_path = Path(__file__).parent / "cursor.png"
    
    print(f"🔍 Looking for cursor at: {cursor_path}")
    print(f"🔍 File exists: {cursor_path.exists()}")
    
    if cursor_path.exists():
        try:
            pixmap = QPixmap(str(cursor_path))
            print(f"🔍 Pixmap loaded: {not pixmap.isNull()}, size: {pixmap.width()}x{pixmap.height()}")
            
            if not pixmap.isNull():
                # Scale jika terlalu besar (max 32x32 untuk cursor)
                if pixmap.width() > 32 or pixmap.height() > 32:
                    pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    print(f"🔍 Scaled to: {pixmap.width()}x{pixmap.height()}")
                
                # Hotspot di tengah cursor
                hotspot_x = pixmap.width() // 2
                hotspot_y = pixmap.height() // 2
                
                cursor = QCursor(pixmap, hotspot_x, hotspot_y)
                print(f"✅ QCursor created successfully with hotspot ({hotspot_x}, {hotspot_y})")
                return cursor
            else:
                print("❌ Pixmap is null (failed to load)")
        except Exception as e:
            print(f"❌ Failed to load cursor.png: {e}")
    else:
        print(f"❌ cursor.png not found at {cursor_path}")
    
    return None