#!/usr/bin/env python3
"""
VirtuaPlant Simulator CLI
Command-line interface for running plant simulations
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sim.bottle.plant import BottleFillingPlant
from sim.refinery.plant import OilRefineryPlant

async def run_bottle_plant(args):
    """Run bottle filling plant simulation"""
    plant = BottleFillingPlant(modbus_port=args.port)
    
    if args.headless:
        print("Running bottle filling plant in headless mode...")
        # Set simulation speed
        plant.dt = 0.02 / args.speedup if args.speedup > 0 else 0.02
        
        await plant.start()
    elif args.gui:
        print("Starting bottle filling plant with pygame GUI...")
        if args.improved:
            from sim.ui.improved_pygame_frontend import ImprovedPygameFrontend
            frontend = ImprovedPygameFrontend("bottle", args.port)
        else:
            from sim.ui.pygame_frontend import PygameFrontend
            frontend = PygameFrontend("bottle", args.port)
        frontend.start()
    else:
        print("Bottle filling plant simulation started.")
        print("Use Ctrl+C to stop.")
        await plant.start()

async def run_refinery_plant(args):
    """Run oil refinery plant simulation"""
    plant = OilRefineryPlant(modbus_port=args.port)
    
    if args.headless:
        print("Running oil refinery plant in headless mode...")
        # Set simulation speed
        plant.dt = 0.02 / args.speedup if args.speedup > 0 else 0.02
        
        await plant.start()
    elif args.gui:
        print("Starting oil refinery plant with pygame GUI...")
        if args.improved:
            from sim.ui.improved_pygame_frontend import ImprovedPygameFrontend
            frontend = ImprovedPygameFrontend("refinery", args.port)
        else:
            from sim.ui.pygame_frontend import PygameFrontend
            frontend = PygameFrontend("refinery", args.port)
        frontend.start()
    else:
        print("Oil refinery plant simulation started.")
        print("Use Ctrl+C to stop.")
        await plant.start()

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="VirtuaPlant Simulator - Industrial Control System Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sim/cli.py bottle                    # Run bottle plant with UI
  python sim/cli.py refinery --headless       # Run refinery plant headless
  python sim/cli.py bottle --gui              # Run with pygame GUI
  python sim/cli.py refinery --port 5022      # Run on custom port
  python sim/cli.py bottle --speedup 10       # Run 10x faster
        """
    )
    
    subparsers = parser.add_subparsers(dest='plant', help='Plant type to simulate')
    
    # Bottle plant parser
    bottle_parser = subparsers.add_parser('bottle', help='Bottle filling plant')
    bottle_parser.add_argument('--port', type=int, default=5020, help='Modbus port (default: 5020)')
    bottle_parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    bottle_parser.add_argument('--gui', action='store_true', help='Run with pygame GUI')
    bottle_parser.add_argument('--improved', action='store_true', help='Use improved physics-based GUI')
    bottle_parser.add_argument('--speedup', type=float, default=1.0, help='Simulation speedup factor (default: 1.0)')
    bottle_parser.set_defaults(func=run_bottle_plant)
    
    # Refinery plant parser
    refinery_parser = subparsers.add_parser('refinery', help='Oil refinery plant')
    refinery_parser.add_argument('--port', type=int, default=5021, help='Modbus port (default: 5021)')
    refinery_parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    refinery_parser.add_argument('--gui', action='store_true', help='Run with pygame GUI')
    refinery_parser.add_argument('--improved', action='store_true', help='Use improved physics-based GUI')
    refinery_parser.add_argument('--speedup', type=float, default=1.0, help='Simulation speedup factor (default: 1.0)')
    refinery_parser.set_defaults(func=run_refinery_plant)
    
    args = parser.parse_args()
    
    if not args.plant:
        parser.print_help()
        sys.exit(1)
    
    try:
        asyncio.run(args.func(args))
    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
