# Rule-Consistency Auditor - Complete Guide

## 📋 Project Overview

**Rule-Consistency Auditor (RCA)** is a system to verify compliance with traffic rules in the CARLA simulator. The project monitors the behavior of a vehicle against rules defined through **state machines**, detecting violations, signaling warnings and generating detailed logs.

**Main objectives:**
- Implement traffic rules as state machines (states + transitions)
- Monitor vehicle behavior in CARLA in real-time
- Detect violations (traffic lights, stop signs, lane markings, safe distance)
- Record violations and generate reports

---

## 📦 Dependencies and Installation

**Required Python packages** (`requirements.txt`):
```
carla              # CARLA Simulator
numpy              # Numerical operations
pygame             # Graphics rendering and input
pyyaml             # YAML rule parsing
pytest             # Testing framework
datetime           # Timestamps
nicegui            # Rule editor GUI
pywebview
```

**Installation steps:**
```bash
git clone https://github.com/BestSolutionSavvy/SVS-26
```

---

## 🏗️ Project Architecture

```
ROOT
├── carla_bindings.py       # CARLA binding + DataBinder (sensor data access)
├── rca.ipynb               # Main notebook - entry point
├── admin/                  # Rule editor (UI for creating rules)
│   ├── rule_editor.py      # Desktop interface (NiceGUI)
│   ├── mermaid_to_yaml.py  # Converter: Mermaid → YAML
│   ├── yaml_to_mermaid.py  # Converter: YAML → Mermaid
│   └── rules/              # Rule repository (YAML files)
│       ├── stop.yaml
│       ├── lane_keeping_continuous.yaml
│       ├── lane_keeping_dashed.yaml
│       ├── safe_distance.yaml
│       └── right_of_way.yaml
├── controller/
│   └── state_machine.py    # StateMachine engine
├── models/                 # Data models
│   ├── rule.py            # Rule class (transitions + constants)
│   ├── state.py           # State class (idle/warning/violation)
│   └── transition.py      # Transition class (conditions)
├── utils/
│   ├── parsing_utils.py   # YAML parsing → Rule objects
│   ├── carla_utils.py     # CARLA helpers (spawn, connect)
│   └── violation_logger.py # ViolationLogger (violation logging)
├── view/
│   ├── pygame_display.py  # Camera rendering + input handling
│   ├── hud_drawer.py      # HUD notifications
│   ├── input_handler.py   # Keyboard/joystick input
│   └── test/
│       ├── hud_demo.py
│       └── rule_scenarios.py
└── tests/
    ├── test_state_machine.py
    ├── test_transition.py
    ├── test_carla_bindings.py
    ├── test_parsing_utils.py
    ├── test_violation_logger.py
    └── conftest.py
```

---

## 🚀 How to Launch the Project

1. **Prerequisites:**
   - CARLA server must be installed and running on your machine

2. **Conda enviroment**
   - conda create -n carla-env python=3.7
   - conda activate carla-env
   - pip install -r requirements.txt

3. **Jupyter notebook:**

4. **Controls:**

   **Keyboard:**
   - **W** - Accelerate (forward)
   - **A** - Steer left
   - **D** - Steer right
   - **S** - Brake (hard stop)
   - **R** - Toggle reverse gear
   - **← / →** (arrow keys) - Toggle left / right blinker
   - **Q / ESC** - Exit simulation

   **Gamepad/Joystick:**
   - **Left Analog Stick (X)** - Steering (normalized)
   - **LT (Left Trigger)** - Throttle / Accelerate
   - **RT (Right Trigger)** - Brake
   - **A Button** - Toggle reverse gear
   - **B Button** - Hazard lights (both blinkers)
   - **LB (Left Paddle)** - Left blinker
   - **RB (Right Paddle)** - Right blinker

---

## 📋 Defined Rules (`admin/rules/`)

Rules are YAML files describing state machines in Mermaid-compliant format:

**Example: `stop.yaml`**
```yaml
metadata:
  title: Stop
  constants:
    warning_threshold: 10
    stop_threshold: 2
    stop_departure_speed: 0.5

state_machine:
  initial_state: idle
  states: [idle, warning, stopped, violation]
  transitions:
    - from: idle
      to: warning
      condition: "distance_to_sign <= 10 and distance_to_sign > 2"
    
    - from: warning
      to: stopped
      condition: "ego_speed == 0.0 and distance_to_sign <= 2"
    
    - from: warning
      to: violation
      condition: "ego_speed > 0.0 and distance_to_sign <= 0.0"
    
    - from: stopped
      to: idle
      condition: "ego_speed >= 0.5"
```

**Available rules:**
1. **stop.yaml** - Behavior at stop signs
2. **lane_keeping_continuous.yaml** - Don't cross solid line
3. **lane_keeping_dashed.yaml** - Distance from dashed line
4. **safe_distance.yaml** - Maintain safe distance
5. **right_of_way.yaml** - Give right of way

---

## 🛠️ Admin Rule Editor (`admin/`)

To **create/modify rules graphically**:

```bash
cd admin/
conda create -n rule-editor python=3.11
conda activate rule-editor
pip install -r requirements.txt
python rule_editor.py
```

**Features:**
- Visual Mermaid editor on the left
- Diagram preview on the right
- Save → automatically converts to YAML
- Load → loads YAML and converts to Mermaid for editing

---

## 📈 Program Output

**Generated log files:**
```
logs/
├── violation_20260604_143022.json
├── violation_20260604_143115.json
└── ...
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v
```

---

## 👥 Authors

- Francesco Buda, francesco.buda3@studio.unibo.it
- Emanuele Sanchi, emanuele.sanchi@studio.unibo.it
- Tommaso Severi, tommaso.severi2@studio.unibo.it

