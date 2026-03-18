<div align="center">

# 🐯 Macan Bubble Shooter

### Dynamic Edition — v6.5.0

A professional, full-featured bubble shooter game with a jungle/tiger theme built using PySide6.  
Features smooth animations, particle effects, a timer-driven scoring engine, 35 achievements,  
boss enemies, daily challenges, a replay system, and a fully immersive fullscreen experience.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/Version-6.5.0-orange.svg)

<img width="1365" height="767" alt="Screenshot 2026-03-18 200057" src="https://github.com/user-attachments/assets/59f6c7be-6be5-477f-8244-4d3316731da1" />


</div>

---

## ✨ What's New in v6.5.0

| Area | Highlight |
|---|---|
| 📅 **Daily Challenge** | Same deterministic grid for all players each day, 40-shot cap, shareable result |
| 👑 **Boss Bubbles** | Multi-hit enemies with HP bars, pulsing glow, and destruction rewards |
| 🧱 **Obstacle Bubbles** | Indestructible blockers that must be cleared by removing all neighbors |
| ♿ **Color-blind Mode** | Shape symbols + Okabe-Ito high-contrast palette, live rebuild |
| 🎬 **Replay System** | Frame-accurate recording, top-5 persistence, in-game browser |
| ⌨️ **Keyboard Shortcuts** | `Esc` / `P` to pause and resume at any time |
| 🖥 **Menu Redesign** | Leaderboard and Achievements accessible directly from main menu |

---

## 🎮 Features

### Core Gameplay
- **Classic bubble shooter mechanics** — match 3 or more bubbles of the same color to pop them
- **Tiger paw shooter** — unique shaped cannon with smooth mouse-driven aiming
- **6 premium bubble colors** — Ruby Red, Emerald Green, Sapphire Blue, Topaz Yellow, Amethyst Purple, Diamond Cyan
- **Intelligent match detection** — BFS-based color matching with rainbow bubble wildcard support
- **Floating bubble removal** — disconnected groups collapse automatically after each match
- **Wall bouncing** — bubbles reflect off side walls with precise angle calculation
- **Aim guide** — dotted aim line with wall-bounce prediction

### 📅 Daily Challenge
- **Same grid for everyone** — each day's layout is seeded from the calendar date,
  so all players face identical conditions
- **40-shot cap** — adds pressure without a time limit; results saved locally
- **Shareable text output** — one-click copy of your result to paste anywhere:
  ```
  🐯 Macan Bubble Shooter — Daily Challenge 2026-03-18
  Score: 12,450  |  ✅ Cleared!  |  Time: 02:31
  ```
- Main menu button shows today's score and ✅ if already completed

### 👑 Boss Bubbles
- Large (30 px radius) enemies that appear after big matches — require **2–5 hits** to destroy
- HP counter displayed on the bubble; pulsing gold ring shifts to red as health drops
- Each hit triggers a white flash; destruction awards a gold explosion and bonus score
- Spawn chance scales with level: `5 + level × 2 %` (capped at 30 %)

### 🧱 Obstacle Bubbles
- **Cannot be matched or shot through** — must be cleared indirectly
- Once all surrounding bubbles are removed, the obstacle becomes a floating cluster and drops
- Dark steel appearance with ✕ label — unmistakable at a glance
- Frequency scales from 4 % at level 1 to 15 % at level 11+

### ♿ Color-blind Mode
- **Shape overlay** — each color gets a unique symbol (● ■ ▲ ★ ♦ ✚)
- **Okabe-Ito palette** — scientifically designed color-safe replacement colors
- Toggle in the main menu; applies **live** without restarting the session

### 🎬 Replay System
- Every shot is recorded with its angle, color, and game tick
- Top 5 replays ranked by score are persisted to disk
- In-game **🎬** button opens the replay browser (game pauses automatically)
- `ReplayPlayer` provides frame-accurate playback at original timing

### ⏱ Timer & Speed System
- Each shot has an **8-second countdown** (4 seconds in Rush Mode)
- Fire quickly to earn a speed multiplier applied to your match score:

  | Time remaining | Multiplier |
  |---|---|
  | > 7.0 s | **3.0×** |
  | > 5.0 s | **2.5×** |
  | > 3.0 s | **2.0×** |
  | > 1.5 s | **1.5×** |
  | ≤ 1.5 s | **1.0×** |

