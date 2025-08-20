#!/usr/bin/env python3
"""
IR Export Analysis Tool
Exports semantic and CFG analysis for OpenPLC ST files using CrossPLC
"""

import subprocess
import sys
import json
import os
from pathlib import Path

def run_crossplc_analysis(st_file: str, output_file: str, components: str = "tags,control_flow"):
    """Run CrossPLC analysis on OpenPLC ST file"""
    
    # Use absolute paths from virtuaplant directory
    virtuaplant_dir = "/Users/lag/Development/virtuaplant"
    st_file_abs = str(Path(virtuaplant_dir) / st_file)
    output_file_abs = str(Path(virtuaplant_dir) / output_file)
    
    cmd = [
        "python3", "-m", "crossplc.cli", "analyze-multi",
        "--st", st_file_abs,
        "-o", output_file_abs,
        "--include", components,
        "-v"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running CrossPLC analysis: {result.stderr}")
        return False
    
    print(f"Successfully exported to {output_file}")
    return True

def main():
    """Main function to export IR analysis for both plants"""
    
    # Define plant configurations
    plants = [
        {
            "name": "bottle",
            "st_file": "openplc/bottle/Main.st",
            "semantic_output": "ir/bottle_semantic.json",
            "cfg_output": "ir/bottle_cfg.json"
        },
        {
            "name": "refinery", 
            "st_file": "openplc/refinery/Main.st",
            "semantic_output": "ir/refinery_semantic.json",
            "cfg_output": "ir/refinery_cfg.json"
        }
    ]
    
    # Change to CrossPLC directory
    crossplc_dir = "/Users/lag/Development/l5x2ST"
    
    # Change to CrossPLC directory for execution
    original_cwd = Path.cwd()
    os.chdir(crossplc_dir)
    
    for plant in plants:
        print(f"\n=== Processing {plant['name']} plant ===")
        
        # Export semantic analysis
        print(f"Exporting semantic analysis...")
        success = run_crossplc_analysis(
            plant['st_file'],
            plant['semantic_output'],
            "tags,control_flow"
        )
        
        if not success:
            print(f"Failed to export semantic analysis for {plant['name']}")
            continue
        
        # Export CFG analysis with graphs
        print(f"Exporting CFG analysis...")
        success = run_crossplc_analysis(
            plant['st_file'],
            plant['cfg_output'],
            "tags,control_flow"
        )
        
        if not success:
            print(f"Failed to export CFG analysis for {plant['name']}")
            continue
    
    # Change back to original directory
    os.chdir(original_cwd)
    
    print("\n=== IR Export Complete ===")
    print("Generated files:")
    for plant in plants:
        print(f"  - {plant['semantic_output']}")
        print(f"  - {plant['cfg_output']}")

if __name__ == "__main__":
    main()
