<div align="center">

# 🐯 Macan Bubble Shooter

### Dynamic Edition — v6.0.0

A professional, full-featured bubble shooter game with a jungle/tiger theme built using PySide6.  
Features smooth animations, particle effects, a timer-driven scoring engine, 35 achievements, and a fully immersive fullscreen experience.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/Version-6.0.0-orange.svg)

<img width="1365" height="767" alt="Screenshot 2026-03-18 073427" src="https://github.com/user-attachments/assets/718f2da3-8802-4852-b2f9-b59bd79a555f" />

</div>

---

## ✨ What's New in v6.0.0

| Area | Highlight |
|---|---|
| ⏱ **Timer System** | Per-shot countdown with speed multiplier (up to 3.0×) |
| 💎 **Scoring Engine** | Combo chains, streak bonuses, animated score popups |
| 🏅 **Achievements** | 35 unlockable achievements with persistent progress |
| ⚠️ **Danger Zone** | 4-level visual warning when bubbles approach the shooter |
| 🏆 **Leaderboard** | Local top-10 with full session stats |
| 🌐 **Full English UI** | All interface text translated to English |



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

### ⏱ Timer & Speed System
- Each shot has an **8-second countdown** (4 seconds in Rush Mode)
- Fire quickly to earn a **speed multiplier** applied to your match score:

  | Time remaining | Multiplier |
  |---|---|
  | > 7.0 s | **3.0×** |
  | > 5.0 s | **2.5×** |
  | > 3.0 s | **2.0×** |
  | > 1.5 s | **1.5×** |
  | ≤ 1.5 s | **1.0×** |

- A **color-coded timer bar** sits below the arena: green → amber → red
- Slow shots incur a small score penalty

### 💎 Advanced Scoring
- **Combo system** — consecutive matches build a combo multiplier (max 10×, +0.3× per level)
- **Streak bonuses** — fixed payouts at 5, 7, 10, and 15-shot streaks
- **Animated popups** — `+617 SUPER! COMBO ×5! ⚡2.5×` labels float upward and fade; pool capped at 3 simultaneous popups
- **Drop scoring** — floating bubbles award batch points in a single event rather than one popup per bubble
- **Rush Mode bonus** — extra base points awarded while Rush Mode is active

### ⚠️ Danger Zone
A four-level warning system activates as the bubble grid descends toward the shooter:

| Level | Trigger | Scene Visual | HUD Pill |
|---|---|---|---|
| Safe | > 220 px | — | — |
| Warning | ≤ 220 px | Pulsing amber line | `⚠ WARNING` |
| Danger | ≤ 150 px | Orange line + red screen tint | `⚠ DANGER` |
| Critical | ≤ 90 px | Red pulsing line + overlay + **"⚠ DANGER ZONE"** label | `⚠ CRITICAL` |

All visuals pulse at ~25 fps and reset cleanly on new game.

### 🏅 Achievement System
35 achievements across five categories, tracked persistently between sessions:

| Category | Count | Examples |
|---|---|---|
| 🏆 Score | 9 | Rookie → Legend (hidden) |
| 💥 Combat | 9 | First Pops → Annihilator, Cluster Bomb |
| ⚡ Skill | 13 | Triple Kill, On Fire!, Speed Shooter, Power Master |
| ⏱ Time | 2 | Survivor (5 min), Endurance (10 min, hidden) |
| 🌟 Special | 4 | First Blood, Precision, Never Give Up, Comeback King |

- Hidden achievements are concealed until unlocked
- Each unlock rewards bonus score instantly
- A **slide-in toast notification** appears for 3.5 seconds in the top-right of the play area

### 🏆 Leaderboard & Stats
- **Local top-10 leaderboard** persisted to disk, accessible in-game at any time
- Stats tracked per session: shots fired, bubbles popped, best combo, total play time
- **Game Over screen** shows a full stats breakdown before offering Continue / New Game / Menu

### 🔋 Power-Up System
Five collectible power-ups dropped randomly after large matches:

| Power | Effect |
|---|---|
| 💣 Bomb | Destroys a 3×3 area around the impact point |
| ⚡ Laser | Clears an entire vertical column |
| 🌈 Rainbow | Acts as a wildcard matching any color |
| 🔥 Fireball | Penetrating shot with a 5×5 explosion radius |
| ❄️ Freeze | Pauses the ceiling-drop counter for 5 shots |