- Color-coded timer bar below the arena: green → amber → red
- Slow shots incur a small score penalty

### 💎 Advanced Scoring
- **Combo system** — consecutive matches compound up to a **10×** multiplier
- **Streak bonuses** — milestone payouts at 5, 7, 10, and 15-shot streaks
- **Animated popups** — floating `+617 SUPER! COMBO ×5! ⚡2.5×` labels; pool capped at 3
- **Rush Mode bonus** — extra base points while Rush Mode is active

### ⚠️ Danger Zone
Four-level warning system as the grid descends toward the shooter:

| Level | Trigger | Scene Visual | HUD Pill |
|---|---|---|---|
| Safe | > 220 px | — | — |
| Warning | ≤ 220 px | Pulsing amber line | `⚠ WARNING` |
| Danger | ≤ 150 px | Orange line + red screen tint | `⚠ DANGER` |
| Critical | ≤ 90 px | Red pulsing line + overlay + **"⚠ DANGER ZONE"** scene label | `⚠ CRITICAL` |

### 🏅 Achievements
35 achievements across five categories, tracked persistently between sessions:

| Category | Count | Examples |
|---|---|---|
| 🏆 Score | 9 | Rookie → Legend *(hidden)* |
| 💥 Combat | 9 | First Pops → Annihilator, Cluster Bomb |
| ⚡ Skill | 13 | Triple Kill, On Fire! *(hidden)*, Speed Shooter, Power Master |
| ⏱ Time | 2 | Survivor (5 min), Endurance *(hidden)* |
| 🌟 Special | 4 | First Blood, Precision, Never Give Up, Comeback King |

- Hidden achievements are concealed until unlocked
- Each unlock credits a reward score instantly
- Slide-in toast notification appears for 3.5 seconds in the top-right corner

### 🏆 Leaderboard & Stats
- Local top-10 leaderboard persisted to disk, accessible from the main menu or in-game
- Per-session stats: shots fired, bubbles popped, best combo, total play time
- Game Over screen shows a full breakdown before offering Continue / New Game / Menu

### 🔋 Power-Up System
Five collectible power-ups dropped randomly after large matches:

| Power | Effect |
|---|---|
| 💣 Bomb | Destroys a 3×3 area around the impact point |
| ⚡ Laser | Clears an entire vertical column |
| 🌈 Rainbow | Wildcard bubble matching any color |
| 🔥 Fireball | Penetrating shot with a 5×5 explosion radius |
| ❄️ Freeze | Pauses the ceiling-drop counter for 5 shots |

### 🎨 Visual Design
- Fullscreen layout scaled via `KeepAspectRatioByExpanding`
- Custom wallpaper support: `ui/bubble_scn.webp` (in-game) and `ui/bubble_bgn.webp` (menu)
- Fallback procedural nebula with star field and nebula clouds
- Per-level background tinting — subtle overlay color change each level
- 8-particle burst per popped bubble with gravity and opacity fade
- Meteor trail effect on flying bubbles
- Bubble textures generated once and cached to disk

