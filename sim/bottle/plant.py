"""
Bottle Filling Plant Simulator
Integrates physics simulation with Modbus bridge
"""

import asyncio
import time
from typing import Dict, Any
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from sim.common.physics import BottleFillingPhysics
from sim.common.modbus_bridge import ModbusBridge

class BottleFillingPlant:
    """Bottle filling plant simulator"""
    
    def __init__(self, modbus_port: int = 5020):
        self.modbus_port = modbus_port
        self.physics = BottleFillingPhysics()
        self.modbus_bridge = ModbusBridge("bottle")
        self.running = False
        self.simulation_time = 0.0
        self.dt = 0.02  # 50 FPS
        
    async def start(self):
        """Start the plant simulation"""
        print("Starting Bottle Filling Plant Simulator...")
        self.running = True
        
        # Start Modbus server
        from pymodbus.server import StartTcpServer
        from pymodbus.device import ModbusDeviceIdentification
        
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'VirtuaPlant'
        identity.ProductCode = 'BFP'
        identity.VendorUrl = 'https://github.com/virtuaplant'
        identity.ProductName = 'Bottle Filling Plant'
        identity.ModelName = 'BFP-1000'
        identity.MajorMinorRevision = '1.0'
        
        # Start Modbus server in background
        server_task = asyncio.create_task(
            StartTcpServer(
                self.modbus_bridge.get_context(),
                identity=identity,
                address=("localhost", self.modbus_port)
            )
        )
        
        print(f"Modbus server started on localhost:{self.modbus_port}")
        
        # Main simulation loop
        try:
            while self.running:
                await self._simulation_step()
                await asyncio.sleep(self.dt)
        except KeyboardInterrupt:
            print("\nStopping simulation...")
        finally:
            self.running = False
            server_task.cancel()
    
    async def _simulation_step(self):
        """Execute one simulation step"""
        # Get current actuator values from Modbus
        actuator_values = self.modbus_bridge.get_actuator_values()
        
        # Update physics simulation
        sensor_values = self.physics.update(self.dt, actuator_values)
        
        # Update Modbus sensor values
        self.modbus_bridge.update_sensors(sensor_values)
        
        # Update simulation time
        self.simulation_time += self.dt
        
        # Print status every 5 seconds
        if int(self.simulation_time) % 5 == 0 and self.simulation_time > 0:
            self._print_status(sensor_values, actuator_values)
    
    def _print_status(self, sensor_values: Dict[str, Any], actuator_values: Dict[str, Any]):
        """Print current plant status"""
        print(f"\n--- Bottle Filling Plant Status (t={self.simulation_time:.1f}s) ---")
        print(f"Bottle Level: {sensor_values.get('bottle_level', 0):.2f}")
        print(f"Bottle Position: {sensor_values.get('bottle_position', 0):.1f}")
        print(f"Water Flow: {sensor_values.get('water_flow', 0):.2f}")
        print(f"Limit Switch: {sensor_values.get('SENSOR_LIMIT_SWITCH', False)}")
        print(f"Level Sensor: {sensor_values.get('SENSOR_LEVEL_SENSOR', False)}")
        print(f"Motor: {actuator_values.get('ACT_MOTOR', False)}")
        print(f"Nozzle: {actuator_values.get('ACT_NOZZLE', False)}")
        print(f"Run Command: {actuator_values.get('CMD_RUN', False)}")
    
    def stop(self):
        """Stop the plant simulation"""
        self.running = False

async def main():
    """Main entry point"""
    plant = BottleFillingPlant()
    await plant.start()

if __name__ == "__main__":
    asyncio.run(main())