### 🎨 Visual Design
- **Fullscreen immersive layout** — game view scales with KeepAspectRatioByExpanding
- **Custom wallpaper support** — place `bubble_scn.webp` / `bubble_bgn.webp` in the `ui/` folder
- **Fallback procedural nebula** — generated star field with nebula clouds if no wallpaper is found
- **Per-level background tinting** — overlay color shifts subtly each level
- **Particle explosions** — 8-particle burst per popped bubble with gravity and opacity fade
- **Meteor trail effect** — flying bubbles leave a short particle trail
- **Cached graphics assets** — bubble textures generated once and saved to disk for fast startup

### 💾 Save / Load System
- **Auto-save** on exit and on return to main menu
- **Persistent state**: score, level, grid layout, shooter queue, power-up charges, play time, and stats
- Storage path: `AppData/Local/MacanBubbleShooter6/saves/`
- **Continue** from last save or **wipe** for a clean new game

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
3. **Swap** — right-click to swap the current bubble with the next one in queue
4. **Match** — connect 3 or more bubbles of the same color to pop them
5. **Chain** — clearing a group may cause floating clusters to drop, earning bonus points
6. **Survive** — don't let the bubble grid reach the shooter, and watch the Danger Zone indicators

### Controls

| Input | Action |
|---|---|
| Mouse movement | Aim the shooter |
| Left click | Fire bubble |
| Right click | Swap current / next bubble |
| `🏠 MENU` button | Pause, auto-save, and return to main menu |
| `🏆` button | Open leaderboard (game pauses) |
| `🏅` button | Open achievement browser (game pauses) |

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
│   └── achievements.json     # Achievement progress
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
├── bubble_fx.py           (unchanged from v5)
├── bubble_gfx.py          (unchanged from v5)
└── bubble_power.py        (unchanged from v5)
```

Each satellite module exposes a singleton accessor (`get_score_manager()`,
`get_shot_timer()`, etc.) so shared state flows without explicit reference passing.

### Rendering
- **Anti-aliasing** and **SmoothPixmapTransform** on all drawing operations
- **60 FPS** game loop (16 ms `QTimer`)
- **ZValue layering**: background (−100) → bubbles (0) → aim line (50) → danger overlay (88–92) → score popups (400) → achievement toasts (600)
- Scene coordinates are fixed; the `QGraphicsView` scales to the window via `KeepAspectRatioByExpanding`

### Hexagonal Grid
- Offset-column hex grid: odd rows are shifted right by one bubble radius
- Neighbor lookup uses direction tables per row parity
- BFS used for match detection, connectivity check, and floating cluster isolation

### Signal / Slot Map

| Signal (GameScene) | Connected slot (MainWindow) |
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
The game falls back to the procedural nebula generator if these files are absent.

### Custom Cursor
Place `cursor.png` (24×24 px recommended) in
`AppData/Local/MacanBubbleShooter6/cursor.png` to override the default crosshair.

---

## 📸 Screenshots

<img width="1365" height="767" alt="Gameplay" src="https://github.com/user-attachments/assets/70155a67-6ea8-4674-b4cb-fc8e60cba25b" />

<img width="1365" height="767" alt="Danger Zone" src="https://github.com/user-attachments/assets/32f0cfbc-a584-470a-9c01-3e5b255cd14a" />

<img width="1365" height="767" alt="Achievement Toast" src="https://github.com/user-attachments/assets/b0a596a1-8641-4d4c-bf6e-2f30ecc2f528" />

---

## 🐛 Known Issues & Troubleshooting

| Issue | Resolution |
|---|---|
| Game won't launch | Ensure Python 3.8+ and `pip install PySide6` |
| No sound | Place `.wav` files in the `bubble_sound/` folder (see `bubble_fx.py`) |
| Save file corrupt | Delete `save_v6.json` from the saves folder; the game starts fresh |
| Bubbles appear misaligned | Delete the `cache/` folder to force asset regeneration |
| Black screen on startup | Verify OpenGL / GPU driver support for Qt |

---

## 🗺️ Roadmap

- [ ] Daily Challenge mode — fixed seed grid, global score compare
- [ ] Boss Bubbles — large multi-hit bubbles requiring several shots
- [ ] Obstacle / Shield Bubbles — immovable blockers that must be cleared around
- [ ] Color-blind mode — shape overlays on every bubble color
- [ ] Replay system — record and replay best sessions
- [ ] Additional themes — ocean, space, desert
- [ ] Online leaderboard integration
- [ ] Custom bubble skin editor

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
