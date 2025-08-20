#!/usr/bin/env python3
"""
Graph Exporter for VirtuaPlant
Generates DOT and GraphML files from CrossPLC IR analysis
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

def export_cfg_to_dot(cfg_data: Dict[str, Any], output_file: str):
    """Export control flow graph to DOT format"""
    
    dot_content = []
    dot_content.append("digraph CFG {")
    dot_content.append("  rankdir=TB;")
    dot_content.append("  node [shape=box, style=filled, fillcolor=lightblue];")
    dot_content.append("  edge [color=black];")
    dot_content.append("")
    
    # Add nodes
    for routine_name, routine_cfg in cfg_data.items():
        if 'blocks' in routine_cfg:
            for i, block in enumerate(routine_cfg['blocks']):
                block_id = block.get('block_id', f"block_{i}")
                block_type = block.get('type', 'instruction')
                
                # Create node label
                label = f"{routine_name}\\n{block_id}\\n({block_type})"
                
                # Add defs and uses to label
                defs = block.get('defs', [])
                uses = block.get('uses', [])
                if defs:
                    label += f"\\nDefs: {', '.join(defs)}"
                if uses:
                    label += f"\\nUses: {', '.join(uses)}"
                
                dot_content.append(f'  "{routine_name}_{block_id}" [label="{label}"];')
    
    dot_content.append("")
    
    # Add edges
    for routine_name, routine_cfg in cfg_data.items():
        if 'blocks' in routine_cfg:
            blocks = routine_cfg['blocks']
            for i, block in enumerate(blocks):
                current_id = block.get('block_id', f"block_{i}")
                
                # Add edge to next block
                if i + 1 < len(blocks):
                    next_block = blocks[i + 1]
                    next_id = next_block.get('block_id', f"block_{i+1}")
                    dot_content.append(f'  "{routine_name}_{current_id}" -> "{routine_name}_{next_id}";')
                
                # Add conditional edges if specified
                if 'successors' in block:
                    for successor in block['successors']:
                        dot_content.append(f'  "{routine_name}_{current_id}" -> "{routine_name}_{successor}";')
    
    dot_content.append("}")
    
    # Write DOT file
    with open(output_file, 'w') as f:
        f.write('\n'.join(dot_content))
    
    print(f"✅ DOT file exported: {output_file}")

def export_dataflow_to_dot(dataflow_data: Dict[str, Any], output_file: str):
    """Export data flow graph to DOT format"""
    
    dot_content = []
    dot_content.append("digraph DataFlow {")
    dot_content.append("  rankdir=LR;")
    dot_content.append("  node [shape=ellipse, style=filled];")
    dot_content.append("  edge [color=blue];")
    dot_content.append("")
    
    # Add nodes for routines
    routines = set()
    for edge in dataflow_data:
        routines.add(edge.get('source_routine', 'unknown'))
        routines.add(edge.get('target_routine', 'unknown'))
    
    for routine in routines:
        dot_content.append(f'  "{routine}" [fillcolor=lightgreen, label="{routine}"];')
    
    dot_content.append("")
    
    # Add edges for data flow
    for edge in dataflow_data:
        source = edge.get('source_routine', 'unknown')
        target = edge.get('target_routine', 'unknown')
        shared_tags = edge.get('shared_tags', [])
        
        if shared_tags:
            label = f"\\n{', '.join(shared_tags[:3])}"  # Show first 3 tags
            if len(shared_tags) > 3:
                label += "..."
        else:
            label = ""
        
        dot_content.append(f'  "{source}" -> "{target}" [label="{label}"];')
    
    dot_content.append("}")
    
    # Write DOT file
    with open(output_file, 'w') as f:
        f.write('\n'.join(dot_content))
    
    print(f"✅ Data flow DOT file exported: {output_file}")

def export_to_graphml(cfg_data: Dict[str, Any], dataflow_data: Dict[str, Any], output_file: str):
    """Export to GraphML format"""
    
    graphml_content = []
    graphml_content.append('<?xml version="1.0" encoding="UTF-8"?>')
    graphml_content.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns"')
    graphml_content.append('         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    graphml_content.append('         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns')
    graphml_content.append('         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">')
    graphml_content.append('')
    
    # Define attributes
    graphml_content.append('  <key id="type" for="node" attr.name="type" attr.type="string"/>')
    graphml_content.append('  <key id="routine" for="node" attr.name="routine" attr.type="string"/>')
    graphml_content.append('  <key id="defs" for="node" attr.name="defs" attr.type="string"/>')
    graphml_content.append('  <key id="uses" for="node" attr.name="uses" attr.type="string"/>')
    graphml_content.append('  <key id="shared_tags" for="edge" attr.name="shared_tags" attr.type="string"/>')
    graphml_content.append('')
    
    # Start graph
    graphml_content.append('  <graph id="virtuaplant_cfg" edgedefault="directed">')
    
    # Add nodes
    node_id = 0
    node_map = {}
    
    for routine_name, routine_cfg in cfg_data.items():
        if 'blocks' in routine_cfg:
            for i, block in enumerate(routine_cfg['blocks']):
                block_id = block.get('block_id', f"block_{i}")
                block_type = block.get('type', 'instruction')
                defs = block.get('defs', [])
                uses = block.get('uses', [])
                
                graphml_content.append(f'    <node id="n{node_id}">')
                graphml_content.append(f'      <data key="type">{block_type}</data>')
                graphml_content.append(f'      <data key="routine">{routine_name}</data>')
                graphml_content.append(f'      <data key="defs">{",".join(defs)}</data>')
                graphml_content.append(f'      <data key="uses">{",".join(uses)}</data>')
                graphml_content.append(f'    </node>')
                
                node_map[f"{routine_name}_{block_id}"] = node_id
                node_id += 1
    
    # Add edges
    edge_id = 0
    
    for routine_name, routine_cfg in cfg_data.items():
        if 'blocks' in routine_cfg:
            blocks = routine_cfg['blocks']
            for i, block in enumerate(blocks):
                current_id = block.get('block_id', f"block_{i}")
                current_node = f"{routine_name}_{current_id}"
                
                if current_node in node_map:
                    source_id = node_map[current_node]
                    
                    # Add edge to next block
                    if i + 1 < len(blocks):
                        next_block = blocks[i + 1]
                        next_id = next_block.get('block_id', f"block_{i+1}")
                        next_node = f"{routine_name}_{next_id}"
                        
                        if next_node in node_map:
                            target_id = node_map[next_node]
                            graphml_content.append(f'    <edge id="e{edge_id}" source="n{source_id}" target="n{target_id}"/>')
                            edge_id += 1
    
    # Add data flow edges
    for edge in dataflow_data:
        source = edge.get('source_routine', 'unknown')
        target = edge.get('target_routine', 'unknown')
        shared_tags = edge.get('shared_tags', [])
        
        # Find or create nodes for routines
        if source not in node_map:
            graphml_content.append(f'    <node id="n{node_id}">')
            graphml_content.append(f'      <data key="type">routine</data>')
            graphml_content.append(f'      <data key="routine">{source}</data>')
            graphml_content.append(f'      <data key="defs"></data>')
            graphml_content.append(f'      <data key="uses"></data>')
            graphml_content.append(f'    </node>')
            node_map[source] = node_id
            node_id += 1
        
        if target not in node_map:
            graphml_content.append(f'    <node id="n{node_id}">')
            graphml_content.append(f'      <data key="type">routine</data>')
            graphml_content.append(f'      <data key="routine">{target}</data>')
            graphml_content.append(f'      <data key="defs"></data>')
            graphml_content.append(f'      <data key="uses"></data>')
            graphml_content.append(f'    </node>')
            node_map[target] = node_id
            node_id += 1
        
        source_id = node_map[source]
        target_id = node_map[target]
        
        graphml_content.append(f'    <edge id="e{edge_id}" source="n{source_id}" target="n{target_id}">')
        graphml_content.append(f'      <data key="shared_tags">{",".join(shared_tags)}</data>')
        graphml_content.append(f'    </edge>')
        edge_id += 1
    
    # Close graph and graphml
    graphml_content.append('  </graph>')
    graphml_content.append('</graphml>')
    
    # Write GraphML file
    with open(output_file, 'w') as f:
        f.write('\n'.join(graphml_content))
    
    print(f"✅ GraphML file exported: {output_file}")

def export_ir_graphs(plant_type: str):
    """Export IR graphs for a specific plant"""
    
    # Load IR data
    ir_file = f"ir/{plant_type}_crossplc.json"
    if not os.path.exists(ir_file):
        print(f"❌ IR file not found: {ir_file}")
        return
    
    with open(ir_file, 'r') as f:
        ir_data = json.load(f)
    
    # Create graphs directory
    graphs_dir = Path("ir/graphs")
    graphs_dir.mkdir(exist_ok=True)
    
    # Extract CFG data
    cfg_data = {}
    dataflow_data = []
    
    for plc_name, plc_data in ir_data.get('detailed_components', {}).items():
        if 'control_flow' in plc_data:
            for routine_name, routine_data in plc_data['control_flow'].get('routines', {}).items():
                if 'Main' in routine_data:
                    cfg_data[f"{plc_name}_{routine_name}"] = routine_data['Main']
    
    # Generate simplified CFG if no detailed data
    if not cfg_data:
        print(f"⚠️ No detailed CFG data found, generating simplified graph for {plant_type}")
        cfg_data = {
            f"{plant_type}_main": {
                "blocks": [
                    {"block_id": "start", "type": "start", "defs": [], "uses": []},
                    {"block_id": "main_logic", "type": "logic", "defs": ["internal_vars"], "uses": ["sensors"]},
                    {"block_id": "outputs", "type": "output", "defs": ["actuators"], "uses": ["internal_vars"]},
                    {"block_id": "end", "type": "end", "defs": [], "uses": []}
                ]
            }
        }
    
    # Export DOT files
    cfg_dot_file = graphs_dir / f"{plant_type}_cfg.dot"
    export_cfg_to_dot(cfg_data, str(cfg_dot_file))
    
    dataflow_dot_file = graphs_dir / f"{plant_type}_dataflow.dot"
    export_dataflow_to_dot(dataflow_data, str(dataflow_dot_file))
    
    # Export GraphML file
    graphml_file = graphs_dir / f"{plant_type}_cfg.graphml"
    export_to_graphml(cfg_data, dataflow_data, str(graphml_file))
    
    print(f"✅ Graph exports completed for {plant_type} plant")

def main():
    """Main function to export graphs for both plants"""
    
    print("📊 Exporting IR graphs...")
    
    # Export for both plants
    for plant_type in ["bottle", "refinery"]:
        print(f"\n=== Processing {plant_type} plant ===")
        export_ir_graphs(plant_type)
    
    print(f"\n🎉 Graph export complete!")
    print(f"Generated files in ir/graphs/:")
    print(f"  - bottle_cfg.dot")
    print(f"  - bottle_dataflow.dot") 
    print(f"  - bottle_cfg.graphml")
    print(f"  - refinery_cfg.dot")
    print(f"  - refinery_dataflow.dot")
    print(f"  - refinery_cfg.graphml")

if __name__ == "__main__":
    main()


