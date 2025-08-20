#!/usr/bin/env python3
"""
Map Validation Tool for VirtuaPlant
Validates Modbus maps for unique addresses, consistent types, and policy compliance
"""

import csv
import yaml
import sys
from pathlib import Path
from typing import Dict, List, Set

def load_tag_policy() -> Dict:
    """Load the tag policy from policy/tags.yaml"""
    with open("policy/tags.yaml", "r") as f:
        return yaml.safe_load(f)

def validate_modbus_map(map_file: str) -> Dict:
    """Validate a single Modbus map file"""
    
    policy = load_tag_policy()
    errors = []
    warnings = []
    
    # Read the map file
    with open(map_file, "r") as f:
        reader = csv.DictReader(f)
        tags = list(reader)
    
    # Check for required columns
    required_columns = ["name", "type", "table", "address", "width", "units", "desc", "role"]
    missing_columns = [col for col in required_columns if col not in tags[0].keys()]
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
    
    # Track addresses for uniqueness check
    addresses = {}
    
    for i, tag in enumerate(tags, 1):
        # Check tag naming policy
        tag_name = tag.get("name", "")
        if not tag_name:
            errors.append(f"Row {i}: Missing tag name")
            continue
            
        # Check prefix compliance
        valid_prefix = False
        for prefix in policy["prefixes"].values():
            if tag_name.startswith(prefix):
                valid_prefix = True
                break
        
        if not valid_prefix:
            errors.append(f"Row {i}: Tag '{tag_name}' doesn't follow naming policy (should start with {list(policy['prefixes'].values())})")
        
        # Check role consistency
        expected_role = None
        for pattern, role in policy["roles"].items():
            if pattern.endswith("*") and tag_name.startswith(pattern[:-1]):
                expected_role = role
                break
        
        actual_role = tag.get("role", "")
        if expected_role and actual_role != expected_role:
            errors.append(f"Row {i}: Tag '{tag_name}' has role '{actual_role}' but should be '{expected_role}'")
        
        # Check type consistency
        expected_types = []
        for pattern, types in policy["type_rules"].items():
            if pattern.endswith("*") and tag_name.startswith(pattern[:-1]):
                expected_types = types
                break
        
        actual_type = tag.get("type", "")
        if expected_types and actual_type not in expected_types:
            errors.append(f"Row {i}: Tag '{tag_name}' has type '{actual_type}' but should be one of {expected_types}")
        
        # Check Modbus table consistency
        expected_table = None
        for pattern, table in policy["modbus_tables"].items():
            if pattern.endswith("*") and tag_name.startswith(pattern[:-1]):
                expected_table = table
                break
        
        actual_table = tag.get("table", "")
        if expected_table and actual_table != expected_table:
            warnings.append(f"Row {i}: Tag '{tag_name}' uses table '{actual_table}' but policy suggests '{expected_table}'")
        
        # Check address uniqueness
        address = tag.get("address", "")
        table = tag.get("table", "")
        address_key = f"{table}:{address}"
        
        if address_key in addresses:
            errors.append(f"Row {i}: Duplicate address {address_key} (already used by '{addresses[address_key]}')")
        else:
            addresses[address_key] = tag_name
        
        # Validate address format
        try:
            if address.startswith("0x"):
                int(address, 16)
            else:
                int(address)
        except ValueError:
            errors.append(f"Row {i}: Invalid address format '{address}'")
    
    return {
        "file": map_file,
        "total_tags": len(tags),
        "errors": errors,
        "warnings": warnings,
        "valid": len(errors) == 0
    }

def main():
    """Main validation function"""
    
    if len(sys.argv) < 2:
        print("Usage: python3 validate_map.py <map_file> [map_file2 ...]")
        sys.exit(1)
    
    map_files = sys.argv[1:]
    all_valid = True
    
    for map_file in map_files:
        print(f"\nValidating {map_file}...")
        result = validate_modbus_map(map_file)
        
        print(f"  Total tags: {result['total_tags']}")
        
        if result['errors']:
            print(f"  ERRORS ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"    - {error}")
            all_valid = False
        
        if result['warnings']:
            print(f"  WARNINGS ({len(result['warnings'])}):")
            for warning in result['warnings']:
                print(f"    - {warning}")
        
        if result['valid']:
            print("  ✓ Map is valid")
        else:
            print("  ✗ Map has errors")
    
    if all_valid:
        print("\n✓ All maps are valid")
        sys.exit(0)
    else:
        print("\n✗ Some maps have errors")
        sys.exit(1)

if __name__ == "__main__":
    main()