### 💾 Save / Load System
- Auto-save on exit and return to menu
- Persistent state: score, level, grid, shooter queue, power-up charges, play time, stats
- Storage: `AppData/Local/MacanBubbleShooter6/saves/`
- Continue from last save or wipe for a clean new game

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- PySide6 6.0 or higher

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/danx123/macan-bubble-shooter.git
   cd macan-bubble-shooter
   ```

2. **Install dependencies**
   ```bash
   pip install PySide6
   ```

3. **Run the game**
   ```bash
   python macan_bubble_shooter.py
   ```

---

## 🎮 How to Play

1. **Aim** — move your mouse over the play area to rotate the cannon
2. **Shoot** — left-click to fire; shoot quickly for a higher speed multiplier
3. **Swap** — right-click to swap the current bubble with the next one in the queue
4. **Match** — connect 3 or more bubbles of the same color to pop them
5. **Chain** — cleared groups may cause floating clusters to drop for bonus points
6. **Boss** — aim directly at the gold-bordered boss bubble and hit it multiple times
7. **Obstacles** — clear all neighboring bubbles around obstacle cells to dislodge them
8. **Survive** — watch the Danger Zone indicators and don't let the grid reach the shooter

### Controls

| Input | Action |
|---|---|
| Mouse movement | Aim the shooter |
| Left click | Fire bubble |
| Right click | Swap current / next bubble |
| `Esc` or `P` | Pause / resume |
| `🏠 MENU` button | Pause, auto-save, return to menu |
| `🏆` button | Open leaderboard (game pauses) |
| `🏅` button | Open achievement browser (game pauses) |
| `🎬` button | Open replay browser (game pauses) |

---

## 🏗️ Project Structure

```
macan-bubble-shooter/
│
├── macan_bubble_shooter.py   # Main game — GameScene, GameView, MainWindow
├── bubble_timer.py           # Shot timer, Rush Mode, game clock
├── bubble_score.py           # ScoreManager, score popups, leaderboard
├── bubble_achievement.py     # Achievement definitions, tracking, toast UI
├── bubble_ui.py              # LeaderboardDialog, AchievementDialog, GameOverDialog
├── bubble_special.py         # BossBubble, ObstacleBubble, ColorBlindMode, ReplaySystem
├── bubble_daily.py           # Daily Challenge grid generation and persistence
├── bubble_fx.py              # Sound effects and background music manager
├── bubble_gfx.py             # Graphics asset generation and disk cache
├── bubble_power.py           # Power-up types, manager, and visual effects
│
├── ui/
│   ├── bubble_scn.webp       # (optional) in-game scene wallpaper
│   └── bubble_bgn.webp       # (optional) menu background wallpaper
│
├── CHANGELOG.md
└── README.md

AppData/Local/MacanBubbleShooter6/
├── saves/
│   ├── save_v6.json          # Current game state
│   ├── highscore.json        # All-time high score
│   ├── leaderboard.json      # Top-10 leaderboard entries
│   ├── achievements.json     # Achievement progress
│   ├── daily.json            # Today's Daily Challenge result
│   └── replays.json          # Top-5 replays by score
└── cache/
    ├── bubble_0.png … bubble_5.png
    ├── launcher.png
    └── background_nebula.png
