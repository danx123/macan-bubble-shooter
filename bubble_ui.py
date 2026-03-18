"""
bubble_ui.py - Komponen UI Tambahan untuk Macan Bubble Shooter
Modul ini berisi:
- LeaderboardDialog (popup top 10)
- AchievementDialog (layar semua achievement)
- GameOverDialog (versi baru dengan stats lengkap)
- HUD Timer Bar widget
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QGridLayout, QProgressBar,
    QGraphicsDropShadowEffect, QTabWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QBrush, QPalette, QPainter, QFont, QPixmap

from bubble_achievement import get_achievement_manager, ALL_ACHIEVEMENTS, ACHIEVEMENT_MAP
from bubble_score import get_leaderboard


# ============================================================
# SHARED STYLE CONSTANTS
# ============================================================

DARK_BG   = "#0a0e1a"
CARD_BG   = "#111827"
BORDER    = "#1e2d45"
GOLD      = "#FFD700"
SILVER    = "#C0C0C0"
BRONZE    = "#CD7F32"
TEXT_MAIN = "#e2e8f0"
TEXT_SUB  = "#64748b"
GREEN     = "#10b981"
RED       = "#ef4444"
BLUE      = "#3b82f6"
PURPLE    = "#8b5cf6"

BTN_BASE = """
    QPushButton {
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 22px;
        font-family: 'Segoe UI';
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton:pressed { margin-top: 2px; }
"""


def make_shadow(blur=30, color=QColor(0,0,0,180), offset=(0,8)):
    e = QGraphicsDropShadowEffect()
    e.setBlurRadius(blur)
    e.setColor(color)
    e.setOffset(*offset)
    return e


# ============================================================
# LEADERBOARD DIALOG
# ============================================================

class LeaderboardDialog(QDialog):

    def __init__(self, parent=None, current_score=0, current_level=1):
        super().__init__(parent)
        self.setWindowTitle("Leaderboard")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 620)

        self.current_score = current_score
        self.current_level = current_level
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_BG};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
        """)
        card.setGraphicsEffect(make_shadow())
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(14)

        # ── Header ──
        header = QHBoxLayout()
        title = QLabel("🏆  LEADERBOARD")
        title.setStyleSheet(f"color: {GOLD}; font-size: 22px; font-weight: 900; font-family: 'Segoe UI Black';")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(255,255,255,0.08); border-radius: 16px; color: {TEXT_MAIN}; font-size: 14px; }}
            QPushButton:hover {{ background: rgba(255,80,80,0.5); }}
        """)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        layout.addLayout(header)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {BORDER}; max-height: 1px;")
        layout.addWidget(sep)

        # ── Entries ──
        entries = get_leaderboard().get_entries()
        medals = {1: GOLD, 2: SILVER, 3: BRONZE}

        if not entries:
            empty = QLabel("No scores saved yet.\nPlay a full game session to appear on the leaderboard!")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px; padding: 40px;")
            layout.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            container = QWidget()
            container.setStyleSheet("background: transparent;")
            vbox = QVBoxLayout(container)
            vbox.setSpacing(6)
            vbox.setContentsMargins(0, 0, 0, 0)

            for rank, entry in enumerate(entries, 1):
                row = self._make_entry_row(rank, entry, medals.get(rank), self.current_score)
                vbox.addWidget(row)
            vbox.addStretch()

            scroll.setWidget(container)
            layout.addWidget(scroll)

        # ── Footer ──
        layout.addStretch()
        ach_mgr = get_achievement_manager()
        unlocked = ach_mgr.get_unlocked_count()
        total = ach_mgr.get_total_count()
        footer = QLabel(f"Achievements: {unlocked}/{total} unlocked")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"color: {TEXT_SUB}; font-size: 12px;")
        layout.addWidget(footer)

    def _make_entry_row(self, rank, entry, medal_color, current_score):
        is_current = (entry['score'] == current_score and rank <= 3)

        row = QFrame()
        border_color = medal_color if medal_color else BORDER
        bg = "rgba(255,215,0,0.08)" if medal_color else "rgba(255,255,255,0.03)"
        row.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border_color if medal_color else BORDER};
                border-radius: 10px;
                padding: 4px;
            }}
        """)

        hl = QHBoxLayout(row)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(10)

        # Rank
        rank_color = medal_color if medal_color else TEXT_SUB
        rank_lbl = QLabel(f"#{rank}")
        rank_lbl.setFixedWidth(32)
        rank_lbl.setStyleSheet(f"color: {rank_color}; font-size: 15px; font-weight: 900;")
        hl.addWidget(rank_lbl)

        # Medal emoji
        medal_map = {GOLD: "🥇", SILVER: "🥈", BRONZE: "🥉"}
        medal_lbl = QLabel(medal_map.get(medal_color, "  "))
        medal_lbl.setFixedWidth(24)
        hl.addWidget(medal_lbl)

        # Name
        name_lbl = QLabel(entry.get('name', 'PLAYER'))
        name_lbl.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 14px; font-weight: bold;")
        hl.addWidget(name_lbl, 1)

        # Level
        lv_lbl = QLabel(f"Lv.{entry.get('level', 1)}")
        lv_lbl.setStyleSheet(f"color: {BLUE}; font-size: 12px; font-weight: bold;")
        hl.addWidget(lv_lbl)

        # Score
        score_lbl = QLabel(f"{entry['score']:,}")
        score_lbl.setStyleSheet(f"color: {GOLD if medal_color else TEXT_MAIN}; font-size: 16px; font-weight: 900;")
        score_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(score_lbl)

        return row


