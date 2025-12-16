# 🐯 Macan Bubble Shooter

A professional, full-featured bubble shooter game with a jungle/tiger theme built using PySide6. Features smooth animations, particle effects, and an immersive fullscreen experience.

![Macan Bubble Shooter](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🎮 Gameplay
- **Classic Bubble Shooter Mechanics**: Match 3 or more bubbles of the same color to pop them
- **Tiger Paw Shooter**: Unique tiger paw-shaped shooter cannon with smooth angle control
- **6 Vibrant Colors**: Colorful gradient bubbles with glow effects
- **Match Detection**: Intelligent bubble matching and floating bubble removal
- **Lives System**: 5 lives to complete the game
- **Scoring System**: 
  - 10 points per bubble in a match
  - 2x multiplier for matches of 5+ bubbles
  - 20 bonus points for each floating bubble removed

### 🎨 Visual Design
- **Fullscreen Immersive Experience**: Optimized for desktop displays
- **Jungle Theme**: Dark jungle background with decorative leaves
- **Smooth Animations**: Bubble shooting, collision, and popping effects
- **Particle Effects**: Explosion particles when bubbles pop
- **Gradient Bubbles**: Radial gradients with highlight and shadow effects
- **Modern HUD**: Professional score, level, and lives display

### 💾 Save/Load System
- **Auto-Save**: Game state automatically saved on exit
- **Persistent Storage**: Saves to `AppData/Local/MacanBubbleShooter/`
- **State Preservation**: Saves score, lives, level, and complete bubble grid layout
- **Auto-Load**: Automatically loads previous game state on startup

### 🎯 User Interface
- **Score Display**: Real-time score tracking
- **Level Indicator**: Current level display
- **Lives Counter**: Heart-based lives indicator
- **Pause Button**: Pause/resume gameplay
- **Restart Button**: Quick game restart
- **Quit Button**: Save and exit
- **Game Over Dialog**: Professional game over screen with final score

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- PySide6

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

## 🎮 How to Play

1. **Aim**: Move your mouse to aim the tiger paw shooter
2. **Shoot**: Click to shoot a bubble
3. **Match**: Match 3 or more bubbles of the same color
4. **Score**: Earn points by popping bubbles and removing floating groups
5. **Survive**: Don't let the bubbles reach the bottom or run out of lives!

### Controls
- **Mouse Movement**: Aim the shooter
- **Left Click**: Shoot bubble
- **Pause Button**: Pause/resume game
- **Restart Button**: Start a new game
- **Quit Button**: Save and exit

## 🏗️ Project Structure

```
macan-bubble-shooter/
│
├── macan_bubble_shooter.py    # Main game file
├── README.md                   # This file
└── AppData/Local/
    └── MacanBubbleShooter/
        └── save.json          # Auto-generated save file
```

## 🎨 Technical Features

### Graphics & Rendering
- **Anti-aliasing**: Smooth graphics rendering
- **Double buffering**: Flicker-free animations
- **60 FPS**: Smooth 16ms update cycle
- **Layered rendering**: Background, game objects, and particles on separate layers

### Game Mechanics
- **Hexagonal Grid**: Offset grid system for authentic bubble shooter layout
- **Collision Detection**: Precise bubble-to-bubble collision
- **Wall Bouncing**: Bubbles bounce off walls
- **Neighbor Detection**: Smart neighbor finding for match detection
- **Floating Detection**: Removes disconnected bubble groups

### Architecture
- **Model-View Architecture**: Clean separation of game logic and rendering
- **Signal-Slot Pattern**: Event-driven HUD updates
- **Scene Graph**: Efficient rendering with QGraphicsScene
- **State Management**: Comprehensive game state tracking

## 📸 Screenshot
<img width="1365" height="767" alt="Screenshot 2025-12-15 202516" src="https://github.com/user-attachments/assets/0fb52304-4bc9-4b9c-8ae0-3f6521556990" />
<img width="1365" height="762" alt="Screenshot 2025-12-15 202829" src="https://github.com/user-attachments/assets/b668ed31-3b3b-43e5-8837-15b41ee81299" />



## 📝 Changelog v3.7.0
- Added Caching System
- Optimize Code


## 🔧 Customization

### Modify Bubble Colors
Edit the `BUBBLE_COLORS` constant in the code:
```python
BUBBLE_COLORS = [
    (255, 100, 100),  # Red
    (100, 255, 100),  # Green
    (100, 100, 255),  # Blue
    # Add more colors...
]
```

### Adjust Difficulty
Modify constants:
```python
INITIAL_LIVES = 5    # Starting lives
ROWS = 10            # Number of bubble rows
COLS = 12            # Number of bubble columns
```

### Change Save Location
Modify the save directory:
```python
self.save_dir = Path.home() / "AppData" / "Local" / "MacanBubbleShooter"
```

## 🐛 Known Issues

- Ensure Python and PySide6 are properly installed
- Game requires OpenGL support for smooth rendering
- Save file uses JSON format - avoid manual editing

## 🚀 Future Enhancements

- [ ] Multiple difficulty levels
- [ ] Power-ups (bomb, color change, aim guide)
- [ ] High score leaderboard
- [ ] Sound effects and background music
- [ ] More themes (ocean, space, desert)
- [ ] Progressive difficulty with advancing levels
- [ ] Online multiplayer mode
- [ ] Achievement system
- [ ] Custom bubble skin editor

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 👤 Author


Project Link: [https://github.com/danx123/macan-bubble-shooter](https://github.com/danx123/macan-bubble-shooter)

## 🙏 Acknowledgments

- PySide6 framework for the excellent Qt bindings
- The bubble shooter game genre pioneers
- All contributors and testers


---

Made with ❤️ and Python 🐍

**Macan** means "Tiger" in Indonesian 🐯