```

---

## 🔧 Technical Details

### Architecture

```
macan_bubble_shooter.py
├── bubble_timer.py        (no internal game dependencies)
├── bubble_score.py        (no internal game dependencies)
├── bubble_achievement.py  (no internal game dependencies)
├── bubble_ui.py           (depends on bubble_score, bubble_achievement)
├── bubble_special.py      (no internal game dependencies)
├── bubble_daily.py        (no internal game dependencies)
├── bubble_fx.py           (unchanged)
├── bubble_gfx.py          (unchanged)
└── bubble_power.py        (unchanged)
```

Each satellite module exposes a singleton accessor so shared state flows without
explicit reference passing (`get_score_manager()`, `get_shot_timer()`,
`get_daily_manager()`, `get_replay_manager()`, etc.).

### Rendering
- **Anti-aliasing** and `SmoothPixmapTransform` on all drawing operations
- **60 FPS** game loop via a 16 ms `QTimer`
- **ZValue layering**:

  | Layer | Z value |
  |---|---|
  | Background | −100 |
  | Bubbles / obstacles / bosses | 0 |
  | Aim line | 50 |
  | Danger overlay | 88–92 |
  | Score popups | 400 |
  | Achievement toasts | 600 |

- Scene coordinates are fixed; `QGraphicsView` scales to the window via
  `KeepAspectRatioByExpanding`

### Hexagonal Grid
- Offset-column hex grid: odd rows shifted right by one bubble radius
- Neighbor lookup uses per-row-parity direction tables
- BFS for match detection, ceiling-connectivity check, and floating cluster isolation
- Obstacle cells use sentinel value `−2`; boss position tracked separately

### Signal / Slot Map

| Signal (`GameScene`) | Slot (`MainWindow`) |
|---|---|
| `score_changed` | `update_score` |
| `high_score_changed` | `update_high_score` |
| `level_changed` | `update_level` |
| `drop_counter_changed` | `update_drop_counter` |
| `combo_changed` | `update_combo_label` |
| `timer_tick` | `update_timer_label` |
| `multiplier_changed` | `update_multiplier_display` |
| `playtime_changed` | `update_playtime_label` |
| `danger_level_changed` | `on_danger_level_changed` |
| `next_bubble_changed` | `update_next_bubble_ui` |
| `power_collected` | `on_power_collected` |
| `power_updated` | `update_all_power_buttons` |
| `game_over` | `show_game_over` |

---

## 🔧 Customization

### Bubble Colors
Edit `BUBBLE_PALETTE` in `macan_bubble_shooter.py`:
```python
BUBBLE_PALETTE = [
    {"base": QColor(255, 69, 58), "light": QColor(255, 134, 124), "dark": QColor(160, 20, 10)},
    # Add or replace entries here
]
```

### Difficulty Tuning
```python
BUBBLE_RADIUS  = 22   # Bubble size in pixels
ROWS           = 14   # Grid height
COLS           = 20   # Grid width
SHOTS_PER_DROP = 7    # Shots before the ceiling advances one row
```

### Daily Challenge Settings
Edit constants in `bubble_daily.py`:
```python
DAILY_ROWS      = 8    # Pre-filled rows in the daily grid
DAILY_SHOTS_CAP = 40   # Maximum shots before the challenge ends
DAILY_COLORS    = 6    # Number of colors used in the daily grid
```

### Timer Thresholds
Edit `TIME_MULTIPLIER_TABLE` in `bubble_timer.py`:
```python
TIME_MULTIPLIER_TABLE = [
    (7.0, 3.0),   # Fire within 1 s → 3.0×
    (5.0, 2.5),
    (3.0, 2.0),
    (1.5, 1.5),
    (0.0, 1.0),
]
```

### Custom Wallpaper
Place any image as `ui/bubble_scn.webp` (in-game) or `ui/bubble_bgn.webp` (menu).
Falls back to the procedural nebula generator if absent.

### Custom Cursor
Place `cursor.png` (24×24 px recommended) in
`AppData/Local/MacanBubbleShooter6/cursor.png` to override the default crosshair.

---

## 📸 Screenshots
<img width="1365" height="767" alt="Screenshot 2026-03-18 200057" src="https://github.com/user-attachments/assets/0632358f-ce1e-4b34-9d46-10e813e53f7c" />

<img width="1362" height="767" alt="Screenshot 2026-03-18 200317" src="https://github.com/user-attachments/assets/ed8301dd-e142-4ed7-a30a-b8a0341e95a7" />

<img width="1365" height="767" alt="Screenshot 2026-03-18 200117" src="https://github.com/user-attachments/assets/30faae82-6ea5-4a78-8850-22d33187ede5" />

---

## 🐛 Known Issues & Troubleshooting

| Issue | Resolution |
|---|---|
| Game won't launch | Ensure Python 3.8+ and `pip install PySide6` |
| No sound | Place `.wav` files in the `bubble_sound/` folder (see `bubble_fx.py`) |
| Save file corrupt | Delete `save_v6.json` from the saves folder; the game starts fresh |
| Bubbles appear misaligned | Delete the `cache/` folder to force asset regeneration |
| Black screen on startup | Verify OpenGL / GPU driver support for Qt |
| Daily Challenge not loading | Delete `daily.json` to reset today's record |

---

## 🗺️ Roadmap

- [ ] Online leaderboard — compare daily scores with other players globally
- [ ] Additional themes — ocean, space, desert visual sets
- [ ] Custom bubble skin editor
- [ ] Progressive difficulty — adaptive ceiling speed per level
- [ ] Online multiplayer mode

---

## 📝 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the project
2. Create your feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 👤 Author

Project Link: [https://github.com/danx123/macan-bubble-shooter](https://github.com/danx123/macan-bubble-shooter)

---

## 🙏 Acknowledgments

- [PySide6](https://doc.qt.io/qtforpython/) — excellent Qt6 Python bindings
- The bubble shooter genre pioneers for the timeless core mechanic
- All contributors and playtesters

---

<div align="center">

Made with ❤️ and Python 🐍

**Macan** means "Tiger" in Indonesian 🐯

</div>
