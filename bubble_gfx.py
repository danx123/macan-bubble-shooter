"""
bubble_gfx.py - Graphics Asset Manager (Cached Version)
Mengelola aset grafis dengan sistem Caching untuk performa maksimal.
"""

from pathlib import Path
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QRadialGradient, QLinearGradient, QPolygonF
from PySide6.QtCore import Qt, QPointF
import sys
import random
import os

class BubbleGraphicsManager:
    def __init__(self, gfx_folder="bubble_img"):
        # 1. Tentukan Path Cache (Sama dengan lokasi Save Data + folder 'cache')
        # Lokasi: C:/Users/[User]/AppData/Local/MacanBubbleShooter6/cache
        self.user_data_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6"
        self.cache_dir = self.user_data_dir / "cache"
        
        # Buat folder cache jika belum ada
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Load assets (Cek Cache dulu, baru Generate)
        self._initialize_assets()

    def _initialize_assets(self):
        """Orchestrator untuk memuat aset"""
        print(f"📂 Cache Directory: {self.cache_dir}")
        
        # 1. Bubbles (0-5)
        for i in range(6):
            filename = f"bubble_{i}.png"
            # Kita generate ukuran cukup besar (100px) agar tajam saat di-scale
            self._load_or_create(f"bubble_{i}", filename, lambda: self._generate_bubble_graphic(i, 100))

        # 2. Launcher
        self._load_or_create("launcher", "launcher.png", lambda: self._generate_launcher_graphic(100, 160))

        # 3. Background (Ukuran Full HD)
        self._load_or_create("background", "background_nebula.png", lambda: self._generate_background_graphic(1920, 1080))
        
        print("✅ All graphics assets ready!")

    def _load_or_create(self, cache_key, filename, generator_func):
        """
        Logika Cerdas: Cek file -> Load jika ada -> Generate & Save jika tidak ada
        """
        file_path = self.cache_dir / filename
        
        # A. Coba Load dari Disk
        if file_path.exists():
            try:
                pixmap = QPixmap(str(file_path))
                if not pixmap.isNull():
                    self.cache[cache_key] = pixmap
                    # print(f"  ⚡ Loaded cached: {filename}")
                    return
            except Exception as e:
                print(f"  ⚠️ Corrupt cache {filename}, regenerating... ({e})")

        # B. Generate Baru (Jika file tidak ada atau rusak)
        print(f"  🎨 Generating new asset: {filename}...")
        pixmap = generator_func()
        self.cache[cache_key] = pixmap
        
        # C. Simpan ke Disk untuk pemakaian berikutnya
        try:
            pixmap.save(str(file_path), "PNG")
            print(f"  💾 Saved to cache: {filename}")
        except Exception as e:
            print(f"  ❌ Failed to save cache: {e}")

    # --- GENERATORS (Logika Menggambar Asli) ---

    def _generate_bubble_graphic(self, color_index, size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        c = self.colors[color_index % len(self.colors)]
        
        # Shadow
        shadow_grad = QRadialGradient(size*0.5, size*0.55, size*0.45)
        shadow_grad.setColorAt(0, QColor(0, 0, 0, 80))
        shadow_grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(size*0.1), int(size*0.1), int(size*0.8), int(size*0.8))
        
        # Main Body
        grad = QRadialGradient(size*0.35, size*0.35, size*0.6)
        grad.setColorAt(0, c["light"])
        grad.setColorAt(0.4, c["base"])
        grad.setColorAt(0.8, c["dark"])
        grad.setColorAt(1, c["dark"].darker(120))
        
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(c["dark"].darker(150), 2))
        painter.drawEllipse(int(size*0.05), int(size*0.05), int(size*0.9), int(size*0.9))
        
        # Highlight
        glow = QRadialGradient(size*0.3, size*0.25, size*0.3)
        glow.setColorAt(0, QColor(255, 255, 255, 200))
        glow.setColorAt(0.5, QColor(255, 255, 255, 100))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(size*0.15), int(size*0.1), int(size*0.4), int(size*0.4))
        
        # Rim Light
        rim = QRadialGradient(size*0.5, size*0.7, size*0.35)
        rim.setColorAt(0, QColor(255, 255, 255, 0))
        rim.setColorAt(0.7, QColor(255, 255, 255, 60))
        rim.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(rim))
        painter.drawEllipse(int(size*0.2), int(size*0.5), int(size*0.6), int(size*0.4))
        
        painter.end()
        return pixmap

    def _generate_launcher_graphic(self, w, h):
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Body Cannon
        body = QPolygonF([
            QPointF(w*0.25, h*0.95), QPointF(w*0.75, h*0.95),
            QPointF(w*0.65, h*0.3), QPointF(w*0.35, h*0.3)
        ])
        
        body_grad = QLinearGradient(0, h, 0, 0)
        body_grad.setColorAt(0, QColor(184, 134, 11))
        body_grad.setColorAt(0.3, QColor(218, 165, 32))
        body_grad.setColorAt(0.5, QColor(255, 215, 0))
        body_grad.setColorAt(0.7, QColor(218, 165, 32))
        body_grad.setColorAt(1, QColor(184, 134, 11))
        
        painter.setBrush(QBrush(body_grad))
        painter.setPen(QPen(QColor(139, 69, 19), 2.5))
        painter.drawPolygon(body)
        
        # Muzzle
        muzzle = QPolygonF([
            QPointF(w*0.35, h*0.3), QPointF(w*0.65, h*0.3),
            QPointF(w*0.6, h*0.05), QPointF(w*0.4, h*0.05)
        ])
        
        muzzle_grad = QLinearGradient(0, h*0.3, 0, 0)
        muzzle_grad.setColorAt(0, QColor(218, 165, 32))
        muzzle_grad.setColorAt(0.5, QColor(255, 223, 0))
        muzzle_grad.setColorAt(1, QColor(255, 240, 100))
        
        painter.setBrush(QBrush(muzzle_grad))
        painter.setPen(QPen(QColor(139, 69, 19), 2))
        painter.drawPolygon(muzzle)
        
        # Highlight
        highlight = QPolygonF([
            QPointF(w*0.4, h*0.9), QPointF(w*0.45, h*0.9),
            QPointF(w*0.43, h*0.4), QPointF(w*0.41, h*0.4)
        ])
        painter.setBrush(QBrush(QColor(255, 255, 200, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(highlight)
        
        # Base
        painter.setBrush(QBrush(QColor(139, 69, 19)))
        painter.setPen(QPen(QColor(101, 67, 33), 2))
        painter.drawEllipse(int(w*0.15), int(h*0.88), int(w*0.7), int(h*0.12))
        
        painter.end()
        return pixmap

    def _generate_background_graphic(self, w, h):
        pixmap = QPixmap(w, h)
        painter = QPainter(pixmap)
        
        # Base Gradient
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(5, 10, 25))
        grad.setColorAt(0.3, QColor(10, 15, 35))
        grad.setColorAt(0.6, QColor(15, 25, 45))
        grad.setColorAt(1, QColor(20, 30, 50))
        painter.fillRect(0, 0, w, h, grad)
        
        # Nebula Clouds
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        for _ in range(8):
            x, y = random.randint(-w//4, w), random.randint(-h//4, h)
            r = random.randint(200, 600)
            nebula = QRadialGradient(x, y, r)
            nebula.setColorAt(0, QColor(100, 50, 150, 40))
            nebula.setColorAt(0.5, QColor(80, 40, 120, 20))
            nebula.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(nebula))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x-r, y-r, r*2, r*2)
        
        for _ in range(6):
            x, y = random.randint(-w//4, w), random.randint(-h//4, h)
            r = random.randint(250, 700)
            nebula = QRadialGradient(x, y, r)
            nebula.setColorAt(0, QColor(50, 100, 200, 35))
            nebula.setColorAt(0.5, QColor(30, 70, 150, 18))
            nebula.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(nebula))
            painter.drawEllipse(x-r, y-r, r*2, r*2)
        
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        # Stars
        painter.setPen(Qt.NoPen)
        # Distant
        for _ in range(300):
            painter.setBrush(QColor(200, 200, 255, random.randint(100, 180)))
            s = random.uniform(0.5, 1.5)
            painter.drawEllipse(int(random.randint(0, w)), int(random.randint(0, h)), int(s), int(s))
        
        # Mid
        for _ in range(150):
            painter.setBrush(QColor(255, 255, 255, random.randint(150, 220)))
            s = random.uniform(1.5, 3)
            painter.drawEllipse(int(random.randint(0, w)), int(random.randint(0, h)), int(s), int(s))
        
        # Bright Stars
        for _ in range(80):
            x, y = random.randint(0, w), random.randint(0, h)
            s = random.uniform(2, 4)
            glow = QRadialGradient(x, y, s*3)
            glow.setColorAt(0, QColor(255, 255, 255, 200))
            glow.setColorAt(0.3, QColor(255, 255, 255, 100))
            glow.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(int(x-s*3), int(y-s*3), int(s*6), int(s*6))
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(int(x-s/2), int(y-s/2), int(s), int(s))
            
        painter.end()
        return pixmap

    # --- Accessors ---
    
    def has_graphics(self):
        return len(self.cache) > 0
    
    def get_bubble_pixmap(self, color_index, size=None):
        key = f"bubble_{color_index}"
        pixmap = self.cache.get(key)
        if pixmap and size:
            if isinstance(size, tuple):
                return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap

    def get_launcher_pixmap(self, size=None):
        pixmap = self.cache.get("launcher")
        if pixmap and size:
            if isinstance(size, tuple):
                return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap

    def get_background_pixmap(self, size=None):
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
    global _gfx_manager
    if _gfx_manager is None:
        _gfx_manager = BubbleGraphicsManager()
    return _gfx_manager

def get_bubble_pixmap(color_index, diameter):
    manager = get_graphics_manager()
    return manager.get_bubble_pixmap(color_index, (diameter, diameter))

def get_launcher_pixmap(width, height):
    manager = get_graphics_manager()
    return manager.get_launcher_pixmap((width, height))

def get_background_pixmap(width, height):
    manager = get_graphics_manager()
    return manager.get_background_pixmap((width, height))

def has_custom_graphics():
    return get_graphics_manager().has_graphics()

def get_custom_cursor():
    """Load custom cursor from cursor.png or cache if available"""
    from PySide6.QtGui import QCursor, QPixmap
    from PySide6.QtCore import Qt
    
    # Cek di folder cache dulu (siapa tahu user masukin custom cursor di folder data)
    user_data_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter6"
    cursor_cache = user_data_dir / "cursor.png"
    
    path_to_check = None
    
    if cursor_cache.exists():
        path_to_check = cursor_cache
    elif hasattr(sys, "_MEIPASS"):
        path_to_check = Path(sys._MEIPASS) / "./ui/cursor.png"
    else:
        path_to_check = Path(__file__).parent / "./ui/cursor.png"
        
    if path_to_check and path_to_check.exists():
        try:
            pixmap = QPixmap(str(path_to_check))
            if not pixmap.isNull():
                if pixmap.width() > 32 or pixmap.height() > 32:
                    pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                return QCursor(pixmap, pixmap.width() // 2, pixmap.height() // 2)
        except:
            pass
    return None