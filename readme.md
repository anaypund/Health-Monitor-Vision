# Vision-Based PC User Health Monitoring Software

## Overview
A Python desktop application that uses computer vision to passively monitor a PC user via the device camera to improve physical health, eye safety, posture, and work habits in a non-intrusive and ethical manner.

The software acts as a continuous ergonomic and wellness observer - a silent coach - that:
- Reduces eye strain and fatigue
- Prevents long-term posture-related issues
- Encourages healthier work rhythms
- Provides actionable insights rather than raw data

## Project Architecture

```
├── main.py                      # Main GUI application with Tkinter
├── src/
│   ├── __init__.py
│   ├── vision_engine.py         # Core MediaPipe facial landmark detection
│   ├── eye_tracker.py           # Eye blink detection and strain scoring
│   ├── posture_analyzer.py      # Head/shoulder posture analysis
│   ├── alert_system.py          # Intelligent notification system
│   ├── screen_time_tracker.py   # Screen time and break management
│   ├── data_logger.py           # Historical data logging
│   └── health_monitor.py        # Central monitoring engine
├── data/                        # Historical health data storage
│   ├── snapshots/               # Daily health snapshots
│   ├── summaries/               # Daily summaries
│   └── baselines.json           # Personalized user baselines
└── replit.md                    # This file
```

## Key Features

### 1. Eye Blink Detection & Eye Health
- Uses MediaPipe 478-point face mesh for precise eye landmark tracking
- Calculates Eye Aspect Ratio (EAR) for blink detection
- Monitors blink rate against healthy baselines (12-20 blinks/min)
- Generates eye strain risk scores based on:
  - Blink frequency
  - Time since last blink
  - Eye openness patterns

### 2. Posture Analysis
- Tracks head pitch, yaw, and roll angles
- Detects forward head posture and slouching
- Estimates distance from screen using facial geometry
- Duration-based alerts (avoids false positives from brief movements)

### 3. Intelligent Alert System
- Context-aware notifications with cooldown periods
- Escalating severity (INFO → WARNING → CRITICAL)
- Desktop notifications via plyer
- Specific recommendations for each issue type

### 4. Screen Time Tracking
- Tracks continuous work sessions
- Implements 20-20-20 rule (micro breaks)
- Recommends short (5 min) and long (15 min) breaks
- Face detection for presence awareness

### 5. Personalized Baseline Learning
- Calibrates to user's natural posture during first 30 seconds
- Learns personal blink rate over 2 minutes
- Adapts thresholds based on individual patterns
- Stores historical data for trend analysis

## Technology Stack
- **Python 3.11**
- **MediaPipe**: 478-point 3D facial landmark detection
- **OpenCV**: Camera capture and image processing
- **Tkinter**: Desktop GUI framework
- **NumPy/Pandas**: Data processing and analysis
- **Pillow**: Image display in GUI
- **plyer**: Cross-platform desktop notifications

## Running the Application
The application runs as a desktop GUI. Click "Start Monitoring" to begin webcam-based health monitoring.

## Ethical Considerations
- Camera processing focuses only on required facial landmarks
- No biometric data stored unnecessarily
- Functions as a health aid, not surveillance
- User can pause alerts at any time
- All data stored locally
