"""
Common Physics Module for VirtuaPlant
Implements deterministic physics equations for bottle filling and oil refinery plants
"""

import math
from typing import Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class PhysicsState:
    """Base physics state for all plants"""
    time: float = 0.0
    dt: float = 0.02  # 50 FPS default

class BottleFillingPhysics:
    """Physics simulation for bottle filling plant"""
    
    def __init__(self):
        # Physics constants
        self.k_pump = 0.1      # Water flow rate when pump is on
        self.k_drain = 0.05    # Drain rate when valve is open
        self.leak_rate = 0.001 # Constant leak rate
        self.gravity = 9.81    # Gravity constant
        
        # State variables
        self.bottle_level = 0.0
        self.bottle_position = 0.0
        self.water_flow = 0.0
        self.bottle_in_position = False
        self.bottle_filled = False
        
        # Physics state
        self.state = PhysicsState()
    
    def update(self, dt: float, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Update physics simulation for one timestep"""
        
        self.state.dt = dt
        self.state.time += dt
        
        # Get inputs from Modbus
        motor_on = inputs.get('ACT_MOTOR', False)
        nozzle_open = inputs.get('ACT_NOZZLE', False)
        limit_switch = inputs.get('SENSOR_LIMIT_SWITCH', False)
        level_sensor = inputs.get('SENSOR_LEVEL_SENSOR', False)
        
        # Update bottle position based on motor
        if motor_on:
            self.bottle_position += 0.25 * dt  # Conveyor speed
        
        # Update bottle level based on nozzle and physics
        if nozzle_open and self.bottle_in_position:
            # Water flow into bottle
            self.bottle_level += self.k_pump * dt
            self.water_flow = self.k_pump
        else:
            # Natural drain/leak
            if self.bottle_level > 0:
                self.bottle_level -= self.k_drain * dt
                self.bottle_level -= self.leak_rate * dt
                self.bottle_level = max(0.0, self.bottle_level)
            self.water_flow = 0.0
        
        # Update sensor states based on physics
        # Limit switch: bottle in position
        self.bottle_in_position = (130 <= self.bottle_position <= 200)
        
        # Level sensor: bottle filled
        self.bottle_filled = (self.bottle_level >= 0.8)  # 80% full threshold
        
        # Reset bottle when it moves off screen
        if self.bottle_position > 600:
            self.bottle_position = 130
            self.bottle_level = 0.0
        
        # Return updated sensor values
        return {
            'SENSOR_LIMIT_SWITCH': self.bottle_in_position,
            'SENSOR_LEVEL_SENSOR': self.bottle_filled,
            'bottle_level': self.bottle_level,
            'bottle_position': self.bottle_position,
            'water_flow': self.water_flow
        }

class OilRefineryPhysics:
    """Physics simulation for oil refinery plant"""
    
    def __init__(self):
        # Physics constants
        self.k_feed = 0.2      # Oil feed rate when pump is on
        self.k_relief = 0.15   # Relief valve flow rate
        self.k_processing = 0.1 # Processing rate
        self.tank_capacity = 100.0  # Tank capacity in liters
        
        # State variables
        self.tank_level = 20.0  # Start at 20%
        self.oil_spilled = 0.0
        self.oil_processed = 0.0
        self.processing_phase = 0  # 0=idle, 1=filling, 2=processing, 3=emptying
        
        # Physics state
        self.state = PhysicsState()
    
    def update(self, dt: float, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Update physics simulation for one timestep"""
        
        self.state.dt = dt
        self.state.time += dt
        
        # Get inputs from Modbus
        feed_pump_on = inputs.get('ACT_FEED_PUMP', False)
        outlet_valve_open = inputs.get('ACT_OUTLET_VALVE', False)
        sep_valve_open = inputs.get('ACT_SEP_VALVE', False)
        waste_valve_open = inputs.get('ACT_WASTE_VALVE', False)
        
        # Update tank level based on feed pump
        if feed_pump_on:
            self.tank_level += self.k_feed * dt
            self.tank_level = min(self.tank_capacity, self.tank_level)
        
        # Update based on processing phase
        if self.processing_phase == 1:  # Filling
            if self.tank_level >= 80:  # 80% threshold
                self.processing_phase = 2
        elif self.processing_phase == 2:  # Processing
            if outlet_valve_open and sep_valve_open:
                # Process oil
                process_rate = min(self.k_processing * dt, self.tank_level)
                self.tank_level -= process_rate
                self.oil_processed += process_rate
        elif self.processing_phase == 3:  # Emptying
            if waste_valve_open:
                # Empty tank
                empty_rate = self.k_relief * dt
                self.tank_level -= empty_rate
                self.tank_level = max(0.0, self.tank_level)
                
                if self.tank_level <= 20:  # Back to idle
                    self.processing_phase = 0
        
        # Check for spills (overflow)
        if self.tank_level > self.tank_capacity:
            spill_amount = self.tank_level - self.tank_capacity
            self.oil_spilled += spill_amount
            self.tank_level = self.tank_capacity
        
        # Update sensor values
        tank_level_percent = int((self.tank_level / self.tank_capacity) * 100)
        oil_upper_sensor = (self.tank_level > 90)  # Upper level sensor
        
        return {
            'SENSOR_TANK_LEVEL': tank_level_percent,
            'SENSOR_OIL_SPILL': int(self.oil_spilled),
            'SENSOR_OIL_PROCESSED': int(self.oil_processed),
            'SENSOR_OIL_UPPER': oil_upper_sensor,
            'tank_level': self.tank_level,
            'oil_spilled': self.oil_spilled,
            'oil_processed': self.oil_processed,
            'processing_phase': self.processing_phase
        }

def create_physics_engine(plant_type: str) -> Any:
    """Factory function to create appropriate physics engine"""
    if plant_type == "bottle":
        return BottleFillingPhysics()
    elif plant_type == "refinery":
        return OilRefineryPhysics()
    else:
        raise ValueError(f"Unknown plant type: {plant_type}")