# ============================================================
# ACHIEVEMENT DIALOG
# ============================================================

class AchievementDialog(QDialog):

    CATEGORY_LABELS = {
        'score':   ('💎 SCORE',   '#3b82f6'),
        'combat':  ('💥 COMBAT',  '#ef4444'),
        'skill':   ('⚡ SKILL',   '#8b5cf6'),
        'time':    ('⏱️ TIME',    '#10b981'),
        'special': ('🌟 SPECIAL', '#f59e0b'),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Achievements")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(680, 720)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_BG};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
        """)
        card.setGraphicsEffect(make_shadow())
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)

        # ── Header ──
        header = QHBoxLayout()
        ach_mgr = get_achievement_manager()
        unlocked = ach_mgr.get_unlocked_count()
        total = ach_mgr.get_total_count()
        title = QLabel(f"🏅  ACHIEVEMENTS  ({unlocked}/{total})")
        title.setStyleSheet(f"color: {GOLD}; font-size: 20px; font-weight: 900; font-family: 'Segoe UI Black';")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(255,255,255,0.08); border-radius: 16px; color: {TEXT_MAIN}; font-size: 14px; }}
            QPushButton:hover {{ background: rgba(255,80,80,0.5); }}
        """)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Progress bar total
        total_bar = QProgressBar()
        total_bar.setRange(0, total)
        total_bar.setValue(unlocked)
        total_bar.setFixedHeight(8)
        total_bar.setTextVisible(False)
        total_bar.setStyleSheet(f"""
            QProgressBar {{ background: {BORDER}; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {GOLD}; border-radius: 4px; }}
        """)
        layout.addWidget(total_bar)

        # ── Tabs per kategori ──
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{
                background: rgba(255,255,255,0.04);
                color: {TEXT_SUB};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 6px 14px;
                margin-right: 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: rgba(255,215,0,0.15);
                color: {GOLD};
                border-color: {GOLD};
            }}
        """)

        all_progress = ach_mgr.get_all_progress()

        # Tab "ALL"
        all_widget = self._make_category_tab([p for p in all_progress])
        tabs.addTab(all_widget, "📋 ALL")

        categories = ['score', 'combat', 'skill', 'time', 'special']
        for cat in categories:
            filtered = [p for p in all_progress if p['def'].category == cat]
            label, _ = self.CATEGORY_LABELS.get(cat, (cat.upper(), '#fff'))
            tab_widget = self._make_category_tab(filtered)
            tabs.addTab(tab_widget, label)

        layout.addWidget(tabs)

    def _make_category_tab(self, progress_list):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QGridLayout(container)
        grid.setSpacing(8)
        grid.setContentsMargins(2, 4, 2, 4)

        col_count = 2
        for idx, p in enumerate(progress_list):
            row_idx = idx // col_count
            col_idx = idx % col_count
            card = self._make_ach_card(p)
            grid.addWidget(card, row_idx, col_idx)

        # Dummy spacer
        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        return scroll

    def _make_ach_card(self, p):
        ach = p['def']
        unlocked = p['unlocked']
        pct = p['progress_pct']

        card = QFrame()
        if unlocked:
            card.setStyleSheet(f"""
                QFrame {{
                    background: rgba(16, 185, 129, 0.08);
                    border: 1px solid rgba(16,185,129,0.4);
                    border-radius: 10px;
                    padding: 4px;
                }}
            """)
        elif ach.hidden:
            card.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255,255,255,0.02);
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                    padding: 4px;
                }}
            """)
        else:
            card.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255,255,255,0.03);
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                    padding: 4px;
                }}
            """)

        hl = QHBoxLayout(card)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(10)

        # Icon
        icon_text = ach.icon if (unlocked or not ach.hidden) else "🔒"
        icon_lbl = QLabel(icon_text)
        icon_lbl.setStyleSheet("font-size: 24px;")
        icon_lbl.setFixedWidth(36)
        icon_lbl.setAlignment(Qt.AlignCenter)
        hl.addWidget(icon_lbl)

        vbox = QVBoxLayout()
        vbox.setSpacing(2)

        display_name = ach.name if (unlocked or not ach.hidden) else "???"
        display_desc = ach.description if (unlocked or not ach.hidden) else "Not yet unlocked"

        name_color = GREEN if unlocked else (TEXT_SUB if ach.hidden else TEXT_MAIN)
        name_lbl = QLabel(display_name)
        name_lbl.setStyleSheet(f"color: {name_color}; font-size: 12px; font-weight: bold;")
        vbox.addWidget(name_lbl)

        desc_lbl = QLabel(display_desc)
        desc_lbl.setStyleSheet(f"color: {TEXT_SUB}; font-size: 10px;")
        desc_lbl.setWordWrap(True)
        vbox.addWidget(desc_lbl)

        if not unlocked and not ach.hidden and pct > 0:
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(pct * 100))
            bar.setFixedHeight(4)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"""
                QProgressBar {{ background: {BORDER}; border-radius: 2px; }}
                QProgressBar::chunk {{ background: {BLUE}; border-radius: 2px; }}
            """)
            vbox.addWidget(bar)

        hl.addLayout(vbox, 1)

        if unlocked and ach.reward_score > 0:
            reward = QLabel(f"+{ach.reward_score:,}")
            reward.setStyleSheet(f"color: {GREEN}; font-size: 11px; font-weight: bold;")
            reward.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            hl.addWidget(reward)

        return card


# ============================================================
# GAME OVER DIALOG — Versi baru dengan stats + leaderboard entry
# ============================================================

class GameOverDialog(QDialog):

    # Signal-like: user memilih aksi
    action_continue = None
    action_new_game = None
    action_menu = None

    def __init__(self, parent=None, stats: dict = None, on_continue=None,
                 on_new_game=None, on_menu=None):
        super().__init__(parent)
        self.setWindowTitle("Game Over")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 560)

        self.stats = stats or {}
        self._on_continue = on_continue
        self._on_new_game = on_new_game
        self._on_menu = on_menu

        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_BG};
                border: 2px solid #2d1a1a;
                border-radius: 24px;
            }}
        """)
        card.setGraphicsEffect(make_shadow(40, QColor(0,0,0,200)))
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 36, 32, 28)
        layout.setSpacing(6)

        # ── Title ──
        title = QLabel("GAME OVER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            color: {RED};
            font-family: 'Segoe UI Black', Arial;
            font-size: 38px;
            font-weight: 900;
            letter-spacing: 3px;
        """)
        layout.addWidget(title)
        layout.addSpacing(8)

        # ── Score Box ──
        score_box = QFrame()
        score_box.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        sb_layout = QVBoxLayout(score_box)
        sb_layout.setContentsMargins(0, 16, 0, 16)
        sb_layout.setSpacing(2)

        lv_lbl = QLabel(f"LEVEL {self.stats.get('level', 1)}")
        lv_lbl.setAlignment(Qt.AlignCenter)
        lv_lbl.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px; font-weight: bold; letter-spacing: 2px;")
        sb_layout.addWidget(lv_lbl)

        score_lbl = QLabel(f"{self.stats.get('score', 0):,}")
        score_lbl.setAlignment(Qt.AlignCenter)
        score_lbl.setStyleSheet(f"color: #fbbf24; font-size: 52px; font-weight: 900; margin: 4px 0;")
        sb_layout.addWidget(score_lbl)

        best_lbl = QLabel(f"BEST: {self.stats.get('high_score', 0):,}")
        best_lbl.setAlignment(Qt.AlignCenter)
        best_lbl.setStyleSheet(f"color: {BLUE}; font-size: 14px; font-weight: bold;")
        sb_layout.addWidget(best_lbl)

        layout.addWidget(score_box)
        layout.addSpacing(12)

        # ── Stats Grid ──
        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)

        stats_items = [
            ("🎯 Shots Fired",  self.stats.get('total_shots', 0)),
            ("💥 Bubbles Pop",  self.stats.get('total_pops', 0)),
            ("⚡ Best Combo",   self.stats.get('best_combo', 0)),
            ("⏱️ Time",         self._format_time(self.stats.get('playtime', 0))),
        ]

        for idx, (label, val) in enumerate(stats_items):
            row_i = idx // 2
            col_i = idx % 2
            mini = self._make_stat_card(label, str(val))
            stats_grid.addWidget(mini, row_i, col_i)

        layout.addLayout(stats_grid)
        layout.addSpacing(16)

        # ── Achievement unlock count ──
        ach_mgr = get_achievement_manager()
        unlocked = ach_mgr.get_unlocked_count()
        total = ach_mgr.get_total_count()
        ach_lbl = QLabel(f"🏅 Achievements: {unlocked}/{total}")
        ach_lbl.setAlignment(Qt.AlignCenter)
        ach_lbl.setStyleSheet(f"color: {GOLD}; font-size: 12px; font-weight: bold;")
        layout.addWidget(ach_lbl)
        layout.addSpacing(8)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        continue_btn = QPushButton("↺ CONTINUE")
        continue_btn.setStyleSheet(BTN_BASE + f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {GREEN}, stop:1 #059669);
                border-bottom: 3px solid #047857;
            }}
            QPushButton:hover {{ background: #34d399; }}
        """)
        continue_btn.clicked.connect(lambda: [self.accept(), self._on_continue and self._on_continue()])

        new_btn = QPushButton("🆕 NEW GAME")
        new_btn.setStyleSheet(BTN_BASE + f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {RED}, stop:1 #dc2626);
                border-bottom: 3px solid #b91c1c;
            }}
            QPushButton:hover {{ background: #f87171; }}
        """)
        new_btn.clicked.connect(lambda: [self.accept(), self._on_new_game and self._on_new_game()])

        menu_btn = QPushButton("🏠 MENU")
        menu_btn.setStyleSheet(BTN_BASE + f"""
            QPushButton {{
                background: #1e293b;
                border: 1px solid {BORDER};
                border-bottom: 3px solid #0f172a;
            }}
            QPushButton:hover {{ background: #334155; }}
        """)
        menu_btn.clicked.connect(lambda: [self.accept(), self._on_menu and self._on_menu()])

        for btn in [continue_btn, new_btn, menu_btn]:
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

    def _make_stat_card(self, label, value):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,0.03);
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 8, 10, 8)
        vl.setSpacing(1)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_SUB}; font-size: 10px;")
        val_lbl = QLabel(str(value))
        val_lbl.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 18px; font-weight: 900;")
        vl.addWidget(lbl)
        vl.addWidget(val_lbl)
        return card

    def _format_time(self, seconds):
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}"
