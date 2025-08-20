"""
Attack Injector for VirtuaPlant
Fault/attack injection module for mutating Modbus space
"""

import time
import random
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class AttackType(Enum):
    """Types of attacks that can be injected"""
    NEVER_STOP = "never_stop"
    STOP_ALL = "stop_all"
    CONSTANT_RUNNING = "constant_running"
    NOTHING_RUNS = "nothing_runs"
    MOVE_AND_FILL = "move_and_fill"
    STOP_AND_FILL = "stop_and_fill"
    RUN_NO_SPILL = "run_no_spill"
    SENSOR_SPOOFING = "sensor_spoofing"
    ACTUATOR_OVERRIDE = "actuator_override"
    RANDOM_NOISE = "random_noise"
    TIMING_ATTACK = "timing_attack"

@dataclass
class AttackConfig:
    """Configuration for an attack"""
    attack_type: AttackType
    target_plant: str
    duration: float = 60.0  # seconds
    intensity: float = 1.0  # 0.0 to 1.0
    target_tags: List[str] = None
    custom_values: Dict[str, Any] = None

class AttackInjector:
    """Attack injector for mutating Modbus space"""
    
    def __init__(self, modbus_bridge):
        self.modbus_bridge = modbus_bridge
        self.active_attacks = {}
        self.attack_threads = {}
        self.running = False
        
        # Attack patterns based on existing attack scripts
        self.attack_patterns = {
            AttackType.NEVER_STOP: self._attack_never_stop,
            AttackType.STOP_ALL: self._attack_stop_all,
            AttackType.CONSTANT_RUNNING: self._attack_constant_running,
            AttackType.NOTHING_RUNS: self._attack_nothing_runs,
            AttackType.MOVE_AND_FILL: self._attack_move_and_fill,
            AttackType.STOP_AND_FILL: self._attack_stop_and_fill,
            AttackType.RUN_NO_SPILL: self._attack_run_no_spill,
            AttackType.SENSOR_SPOOFING: self._attack_sensor_spoofing,
            AttackType.ACTUATOR_OVERRIDE: self._attack_actuator_override,
            AttackType.RANDOM_NOISE: self._attack_random_noise,
            AttackType.TIMING_ATTACK: self._attack_timing_attack
        }
    
    def start_attack(self, config: AttackConfig) -> str:
        """Start an attack with the given configuration"""
        attack_id = f"{config.attack_type.value}_{int(time.time())}"
        
        if attack_id in self.active_attacks:
            raise ValueError(f"Attack {attack_id} already running")
        
        self.active_attacks[attack_id] = config
        
        # Start attack thread
        thread = threading.Thread(
            target=self._run_attack,
            args=(attack_id, config),
            daemon=True
        )
        thread.start()
        self.attack_threads[attack_id] = thread
        
        print(f"🚨 Started attack: {config.attack_type.value} (ID: {attack_id})")
        return attack_id
    
    def stop_attack(self, attack_id: str):
        """Stop a specific attack"""
        if attack_id in self.active_attacks:
            del self.active_attacks[attack_id]
            print(f"✅ Stopped attack: {attack_id}")
        else:
            print(f"⚠️ Attack {attack_id} not found")
    
    def stop_all_attacks(self):
        """Stop all active attacks"""
        for attack_id in list(self.active_attacks.keys()):
            self.stop_attack(attack_id)
        print("🛑 All attacks stopped")
    
    def list_attacks(self) -> Dict[str, AttackConfig]:
        """List all active attacks"""
        return self.active_attacks.copy()
    
    def _run_attack(self, attack_id: str, config: AttackConfig):
        """Run an attack in a separate thread"""
        start_time = time.time()
        
        try:
            while (attack_id in self.active_attacks and 
                   time.time() - start_time < config.duration):
                
                # Execute attack pattern
                if config.attack_type in self.attack_patterns:
                    self.attack_patterns[config.attack_type](config)
                
                time.sleep(0.1)  # 10Hz attack rate
                
        except Exception as e:
            print(f"❌ Attack {attack_id} failed: {e}")
        finally:
            if attack_id in self.active_attacks:
                del self.active_attacks[attack_id]
    
    # Attack pattern implementations
    def _attack_never_stop(self, config: AttackConfig):
        """Never stop attack - keeps system running indefinitely"""
        if config.target_plant == "bottle":
            self.modbus_bridge.set_tag_value('CMD_RUN', True)
            self.modbus_bridge.set_tag_value('SENSOR_LIMIT_SWITCH', False)
            self.modbus_bridge.set_tag_value('SENSOR_LEVEL_SENSOR', False)
            self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', False)
        elif config.target_plant == "refinery":
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', True)
            self.modbus_bridge.set_tag_value('SENSOR_TANK_LEVEL', 0)
            self.modbus_bridge.set_tag_value('SENSOR_OIL_UPPER', False)
            self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', False)
            self.modbus_bridge.set_tag_value('ACT_WASTE_VALVE', False)
    
    def _attack_stop_all(self, config: AttackConfig):
        """Stop all attack - shuts down all systems"""
        if config.target_plant == "bottle":
            self.modbus_bridge.set_tag_value('CMD_RUN', False)
            self.modbus_bridge.set_tag_value('ACT_MOTOR', False)
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', False)
        elif config.target_plant == "refinery":
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', False)
            self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', False)
            self.modbus_bridge.set_tag_value('ACT_SEP_VALVE', False)
            self.modbus_bridge.set_tag_value('ACT_WASTE_VALVE', False)
    
    def _attack_constant_running(self, config: AttackConfig):
        """Constant running attack - keeps pumps running continuously"""
        if config.target_plant == "bottle":
            self.modbus_bridge.set_tag_value('CMD_RUN', True)
            self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
        elif config.target_plant == "refinery":
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', True)
            self.modbus_bridge.set_tag_value('SENSOR_TANK_LEVEL', 0)
            self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', False)
            self.modbus_bridge.set_tag_value('ACT_WASTE_VALVE', False)
    
    def _attack_nothing_runs(self, config: AttackConfig):
        """Nothing runs attack - prevents all systems from running"""
        if config.target_plant == "bottle":
            self.modbus_bridge.set_tag_value('CMD_RUN', False)
        elif config.target_plant == "refinery":
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', False)
    
    def _attack_move_and_fill(self, config: AttackConfig):
        """Move and fill attack - keeps motor running and nozzle open"""
        if config.target_plant == "bottle":
            self.modbus_bridge.set_tag_value('CMD_RUN', True)
            self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', True)
    
    def _attack_stop_and_fill(self, config: AttackConfig):
        """Stop and fill attack - stops motor but keeps nozzle open"""
        if config.target_plant == "bottle":
            self.modbus_bridge.set_tag_value('CMD_RUN', True)
            self.modbus_bridge.set_tag_value('ACT_MOTOR', False)
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', True)
    
    def _attack_run_no_spill(self, config: AttackConfig):
        """Run no spill attack - keeps processing but prevents spill detection"""
        if config.target_plant == "refinery":
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', True)
            self.modbus_bridge.set_tag_value('SENSOR_OIL_SPILL', 0)
    
    def _attack_sensor_spoofing(self, config: AttackConfig):
        """Sensor spoofing attack - manipulates sensor readings"""
        if config.target_plant == "bottle":
            # Spoof sensor readings using update_sensors (which handles read-only tables)
            if random.random() < config.intensity:
                self.modbus_bridge.update_sensors({
                    'SENSOR_LIMIT_SWITCH': random.choice([True, False]),
                    'SENSOR_LEVEL_SENSOR': random.choice([True, False])
                })
        elif config.target_plant == "refinery":
            # Spoof tank level using update_sensors
            if random.random() < config.intensity:
                fake_level = random.randint(0, 100)
                self.modbus_bridge.update_sensors({
                    'SENSOR_TANK_LEVEL': fake_level
                })
    
    def _attack_actuator_override(self, config: AttackConfig):
        """Actuator override attack - forces actuator states"""
        if config.target_plant == "bottle":
            if random.random() < config.intensity:
                self.modbus_bridge.set_tag_value('ACT_MOTOR', random.choice([True, False]))
                self.modbus_bridge.set_tag_value('ACT_NOZZLE', random.choice([True, False]))
        elif config.target_plant == "refinery":
            if random.random() < config.intensity:
                self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', random.choice([True, False]))
                self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', random.choice([True, False]))
    
    def _attack_random_noise(self, config: AttackConfig):
        """Random noise attack - injects random values into all tags"""
        all_tags = list(self.modbus_bridge.tag_mappings.keys())
        
        for tag in all_tags:
            if random.random() < config.intensity * 0.1:  # Lower probability
                mapping = self.modbus_bridge.tag_mappings[tag]
                if mapping['type'] == 'BOOL':
                    self.modbus_bridge.set_tag_value(tag, random.choice([True, False]))
                elif mapping['type'] == 'INT':
                    self.modbus_bridge.set_tag_value(tag, random.randint(0, 100))
    
    def _attack_timing_attack(self, config: AttackConfig):
        """Timing attack - manipulates timing of operations"""
        # This attack would need more sophisticated timing manipulation
        # For now, we'll just add random delays
        if random.random() < config.intensity:
            time.sleep(random.uniform(0.1, 0.5))

