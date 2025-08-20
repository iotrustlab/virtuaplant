#!/usr/bin/env python3
"""
Inventory Analyzer for VirtuaPlant
Analyzes existing Python plants to extract sensor/actuator information
"""

import re
import json
import csv
from pathlib import Path
from typing import Dict, List, Set

def analyze_bottle_filling_plant() -> Dict:
    """Analyze bottle filling plant from world.py"""
    
    # Based on analysis of plants/bottle-filling/world.py
    inventory = {
        "plant": "bottle-filling",
        "sensors": [
            {
                "name": "SENSOR_LIMIT_SWITCH",
                "type": "BOOL",
                "address": 0x2,
                "description": "Limit switch detects bottle in position",
                "role": "Sensor"
            },
            {
                "name": "SENSOR_LEVEL_SENSOR", 
                "type": "BOOL",
                "address": 0x1,
                "description": "Level sensor detects bottle filled",
                "role": "Sensor"
            }
        ],
        "actuators": [
            {
                "name": "ACT_MOTOR",
                "type": "BOOL", 
                "address": 0x3,
                "description": "Conveyor motor control",
                "role": "Actuator"
            },
            {
                "name": "ACT_NOZZLE",
                "type": "BOOL",
                "address": 0x4, 
                "description": "Water nozzle valve control",
                "role": "Actuator"
            }
        ],
        "commands": [
            {
                "name": "CMD_RUN",
                "type": "BOOL",
                "address": 0x10,
                "description": "System run command",
                "role": "Command"
            }
        ],
        "physics": {
            "description": "Bottle filling with water physics simulation",
            "key_variables": ["level", "bottle_position", "water_flow"],
            "equations": [
                "level' = level + k_pump*ACT_P1_ON - k_drain*ACT_V_DRAIN_OPEN - leak"
            ]
        }
    }
    
    return inventory

def analyze_oil_refinery_plant() -> Dict:
    """Analyze oil refinery plant from oil_world.py"""
    
    # Based on analysis of plants/oil-refinery/oil_world.py
    inventory = {
        "plant": "oil-refinery",
        "sensors": [
            {
                "name": "SENSOR_TANK_LEVEL",
                "type": "INT",
                "address": 0x2,
                "description": "Oil tank level sensor",
                "role": "Sensor"
            },
            {
                "name": "SENSOR_OIL_SPILL",
                "type": "INT", 
                "address": 0x6,
                "description": "Oil spill detection sensor",
                "role": "Sensor"
            },
            {
                "name": "SENSOR_OIL_PROCESSED",
                "type": "INT",
                "address": 0x7,
                "description": "Oil processed counter",
                "role": "Sensor"
            },
            {
                "name": "SENSOR_OIL_UPPER",
                "type": "BOOL",
                "address": 0x9,
                "description": "Upper tank level sensor",
                "role": "Sensor"
            }
        ],
        "actuators": [
            {
                "name": "ACT_FEED_PUMP",
                "type": "BOOL",
                "address": 0x1,
                "description": "Feed pump control",
                "role": "Actuator"
            },
            {
                "name": "ACT_OUTLET_VALVE",
                "type": "BOOL",
                "address": 0x3,
                "description": "Outlet valve control",
                "role": "Actuator"
            },
            {
                "name": "ACT_SEP_VALVE",
                "type": "BOOL",
                "address": 0x4,
                "description": "Separator valve control", 
                "role": "Actuator"
            },
            {
                "name": "ACT_WASTE_VALVE",
                "type": "BOOL",
                "address": 0x8,
                "description": "Waste valve control",
                "role": "Actuator"
            }
        ],
        "physics": {
            "description": "Oil refinery with separation and spill detection",
            "key_variables": ["store", "oil_level", "spill_amount", "processed_amount"],
            "equations": [
                "store' = store + k_feed*ACT_FEED_PUMP_ON - k_relief*ACT_RELIEF_VALVE_OPEN"
            ]
        }
    }
    
    return inventory

def generate_inventory_report():
    """Generate the inventory report"""
    
    bottle_inventory = analyze_bottle_filling_plant()
    refinery_inventory = analyze_oil_refinery_plant()
    
    # Combine into full inventory
    full_inventory = {
        "plants": [bottle_inventory, refinery_inventory],
        "summary": {
            "total_sensors": len(bottle_inventory["sensors"]) + len(refinery_inventory["sensors"]),
            "total_actuators": len(bottle_inventory["actuators"]) + len(refinery_inventory["actuators"]),
            "total_commands": len(bottle_inventory["commands"]),
            "plants": ["bottle-filling", "oil-refinery"]
        }
    }
    
    # Write JSON report
    with open("reports/inventory.json", "w") as f:
        json.dump(full_inventory, f, indent=2)
    
    # Generate CSV tag list
    all_tags = []
    
    for plant in [bottle_inventory, refinery_inventory]:
        for sensor in plant["sensors"]:
            all_tags.append({
                "name": sensor["name"],
                "type": sensor["type"],
                "address": sensor["address"],
                "role": sensor["role"],
                "plant": plant["plant"],
                "description": sensor["description"]
            })
        
        for actuator in plant["actuators"]:
            all_tags.append({
                "name": actuator["name"],
                "type": actuator["type"],
                "address": actuator["address"],
                "role": actuator["role"],
                "plant": plant["plant"],
                "description": actuator["description"]
            })
        
        if "commands" in plant:
            for cmd in plant["commands"]:
                all_tags.append({
                    "name": cmd["name"],
                    "type": cmd["type"],
                    "address": cmd["address"],
                    "role": cmd["role"],
                    "plant": plant["plant"],
                    "description": cmd["description"]
                })
    
    # Write CSV report
    with open("reports/taglist.csv", "w", newline="") as f:
        if all_tags:
            writer = csv.DictWriter(f, fieldnames=all_tags[0].keys())
            writer.writeheader()
            writer.writerows(all_tags)
    
    print(f"Generated inventory report with {full_inventory['summary']['total_sensors']} sensors, {full_inventory['summary']['total_actuators']} actuators")
    print("Files created: reports/inventory.json, reports/taglist.csv")

if __name__ == "__main__":
    generate_inventory_report()


