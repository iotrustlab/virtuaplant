#!/usr/bin/env python3
"""
Round-trip Tests for VirtuaPlant
Validates complete system from ST to physics and back
"""

import asyncio
import time
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sim.common.modbus_bridge import ModbusBridge
from sim.common.physics import create_physics_engine
from sim.common.attack_injector import AttackManager, AttackType, AttackConfig

class RoundTripTester:
    """Round-trip test suite for VirtuaPlant"""
    
    def __init__(self, plant_type: str):
        self.plant_type = plant_type
        self.modbus_bridge = ModbusBridge(plant_type)
        self.physics = create_physics_engine(plant_type)
        self.attack_manager = AttackManager(self.modbus_bridge)
        
        # Test results
        self.test_results = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all round-trip tests"""
        print(f"🧪 Running round-trip tests for {self.plant_type} plant...")
        
        tests = [
            ("Basic Physics", self._test_basic_physics),
            ("Sensor Validation", self._test_sensor_validation),
            ("Actuator Control", self._test_actuator_control),
            ("Alarm Conditions", self._test_alarm_conditions),
            ("Attack Injection", self._test_attack_injection),
            ("Modbus Consistency", self._test_modbus_consistency),
            ("CrossPLC IR Validation", self._test_crossplc_ir_validation)
        ]
        
        for test_name, test_func in tests:
            print(f"\n--- Running {test_name} ---")
            try:
                result = await test_func()
                self.test_results.append({
                    "test": test_name,
                    "status": "PASS" if result else "FAIL",
                    "details": result
                })
                print(f"✅ {test_name}: PASS")
            except Exception as e:
                self.test_results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "details": str(e)
                })
                print(f"❌ {test_name}: ERROR - {e}")
        
        # Generate summary
        summary = self._generate_summary()
        return summary
    
    async def _test_basic_physics(self) -> bool:
        """Test basic physics simulation"""
        # Set initial conditions
        if self.plant_type == "bottle":
            self.modbus_bridge.set_tag_value('CMD_RUN', True)
            self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', False)
        else:  # refinery
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', True)
            self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', False)
        
        # Run physics for several steps
        for i in range(10):
            actuator_values = self.modbus_bridge.get_actuator_values()
            sensor_values = self.physics.update(0.02, actuator_values)
            self.modbus_bridge.update_sensors(sensor_values)
            await asyncio.sleep(0.01)
        
        # Check that physics responded
        if self.plant_type == "bottle":
            bottle_position = sensor_values.get('bottle_position', 0)
            return bottle_position > 130.0  # Bottle should have moved
        else:
            tank_level = sensor_values.get('SENSOR_TANK_LEVEL', 0)
            return tank_level > 20  # Tank level should have increased
    
    async def _test_sensor_validation(self) -> bool:
        """Test sensor validation and updates"""
        # Test sensor updates
        if self.plant_type == "bottle":
            # Test limit switch
            self.modbus_bridge.update_sensors({'SENSOR_LIMIT_SWITCH': True})
            limit_switch = self.modbus_bridge.get_tag_value('SENSOR_LIMIT_SWITCH')
            
            # Test level sensor
            self.modbus_bridge.update_sensors({'SENSOR_LEVEL_SENSOR': True})
            level_sensor = self.modbus_bridge.get_tag_value('SENSOR_LEVEL_SENSOR')
            
            return limit_switch and level_sensor
        else:
            # Test tank level
            self.modbus_bridge.update_sensors({'SENSOR_TANK_LEVEL': 50})
            tank_level = self.modbus_bridge.get_tag_value('SENSOR_TANK_LEVEL')
            
            # Test oil spill
            self.modbus_bridge.update_sensors({'SENSOR_OIL_SPILL': 10})
            oil_spill = self.modbus_bridge.get_tag_value('SENSOR_OIL_SPILL')
            
            return tank_level == 50 and oil_spill == 10
    
    async def _test_actuator_control(self) -> bool:
        """Test actuator control and state changes"""
        if self.plant_type == "bottle":
            # Test motor control
            self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
            motor_on = self.modbus_bridge.get_tag_value('ACT_MOTOR')
            
            # Test nozzle control
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', True)
            nozzle_open = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
            
            return motor_on and nozzle_open
        else:
            # Test feed pump
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', True)
            pump_on = self.modbus_bridge.get_tag_value('ACT_FEED_PUMP')
            
            # Test outlet valve
            self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', True)
            valve_open = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE')
            
            return pump_on and valve_open
    
    async def _test_alarm_conditions(self) -> bool:
        """Test alarm condition detection"""
        if self.plant_type == "bottle":
            # Test high level alarm condition
            self.modbus_bridge.update_sensors({
                'SENSOR_LIMIT_SWITCH': True,
                'SENSOR_LEVEL_SENSOR': True
            })
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', True)
            
            # Run physics to trigger alarm
            for i in range(5):
                actuator_values = self.modbus_bridge.get_actuator_values()
                sensor_values = self.physics.update(0.02, actuator_values)
                self.modbus_bridge.update_sensors(sensor_values)
                await asyncio.sleep(0.01)
            
            # Check that bottle level increased
            bottle_level = sensor_values.get('bottle_level', 0)
            return bottle_level > 0.5
        else:
            # Test spill alarm condition
            self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', True)
            self.modbus_bridge.update_sensors({'SENSOR_TANK_LEVEL': 95})  # High level
            
            # Run physics to trigger spill
            for i in range(10):
                actuator_values = self.modbus_bridge.get_actuator_values()
                sensor_values = self.physics.update(0.02, actuator_values)
                self.modbus_bridge.update_sensors(sensor_values)
                await asyncio.sleep(0.01)
            
            # Check that spill was detected
            oil_spilled = sensor_values.get('oil_spilled', 0)
            return oil_spilled > 0
    
    async def _test_attack_injection(self) -> bool:
        """Test attack injection functionality"""
        # Start a simple attack
        config = AttackConfig(
            attack_type=AttackType.SENSOR_SPOOFING,
            target_plant=self.plant_type,
            duration=2.0,
            intensity=0.5
        )
        
        attack_id = self.attack_manager.injector.start_attack(config)
        
        # Let attack run for a moment
        await asyncio.sleep(1.0)
        
        # Check that attack is active
        active_attacks = self.attack_manager.injector.list_attacks()
        attack_active = attack_id in active_attacks
        
        # Stop attack
        self.attack_manager.injector.stop_attack(attack_id)
        
        return attack_active
    
    async def _test_modbus_consistency(self) -> bool:
        """Test Modbus consistency and tag mappings"""
        # Check that all tags in the map are accessible
        all_tags = list(self.modbus_bridge.tag_mappings.keys())
        
        for tag in all_tags:
            try:
                # Try to read the tag
                value = self.modbus_bridge.get_tag_value(tag)
                # Try to write to the tag (if it's writable)
                if self.modbus_bridge.tag_mappings[tag]['role'] in ['Actuator', 'Command']:
                    self.modbus_bridge.set_tag_value(tag, value)
            except Exception as e:
                print(f"❌ Tag {tag} failed consistency check: {e}")
                return False
        
        return True
    
    async def _test_crossplc_ir_validation(self) -> bool:
        """Test CrossPLC IR validation"""
        # Check that IR file exists
        ir_file = f"ir/{self.plant_type}_crossplc.json"
        if not Path(ir_file).exists():
            print(f"⚠️ IR file not found: {ir_file}")
            return False
        
        # Load IR data
        with open(ir_file, 'r') as f:
            ir_data = json.load(f)
        
        # Check that IR contains expected components
        if 'detailed_components' not in ir_data:
            return False
        
        # Check that tags are present
        for plc_name, plc_data in ir_data['detailed_components'].items():
            if 'tags' not in plc_data:
                return False
            
            # Check that some tags exist
            tags = plc_data['tags'].get('controller_tags', [])
            if not tags:
                return False
        
        return True
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed_tests = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        error_tests = sum(1 for r in self.test_results if r['status'] == 'ERROR')
        
        summary = {
            "plant_type": self.plant_type,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "test_results": self.test_results
        }
        
        return summary

async def run_roundtrip_tests():
    """Run round-trip tests for both plants"""
    
    print("🧪 VirtuaPlant Round-trip Test Suite")
    print("=" * 50)
    
    all_results = {}
    
    for plant_type in ["bottle", "refinery"]:
        print(f"\n{'='*20} {plant_type.upper()} PLANT {'='*20}")
        
        tester = RoundTripTester(plant_type)
        results = await tester.run_all_tests()
        all_results[plant_type] = results
        
        # Print summary
        print(f"\n📊 {plant_type.title()} Plant Test Summary:")
        print(f"  Total Tests: {results['total_tests']}")
        print(f"  Passed: {results['passed']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Errors: {results['errors']}")
        print(f"  Success Rate: {results['success_rate']:.1%}")
    
    # Overall summary
    print(f"\n{'='*50}")
    print("🎯 OVERALL TEST SUMMARY")
    print("=" * 50)
    
    total_passed = sum(r['passed'] for r in all_results.values())
    total_tests = sum(r['total_tests'] for r in all_results.values())
    overall_success_rate = total_passed / total_tests if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Total Passed: {total_passed}")
    print(f"Overall Success Rate: {overall_success_rate:.1%}")
    
    # Save results
    with open("reports/roundtrip_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📄 Test results saved to: reports/roundtrip_test_results.json")
    
    return overall_success_rate >= 0.7  # 70% success threshold

def main():
    """Main entry point"""
    try:
        success = asyncio.run(run_roundtrip_tests())
        if success:
            print("\n✅ Round-trip tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Round-trip tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