class AttackManager:
    """High-level attack manager for coordinating multiple attacks"""
    
    def __init__(self, modbus_bridge):
        self.injector = AttackInjector(modbus_bridge)
        self.attack_scenarios = self._define_scenarios()
    
    def _define_scenarios(self) -> Dict[str, List[AttackConfig]]:
        """Define predefined attack scenarios"""
        return {
            "bottle_chaos": [
                AttackConfig(AttackType.NEVER_STOP, "bottle", 30.0),
                AttackConfig(AttackType.SENSOR_SPOOFING, "bottle", 30.0, 0.5)
            ],
            "refinery_overflow": [
                AttackConfig(AttackType.CONSTANT_RUNNING, "refinery", 45.0),
                AttackConfig(AttackType.RUN_NO_SPILL, "refinery", 45.0)
            ],
            "sensor_manipulation": [
                AttackConfig(AttackType.SENSOR_SPOOFING, "bottle", 60.0, 0.8),
                AttackConfig(AttackType.SENSOR_SPOOFING, "refinery", 60.0, 0.8)
            ],
            "actuator_chaos": [
                AttackConfig(AttackType.ACTUATOR_OVERRIDE, "bottle", 40.0, 0.6),
                AttackConfig(AttackType.ACTUATOR_OVERRIDE, "refinery", 40.0, 0.6)
            ],
            "random_chaos": [
                AttackConfig(AttackType.RANDOM_NOISE, "bottle", 30.0, 0.3),
                AttackConfig(AttackType.RANDOM_NOISE, "refinery", 30.0, 0.3)
            ]
        }
    
    def run_scenario(self, scenario_name: str) -> List[str]:
        """Run a predefined attack scenario"""
        if scenario_name not in self.attack_scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        attack_ids = []
        for config in self.attack_scenarios[scenario_name]:
            attack_id = self.injector.start_attack(config)
            attack_ids.append(attack_id)
        
        print(f"🎭 Running scenario: {scenario_name} with {len(attack_ids)} attacks")
        return attack_ids
    
    def list_scenarios(self) -> List[str]:
        """List available attack scenarios"""
        return list(self.attack_scenarios.keys())
    
    def stop_all(self):
        """Stop all attacks"""
        self.injector.stop_all_attacks()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current attack status"""
        return {
            "active_attacks": len(self.injector.active_attacks),
            "attack_list": self.injector.list_attacks(),
            "available_scenarios": self.list_scenarios()
        }
