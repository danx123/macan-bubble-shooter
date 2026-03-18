## [6.5.0] — 2026-03-18

This release delivers five major feature systems on top of the v6.0.0 foundation,
packaged in two new dedicated modules. The main menu has been redesigned with
direct access to the leaderboard and achievements, keyboard shortcuts are now
supported, and the codebase gains boss mechanics, environmental obstacles,
an accessibility mode, a replay engine, and a daily challenge mode with a
shareable result format.

### New Modules

| Module | Responsibility |
|---|---|
| `bubble_daily.py` | Daily Challenge grid generation, shot cap, and session persistence |
| `bubble_special.py` | Boss Bubbles, Obstacle Bubbles, Color-blind Mode, Replay System |

---

### Added

#### 📅 Daily Challenge (`bubble_daily.py`)

- **Deterministic daily grid** — each calendar day produces the same bubble
  layout for all players, derived from an MD5 seed of the ISO date string
  (`YYYY-MM-DD`). The grid uses a density gradient: denser at the bottom rows,
  sparser toward the top.
- **Shot cap** — the challenge ends after **40 shots** regardless of whether the
  grid has been cleared, adding a fixed pressure element absent from the
  infinite free-play mode.
- **Persistent result** — today's score, shot count, completion status, and play
  time are written to `daily.json` and survive between sessions. Replaying on the
  same day resets the shot counter but preserves the personal best for that day.
- **Shareable result string** — `DailyChallengeManager.get_share_text()` produces
  a clipboard-ready summary:
  ```
  🐯 Macan Bubble Shooter — Daily Challenge 2026-03-18
  Score: 12,450  |  ✅ Cleared!  |  Time: 02:31
  Play at: github.com/danx123/macan-bubble-shooter
  ```
- **Main menu integration** — the Daily Challenge button dynamically shows
  today's score and a ✅ badge once the challenge has been completed.

#### 👑 Boss Bubbles (`bubble_special.BossBubble`)

- **Multi-hit bubbles** — boss bubbles require 2–5 direct hits to destroy, with
  HP scaling per level: `hp = min(2 + level // 2, 5)`.
- **Larger hitbox** — boss radius is 30 px (vs. the standard 22 px), making them
  a prominent target in the grid.
- **Visual indicators** — gold border, radial-gradient body, and a live HP
  counter label centered on the bubble face.
- **Pulsing glow ring** — an outer ring pulses at ~20 fps; color interpolates
  from gold → red as HP decreases.
- **Hit feedback** — each hit triggers a 120 ms white flash before reverting to
  the gold border.
- **Destruction reward** — destroying a boss awards `200 + max_hp × 50` points,
  a gold particle burst, and a `👑 BOSS!` score popup.
- **Probabilistic spawn** — bosses appear after matches of 5+ bubbles with a
  chance of `min(5 + level × 2, 30)` percent, spawning near the cleared area.

#### 🧱 Obstacle Bubbles (`bubble_special.ObstacleBubble`)

- **Indestructible cells** — obstacle bubbles cannot be matched, shot through,
  or removed by any power-up directly.
- **Gravity-clear mechanic** — they obey the same floating-bubble detection as
  normal bubbles: once all connected neighbors are removed, the cluster becomes
  disconnected from the ceiling and drops naturally, awarding drop-score points.
- **Visual design** — dark steel gradient with a ✕ label and silver border,
  clearly distinguishable from all six normal colors and from boss bubbles.
- **Level scaling** — obstacle probability in new ceiling rows grows from 4 % at
  level 1 to a cap of 15 % at level 11+, via `obstacle_chance(level)`.

#### ♿ Color-blind Mode (`bubble_special`)

- **Per-color shape symbols** — each of the six bubble colors is assigned a
  unique geometric symbol: `● ■ ▲ ★ ♦ ✚`. The symbol is rendered as a centered
  white label overlaid on the bubble.
- **Okabe-Ito palette** — bubble fill colors are replaced with a
  color-vision-deficiency-safe palette widely used in scientific publishing, with
  strong contrast across all six slots.
- **Persistent setting** — toggle state is stored in `settings.json` under
  `colorblind_enabled` and applied on startup via `set_colorblind_mode()`.
- **Live rebuild** — toggling mid-session immediately rebuilds all visible bubble
  visuals in-place; no game restart required.
- **Main menu checkbox** — `COLOR-BLIND` checkbox added alongside MUSIC and
  SOUND FX in the settings row.

#### 🎬 Replay System (`bubble_special`)

- **Frame-accurate recording** — `ReplayRecorder` captures every shot (angle,
  bubble color, game tick) and swap action during a live session.
- **Top-5 persistence** — replays are ranked by final score; the top 5 are saved
  to `replays.json`. Lower-scoring replays are discarded automatically.
- **`ReplayPlayer`** — a `QTimer`-driven playback engine that re-issues shot and
  swap events at their original tick timestamps, enabling frame-accurate
  reproduction of any saved session.
- **In-game replay browser** (`🎬` HUD button) — lists saved replays with score,
  level, shot count, and recording date. Game pauses automatically while the
  dialog is open.
- **Auto-save on session end** — a replay is attempted at game over, return to
  menu, and window close via `_save_replay_after_session()`.

#### ⌨️ Keyboard Shortcuts

- **`Esc` / `P`** — pause and resume the game from anywhere in the play area.
- Implemented in `GameView.keyPressEvent`; the handler walks the parent chain to
  reach `MainWindow.toggle_pause()`.
