"""
Modbus Bridge for VirtuaPlant
Loads modbus_map.csv and validates tag mappings using CrossPLC IR
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext

class ModbusBridge:
    """Modbus bridge that validates and manages tag mappings"""
    
    def __init__(self, plant_type: str):
        self.plant_type = plant_type
        self.map_file = f"maps/{plant_type}/modbus_map.csv"
        self.ir_file = f"ir/{plant_type}_crossplc.json"
        
        # Load and validate the modbus map
        self.tag_mappings = self._load_modbus_map()
        self.ir_data = self._load_ir_data()
        
        # Validate mappings against IR
        self._validate_mappings()
        
        # Initialize Modbus context
        self.context = self._create_modbus_context()
    
    def _load_modbus_map(self) -> Dict[str, Dict[str, Any]]:
        """Load modbus map from CSV file"""
        mappings = {}
        
        if not Path(self.map_file).exists():
            raise FileNotFoundError(f"Modbus map file not found: {self.map_file}")
        
        with open(self.map_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tag_name = row['name']
                mappings[tag_name] = {
                    'type': row['type'],
                    'table': row['table'],
                    'address': int(row['address']),
                    'width': int(row['width']) if row['width'] else 1,
                    'units': row['units'],
                    'desc': row['desc'],
                    'role': row['role']
                }
        
        return mappings
    
    def _load_ir_data(self) -> Optional[Dict[str, Any]]:
        """Load CrossPLC IR data"""
        if not Path(self.ir_file).exists():
            print(f"Warning: IR file not found: {self.ir_file}")
            return None
        
        with open(self.ir_file, 'r') as f:
            return json.load(f)
    
    def _validate_mappings(self):
        """Validate tag mappings against CrossPLC IR"""
        if not self.ir_data:
            print("Warning: Skipping IR validation (no IR data)")
            return
        
        # Extract tags from IR
        ir_tags = set()
        for plc_name, plc_data in self.ir_data.get('detailed_components', {}).items():
            if 'tags' in plc_data:
                for tag in plc_data['tags'].get('controller_tags', []):
                    ir_tags.add(tag['name'])
        
        # Check for missing mappings
        missing_tags = []
        for tag_name in ir_tags:
            if tag_name not in self.tag_mappings:
                missing_tags.append(tag_name)
        
        if missing_tags:
            print(f"Warning: Tags in IR but not in modbus map: {missing_tags}")
        
        # Check for unmapped tags
        unmapped_tags = []
        for tag_name in self.tag_mappings:
            if tag_name not in ir_tags:
                unmapped_tags.append(tag_name)
        
        if unmapped_tags:
            print(f"Warning: Tags in modbus map but not in IR: {unmapped_tags}")
        
        # Validate role compliance
        for tag_name, mapping in self.tag_mappings.items():
            if not self._validate_tag_role(tag_name, mapping):
                print(f"Error: Tag '{tag_name}' role validation failed")
                sys.exit(1)
    
    def _validate_tag_role(self, tag_name: str, mapping: Dict[str, Any]) -> bool:
        """Validate that tag follows role policy"""
        role = mapping['role']
        
        # Check prefix-based role assignment
        if tag_name.startswith('SENSOR_') and role != 'Sensor':
            print(f"Error: Tag '{tag_name}' should have role 'Sensor' but has '{role}'")
            return False
        
        if tag_name.startswith('ACT_') and role != 'Actuator':
            print(f"Error: Tag '{tag_name}' should have role 'Actuator' but has '{role}'")
            return False
        
        if tag_name.startswith('CMD_') and role != 'Command':
            print(f"Error: Tag '{tag_name}' should have role 'Command' but has '{role}'")
            return False
        
        return True
    
    def _create_modbus_context(self) -> ModbusServerContext:
        """Create Modbus context with proper table mappings"""
        
        # Initialize data blocks
        di_block = ModbusSequentialDataBlock(0, [0] * 100)  # Discrete Inputs
        co_block = ModbusSequentialDataBlock(0, [0] * 100)  # Coils
        hr_block = ModbusSequentialDataBlock(0, [0] * 100)  # Holding Registers
        ir_block = ModbusSequentialDataBlock(0, [0] * 100)  # Input Registers
        
        # Create server context with data blocks
        context = ModbusServerContext(
            devices={
                0: {
                    'di': di_block,
                    'co': co_block,
                    'hr': hr_block,
                    'ir': ir_block
                }
            },
            single=True
        )
        
        return context
    
    def get_tag_value(self, tag_name: str) -> Any:
        """Get tag value from Modbus context"""
        if tag_name not in self.tag_mappings:
            raise ValueError(f"Unknown tag: {tag_name}")
        
        mapping = self.tag_mappings[tag_name]
        table = mapping['table']
        address = mapping['address']
        
        # Map table names to Modbus function codes
        table_map = {
            'DI': 2,   # Read Discrete Inputs
            'COIL': 1, # Read Coils
            'HR': 3,   # Read Holding Registers
            'IR': 4    # Read Input Registers
        }
        
        if table not in table_map:
            raise ValueError(f"Unknown table: {table}")
        
        # Access the data block directly
        if table == 'DI':
            return self.context[0][0]['di'].getValues(address, 1)[0]
        elif table == 'COIL':
            return self.context[0][0]['co'].getValues(address, 1)[0]
        elif table == 'HR':
            return self.context[0][0]['hr'].getValues(address, 1)[0]
        elif table == 'IR':
            return self.context[0][0]['ir'].getValues(address, 1)[0]
        else:
            return 0
    
    def set_tag_value(self, tag_name: str, value: Any):
        """Set tag value in Modbus context"""
        if tag_name not in self.tag_mappings:
            raise ValueError(f"Unknown tag: {tag_name}")
        
        mapping = self.tag_mappings[tag_name]
        table = mapping['table']
        address = mapping['address']
        
        # Map table names to Modbus function codes for writing
        table_map = {
            'COIL': 5,   # Write Single Coil
            'HR': 6,     # Write Single Register
        }
        
        # Set values directly in the data block
        if table == 'COIL':
            self.context[0][0]['co'].setValues(address, [value])
        elif table == 'HR':
            self.context[0][0]['hr'].setValues(address, [value])
        else:
            raise ValueError(f"Cannot write to table: {table}")
    
    def update_sensors(self, sensor_values: Dict[str, Any]):
        """Update sensor values in Modbus context"""
        for tag_name, value in sensor_values.items():
            if tag_name in self.tag_mappings:
                mapping = self.tag_mappings[tag_name]
                table = mapping['table']
                address = mapping['address']
                
                # Map table names to Modbus function codes
                table_map = {
                    'DI': 2,   # Discrete Inputs
                    'IR': 4    # Input Registers
                }
                
                # Set sensor values directly in the data block
                if table == 'DI':
                    self.context[0][0]['di'].setValues(address, [value])
                elif table == 'IR':
                    self.context[0][0]['ir'].setValues(address, [value])
    
    def get_actuator_values(self) -> Dict[str, Any]:
        """Get all actuator values from Modbus context"""
        actuator_values = {}
        
        for tag_name, mapping in self.tag_mappings.items():
            if mapping['role'] == 'Actuator':
                actuator_values[tag_name] = self.get_tag_value(tag_name)
        
        return actuator_values
    
    def get_context(self) -> ModbusServerContext:
        """Get the Modbus server context"""
        return self.context
