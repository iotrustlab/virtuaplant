"""
Oil Refinery Plant Simulator
Integrates physics simulation with Modbus bridge
"""

import asyncio
import time
from typing import Dict, Any
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from sim.common.physics import OilRefineryPhysics
from sim.common.modbus_bridge import ModbusBridge

class OilRefineryPlant:
    """Oil refinery plant simulator"""
    
    def __init__(self, modbus_port: int = 5021):
        self.modbus_port = modbus_port
        self.physics = OilRefineryPhysics()
        self.modbus_bridge = ModbusBridge("refinery")
        self.running = False
        self.simulation_time = 0.0
        self.dt = 0.02  # 50 FPS
        
    async def start(self):
        """Start the plant simulation"""
        print("Starting Oil Refinery Plant Simulator...")
        self.running = True
        
        # Start Modbus server
        from pymodbus.server import StartTcpServer
        from pymodbus.device import ModbusDeviceIdentification
        
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'VirtuaPlant'
        identity.ProductCode = 'ORP'
        identity.VendorUrl = 'https://github.com/virtuaplant'
        identity.ProductName = 'Oil Refinery Plant'
        identity.ModelName = 'ORP-2000'
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
        print(f"\n--- Oil Refinery Plant Status (t={self.simulation_time:.1f}s) ---")
        print(f"Tank Level: {sensor_values.get('SENSOR_TANK_LEVEL', 0)}%")
        print(f"Oil Spilled: {sensor_values.get('SENSOR_OIL_SPILL', 0)}L")
        print(f"Oil Processed: {sensor_values.get('SENSOR_OIL_PROCESSED', 0)}L")
        print(f"Upper Sensor: {sensor_values.get('SENSOR_OIL_UPPER', False)}")
        print(f"Processing Phase: {sensor_values.get('processing_phase', 0)}")
        print(f"Feed Pump: {actuator_values.get('ACT_FEED_PUMP', False)}")
        print(f"Outlet Valve: {actuator_values.get('ACT_OUTLET_VALVE', False)}")
        print(f"Sep Valve: {actuator_values.get('ACT_SEP_VALVE', False)}")
        print(f"Waste Valve: {actuator_values.get('ACT_WASTE_VALVE', False)}")
    
    def stop(self):
        """Stop the plant simulation"""
        self.running = False

async def main():
    """Main entry point"""
    plant = OilRefineryPlant()
    await plant.start()

if __name__ == "__main__":
    asyncio.run(main())
