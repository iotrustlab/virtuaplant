# VirtuaPlant

**VirtuaPlant** is a modern Industrial Control Systems (ICS) simulator that provides realistic physics-based simulation of industrial processes with integrated PLC control logic. It combines 2D physics simulation with real-time Modbus communication to create an immersive learning and testing platform for industrial cybersecurity and control systems.

## 🚀 Features

### 🌍 **Physics-Based Simulation**
- **Real-time 2D Physics**: Powered by Pymunk physics engine
- **Fluid Dynamics**: Realistic oil flow simulation with gravity and collision detection
- **Valve Control**: Dynamic valve barriers that physically block or allow flow
- **Sensor Integration**: Real-time level sensors and process monitoring

### 🔧 **PLC Integration**
- **OpenPLC Runtime**: Full IEC 61131-3 Structured Text (ST) support
- **Modbus/TCP Communication**: Real-time tag reading/writing
- **Safety Systems**: SIS (Safety Instrumented System) with LSHH protection
- **CrossPLC IR Analysis**: Program validation and control flow analysis

### 🎮 **Interactive Visualization**
- **Real-time GUI**: Pygame-based frontend with live process visualization
- **Multi-Plant Support**: Oil refinery and bottle filling plant simulations
- **CLI Interface**: Command-line tools for automation and testing
- **Attack Simulation**: Built-in attack injection capabilities

## 🏭 Supported Plants

### Oil Refinery Plant
- **Process**: Oil storage, separation, and waste management
- **Safety**: High-high level protection (LSHH) with latched trip
- **Control**: 4-phase operation (Idle, Filling, Processing, Emptying)
- **Sensors**: Level sensors, flow meters, pressure indicators
- **Actuators**: Inlet/outlet valves, feed pump, separator/waste valves

### Bottle Filling Plant
- **Process**: Automated bottle filling with conveyor system
- **Control**: Fill level control with overflow protection
- **Sensors**: Bottle presence, fill level, conveyor position
- **Actuators**: Fill valves, conveyor motors, emergency stops

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Git

### Quick Start
```bash
# Clone the repository
git clone https://github.com/iotrustlab/virtuaplant.git
cd virtuaplant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_modern.txt
```

### Dependencies
- **Physics**: `pymunk` - 2D physics engine
- **GUI**: `pygame` - Game development library
- **Communication**: `pymodbus` - Modbus protocol implementation
- **Analysis**: `networkx`, `matplotlib` - Graph analysis and visualization
- **Validation**: `jsonschema` - Configuration validation

## 🎯 Usage

### Running Simulations

#### Oil Refinery Plant
```bash
# Start the oil refinery simulation with GUI
python sim/cli.py refinery --gui --improved

# Run in headless mode for automation
python sim/cli.py refinery --headless
```

#### Bottle Filling Plant
```bash
# Start the bottle filling simulation
python sim/cli.py bottle --gui --improved
```

### OpenPLC Integration
```bash
# Compile ST programs (requires OpenPLC runtime)
cd /path/to/OpenPLC_v3/webserver
./scripts/compile_program.sh Main.st

# Start OpenPLC runtime
./openplc
```

### Analysis Tools
```bash
# Validate modbus mappings
python tools/validate_map.py

# Export IR analysis
python tools/export_ir_analysis.py

# Run round-trip tests
python tools/roundtrip_tests.py
```

## 📁 Project Structure

```
virtuaplant/
├── sim/                    # Simulation engine
│   ├── cli.py             # Command-line interface
│   ├── common/            # Shared components
│   │   ├── physics.py     # Physics engine wrapper
│   │   ├── modbus_bridge.py # Modbus communication
│   │   └── attack_injector.py # Attack simulation
│   ├── ui/                # User interface
│   │   └── improved_pygame_frontend.py # Main GUI
│   ├── refinery/          # Oil refinery plant
│   └── bottle/            # Bottle filling plant
├── openplc/               # OpenPLC ST programs
│   ├── refinery/          # Oil refinery PLC logic
│   └── bottle/            # Bottle filling PLC logic
├── maps/                  # Modbus address mappings
│   ├── refinery/          # Oil refinery tags
│   └── bottle/            # Bottle filling tags
├── ir/                    # CrossPLC IR analysis
│   └── graphs/            # Control flow graphs
├── tools/                 # Analysis and validation tools
├── policy/                # Tag management policies
└── requirements_modern.txt # Python dependencies
```

## 🔌 Modbus Communication

### Tag Structure
- **Input Registers**: Sensor readings (level, pressure, temperature)
- **Holding Registers**: Setpoints and configuration
- **Coils**: Binary actuators (valves, pumps, motors)
- **Discrete Inputs**: Binary sensors (alarms, status indicators)

### Example Tags (Oil Refinery)
```csv
Tag Name,Type,Table,Address,Description
LT_TANK_LEVEL_PCT,REAL,IR,1000,Tank level percentage
ACT_INLET_VALVE,BOOL,CO,100,Inlet valve control
SIS_TANK_LSHH,BOOL,DI,200,High-high level alarm
CMD_SIS_RESET,BOOL,CO,201,SIS reset command
```

## 🛡️ Safety Systems

### SIS (Safety Instrumented System)
- **LSHH Protection**: High-high level detection with latched trip
- **Manual Reset**: Requires explicit reset command after trip
- **Independent Logic**: Separate from normal BPCS control
- **Fail-Safe Design**: Valves fail closed on system failure

### BPCS (Basic Process Control System)
- **Band Control**: Normal level control within safe limits
- **Process Routing**: Automatic diversion to slop/API separator
- **Alarm Management**: Comprehensive alarm and status reporting

## 🧪 Testing and Validation

### Physics Testing
```bash
# Test physics simulation
python test_physics.py

# Test GUI components
python test_gui.py
```

### PLC Logic Testing
```bash
# Test PLC control logic
python test_plc_logic.py

# Validate modbus mappings
python tools/validate_map.py
```

### Round-trip Testing
```bash
# Comprehensive system testing
python tools/roundtrip_tests.py
```

## 🔬 Research and Development

### CrossPLC IR Analysis
- **Control Flow Graphs**: Visual representation of PLC logic
- **Data Flow Analysis**: Tag usage and dependencies
- **Semantic Analysis**: Program behavior understanding
- **Validation**: Syntax and logic error detection

### Attack Simulation
- **Tag Manipulation**: Direct modbus tag modification
- **Protocol Attacks**: Modbus-specific attack vectors
- **Physics-Based Validation**: Real-world consequence simulation
- **Safety System Testing**: SIS response to malicious inputs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 Python style guidelines
- Add comprehensive docstrings
- Include unit tests for new features
- Update documentation for API changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Pymunk**: 2D physics engine for realistic simulation
- **OpenPLC**: Open-source PLC runtime
- **PyModbus**: Modbus protocol implementation
- **CrossPLC**: PLC program analysis framework

## 📞 Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check the documentation in the `docs/` directory
- Review the testing guide for troubleshooting

---

**VirtuaPlant** - Bridging the gap between cybersecurity and industrial control systems through realistic physics simulation. 🏭🔒