- The MENU button label updates to `▶ RESUME  (P)` while paused to confirm the
  shortcut visually, then restores to `🏠 MENU` on resume.

#### 🖥 Main Menu Redesign (`WelcomeScreen`)

- **Daily Challenge button** — full-width green primary button below CONTINUE;
  label reflects today's result dynamically.
- **Secondary row** — `🏆 LEADERBOARD` and `🏅 ACHIEVEMENTS` rendered side-by-side,
  opening the respective dialogs directly from the menu without starting a game.
- **Color-blind toggle** — third checkbox in the settings row.
- **Keyboard hint** — version label updated to
  `v6.5.0 — Dynamic Edition  ·  ESC / P to pause`.
- **Wider card** — main menu card width increased from 450 px to 480 px.

#### 🎬 In-Game HUD: Replay Button

- `🎬` button added to the right side of the HUD, styled in sky-blue alongside
  `🏆` and `🏅`, opening the replay browser with automatic game pause.

---

### Changed

- **`WelcomeScreen.__init__` signature** — extended with optional keyword
  arguments `daily_callback`, `leaderboard_callback`, `achievements_callback`,
  `colorblind_callback`, and `colorblind_on`. Omitting any argument is safe; the
  corresponding button or toggle is simply inert.
- **`reset_game()`** — now clears `boss_bubbles`, `obstacle_bubbles`, the replay
  recorder state, and `daily_mode` / `daily_shots` counters, in addition to all
  existing v6.0.0 resets.
- **`back_to_menu()`** — calls `_save_replay_after_session()` before `save_game()`
  to ensure session replay data is not lost when returning mid-game.
- **`show_game_over()`** — calls `_save_replay_after_session()` alongside the
  existing leaderboard submission.
- **`closeEvent()`** — calls `_save_replay_after_session()` before `save_game()`
  to capture replays on abrupt close.
- **`settings.json` schema** — extended with `colorblind_enabled` (boolean).
  Existing files without this key default to `false`.
- **Architecture diagram** updated to include the two new modules:

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

---

### Fixed

- **Circular import in `bubble_daily.py`** — initial implementation imported
  `ROWS` from `macan_bubble_shooter` at module level, causing a startup error.
  Replaced with a local constant `TOTAL_ROWS = 14`.
- **`toggle_pause()` missing** — `MainWindow` lacked a unified pause/resume
  method, preventing the `Esc`/`P` shortcut from functioning. Implemented as a
  single coordinated method managing `QTimer`, `ShotTimer`, `GameTimer`, BGM
  state, and HUD button label.
- **Boss bubble `destroyed` signal double-fire** — the lambda closure captured
  `boss` by reference, potentially firing for already-removed items after a scene
  reset. Fixed by connecting directly to `_on_boss_destroyed`.

---

### Storage Changes

| File | Status | Notes |
|---|---|---|
| `settings.json` | Extended | Added `colorblind_enabled` boolean |
| `daily.json` | **New** | Daily challenge result for the current calendar day |
| `replays.json` | **New** | Top-5 replays ranked by final score |

All new files are created on first use. Existing installations upgrade silently
with no manual migration required.

---

## [6.0.0] — Dynamic Edition — 2026-03-18

Major overhaul introducing timer-driven scoring, 35 achievements, a four-level
danger zone system, and four new satellite modules. Full details below.

### New Modules

| Module | Responsibility |
|---|---|
| `bubble_timer.py` | Shot timer, Rush Mode, global game clock |
| `bubble_score.py` | ScoreManager, score popups, local leaderboard |
| `bubble_achievement.py` | 35 achievement definitions, progress tracking, toast UI |
| `bubble_ui.py` | LeaderboardDialog, AchievementDialog, GameOverDialog |

### Added
- Per-shot countdown timer with speed multiplier up to 3.0×; Rush Mode compresses
  the window to 4 s when bubbles approach the shooter.
- `ScoreManager` as the single source of truth; combo (max 10×) and streak
  multipliers; animated popup pool capped at 3 simultaneous entries.
- 35 persistent achievements across five categories with reward scores and
  slide-in toast notifications.
- Four-level Danger Zone overlay (Safe → Warning → Danger → Critical) driven by
  distance between the lowest bubble and the shooter.
- HUD pills for combo, timer, playtime, and danger level.
- In-game `🏆` Leaderboard and `🏅` Achievements buttons with automatic pause.
- Redesigned Game Over screen with full stats breakdown and leaderboard submission.
- Full English translation of all UI-facing strings.

### Changed
- All score mutations routed through `ScoreManager`.
- Drop scoring batched to a single popup event per cluster.
- `reset_game()` fully resets all subsystem singletons and tracking counters.
- `save_v6.json` extended with `high_score`, `playtime`, `total_shots`,
  `total_pops`, and `best_combo`.

### Fixed
- Score popup stacking (pool cap introduced).
- Five missing `MainWindow` update methods restored after refactor regression.
- Shot timer not restarting after `attach_bubble()`.
- Danger zone visuals not clearing on new game.

### Removed
- All Indonesian-language UI strings — interface is fully in English.
- Legacy `add_score()` as the primary scoring path.

---

## [5.2.0] — 2025

- Initial public release with core bubble-shooter mechanics, power-up system
  (`bubble_power.py`), graphics asset caching (`bubble_gfx.py`), and sound
  management (`bubble_fx.py`).
- Aim-assist guide line with wall-bounce prediction.
- Procedural nebula background generator with per-level color tinting.
- Auto-save on quit / return to menu; manual continue from save slot.

---

*Generated by the Macan Bubble Shooter development team.*
