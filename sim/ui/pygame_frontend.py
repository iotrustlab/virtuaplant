"""
Pygame Frontend for VirtuaPlant Simulator
2D visualization for bottle filling and oil refinery plants
"""

import pygame
import asyncio
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from sim.common.modbus_bridge import ModbusBridge

class PygameFrontend:
    """2D pygame frontend for plant visualization"""
    
    def __init__(self, plant_type: str, modbus_port: int = 5020):
        self.plant_type = plant_type
        self.modbus_port = modbus_port
        self.modbus_bridge = ModbusBridge(plant_type)
        
        # Screen dimensions (from existing world.py files)
        if plant_type == "bottle":
            self.SCREEN_WIDTH = 600
            self.SCREEN_HEIGHT = 350
        else:  # refinery
            self.SCREEN_WIDTH = 580
            self.SCREEN_HEIGHT = 460
        
        self.FPS = 50
        self.running = False
        
        # Physics state
        self.bottles = [
            {'position': 130.0, 'level': 0.0, 'filled': False},
            {'position': 130.0, 'level': 0.0, 'filled': False},
            {'position': 130.0, 'level': 0.0, 'filled': False}
        ]
        self.current_bottle = 0
        self.tank_level = 20.0
        self.oil_spilled = 0.0
        self.oil_processed = 0.0
        
        # Visual elements
        self.water_drops = []
        self.oil_drops = []
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption(f"VirtuaPlant - {plant_type.title()} Plant")
        
        # Fonts
        self.font_big = pygame.font.SysFont(None, 40)
        self.font_medium = pygame.font.SysFont(None, 26)
        self.font_small = pygame.font.SysFont(None, 18)
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (0, 100, 255)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BROWN = (139, 69, 19)
        self.GRAY = (128, 128, 128)
        self.DARK_GRAY = (64, 64, 64)
        
    def start(self):
        """Start the pygame frontend"""
        self.running = True
        clock = pygame.time.Clock()
        
        print(f"Starting {self.plant_type} plant visualization...")
        
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("Quit event received")
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    print(f"Key pressed: {event.key}")
                    if event.key == pygame.K_ESCAPE:
                        print("ESC pressed - quitting")
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        print("SPACE pressed - toggling run")
                        self._toggle_run()
                    elif event.key == pygame.K_n:
                        print("N pressed - toggling nozzle")
                        self._toggle_nozzle()
                    elif event.key == pygame.K_m:
                        print("M pressed - toggling motor")
                        self._toggle_motor()
                    elif event.key == pygame.K_TAB:
                        print("TAB pressed - switching bottle")
                        self._switch_bottle()
            
            # Update physics and get sensor values
            self._update_physics()
            
            # Draw everything
            self._draw()
            
            # Update display
            pygame.display.flip()
            clock.tick(self.FPS)
        
        pygame.quit()
    
    def _update_physics(self):
        """Update physics simulation"""
        # Get actuator values from Modbus
        actuator_values = self.modbus_bridge.get_actuator_values()
        
        if self.plant_type == "bottle":
            self._update_bottle_physics(actuator_values)
        else:
            self._update_refinery_physics(actuator_values)
    
    def _update_bottle_physics(self, actuator_values: Dict[str, Any]):
        """Update bottle filling physics"""
        motor_on = actuator_values.get('ACT_MOTOR', False)
        nozzle_open = actuator_values.get('ACT_NOZZLE', False)
        run_cmd = self.modbus_bridge.get_tag_value('CMD_RUN')
        
        # Update all bottles
        for i, bottle in enumerate(self.bottles):
            # Update bottle position (only if run command is active)
            if motor_on and run_cmd:
                bottle['position'] += 0.5  # Faster movement
            elif run_cmd:
                bottle['position'] += 0.1  # Slow movement even without motor
            
            # Reset bottle when it goes off screen
            if bottle['position'] > self.SCREEN_WIDTH + 150:
                bottle['position'] = 130
                bottle['level'] = 0.0
                bottle['filled'] = False
            
            # Update bottle level (only for bottle in filling position)
            if nozzle_open and 130 <= bottle['position'] <= 200:
                bottle['level'] += 0.1
                bottle['level'] = min(1.0, bottle['level'])
                
                # Mark as filled when level is high enough
                if bottle['level'] >= 0.8:
                    bottle['filled'] = True
                
                # Add water drops
                if len(self.water_drops) < 15:
                    self.water_drops.append({
                        'x': 180 + (bottle['position'] - 130) * 0.1,
                        'y': 430,
                        'vx': 0,
                        'vy': 2
                    })
            else:
                # Natural drain
                if bottle['level'] > 0:
                    bottle['level'] -= 0.02
                    bottle['level'] = max(0.0, bottle['level'])
        
        # Update water drops
        for drop in self.water_drops[:]:
            drop['y'] += drop['vy']
            if drop['y'] > self.SCREEN_HEIGHT or drop['y'] < 150:
                self.water_drops.remove(drop)
        
        # Update sensor values based on current bottle
        current_bottle = self.bottles[self.current_bottle]
        bottle_in_position = 130 <= current_bottle['position'] <= 200
        bottle_filled = current_bottle['filled']
        
        self.modbus_bridge.update_sensors({
            'SENSOR_LIMIT_SWITCH': bottle_in_position,
            'SENSOR_LEVEL_SENSOR': bottle_filled
        })
    
    def _update_refinery_physics(self, actuator_values: Dict[str, Any]):
        """Update oil refinery physics"""
        feed_pump_on = actuator_values.get('ACT_FEED_PUMP', False)
        outlet_valve_open = actuator_values.get('ACT_OUTLET_VALVE', False)
        sep_valve_open = actuator_values.get('ACT_SEP_VALVE', False)
        waste_valve_open = actuator_values.get('ACT_WASTE_VALVE', False)
        
        # Update tank level
        if feed_pump_on:
            self.tank_level += 0.2
            self.tank_level = min(100.0, self.tank_level)
            
            # Add oil drops
            if len(self.oil_drops) < 15:
                self.oil_drops.append({
                    'x': 70,
                    'y': 565,
                    'vx': 0,
                    'vy': 1.5
                })
        
        # Process oil
        if outlet_valve_open and sep_valve_open:
            process_rate = min(0.1, self.tank_level)
            self.tank_level -= process_rate
            self.oil_processed += process_rate
        
        # Empty tank
        if waste_valve_open:
            empty_rate = 0.15
            self.tank_level -= empty_rate
            self.tank_level = max(0.0, self.tank_level)
        
        # Check for spills
        if self.tank_level > 100.0:
            spill_amount = self.tank_level - 100.0
            self.oil_spilled += spill_amount
            self.tank_level = 100.0
        
        # Update oil drops
        for drop in self.oil_drops[:]:
            drop['y'] += drop['vy']
            if drop['y'] > self.SCREEN_HEIGHT or drop['y'] < 100:
                self.oil_drops.remove(drop)
        
        # Update sensor values
        tank_level_percent = int(self.tank_level)
        oil_upper_sensor = self.tank_level > 90
        
        self.modbus_bridge.update_sensors({
            'SENSOR_TANK_LEVEL': tank_level_percent,
            'SENSOR_OIL_SPILL': int(self.oil_spilled),
            'SENSOR_OIL_PROCESSED': int(self.oil_processed),
            'SENSOR_OIL_UPPER': oil_upper_sensor
        })
    
    def _draw(self):
        """Draw the plant visualization"""
        self.screen.fill(self.WHITE)
        
        if self.plant_type == "bottle":
            self._draw_bottle_plant()
        else:
            self._draw_refinery_plant()
        
        # Draw UI elements
        self._draw_ui()
    
    def _draw_bottle_plant(self):
        """Draw bottle filling plant"""
        # Draw base
        pygame.draw.rect(self.screen, self.BLACK, (0, 300, self.SCREEN_WIDTH, 20))
        
        # Draw nozzle
        nozzle_color = self.GREEN if self.modbus_bridge.get_tag_value('ACT_NOZZLE') else self.RED
        pygame.draw.rect(self.screen, nozzle_color, (165, 410, 30, 40))
        
        # Draw all bottles
        for i, bottle in enumerate(self.bottles):
            bottle_x = bottle['position']
            bottle_y = 300
            
            # Bottle outline (highlight current bottle)
            outline_color = self.BLUE if i == self.current_bottle else self.BLACK
            outline_width = 3 if i == self.current_bottle else 2
            pygame.draw.rect(self.screen, outline_color, (bottle_x - 25, bottle_y - 100, 50, 100), outline_width)
            
            # Bottle fill level
            fill_height = int(bottle['level'] * 80)
            if fill_height > 0:
                fill_color = self.GREEN if bottle['filled'] else self.BLUE
                pygame.draw.rect(self.screen, fill_color, 
                               (bottle_x - 23, bottle_y - 20 - fill_height, 46, fill_height))
            
            # Bottle number
            number_text = self.font_small.render(str(i+1), True, self.BLACK)
            self.screen.blit(number_text, (bottle_x - 5, bottle_y - 120))
        
        # Draw limit switch
        current_bottle = self.bottles[self.current_bottle]
        switch_color = self.GREEN if 130 <= current_bottle['position'] <= 200 else self.RED
        pygame.draw.circle(self.screen, switch_color, (200, 300), 5)
        
        # Draw level sensor
        sensor_color = self.GREEN if current_bottle['filled'] else self.RED
        pygame.draw.circle(self.screen, sensor_color, (155, 380), 5)
        
        # Draw water drops
        for drop in self.water_drops:
            pygame.draw.circle(self.screen, self.BLUE, (int(drop['x']), int(drop['y'])), 3)
        
        # Draw run status indicator (large colored circle)
        run_cmd = self.modbus_bridge.get_tag_value('CMD_RUN')
        status_color = self.GREEN if run_cmd else self.RED
        pygame.draw.circle(self.screen, status_color, (self.SCREEN_WIDTH - 30, 30), 15)
        
        # Draw motor status indicator
        motor_on = self.modbus_bridge.get_tag_value('ACT_MOTOR')
        motor_color = self.GREEN if motor_on else self.RED
        pygame.draw.circle(self.screen, motor_color, (self.SCREEN_WIDTH - 30, 60), 10)
        
        # Draw nozzle status indicator
        nozzle_open = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
        nozzle_color = self.GREEN if nozzle_open else self.RED
        pygame.draw.circle(self.screen, nozzle_color, (self.SCREEN_WIDTH - 30, 90), 10)
    
    def _draw_refinery_plant(self):
        """Draw oil refinery plant"""
        # Draw base
        pygame.draw.rect(self.screen, self.BLACK, (0, 400, self.SCREEN_WIDTH, 20))
        
        # Draw oil tank
        tank_x, tank_y = 115, 400
        tank_width, tank_height = 100, 120
        
        # Tank outline
        pygame.draw.rect(self.screen, self.BLACK, (tank_x, tank_y - tank_height, tank_width, tank_height), 2)
        
        # Tank fill level
        fill_height = int((self.tank_level / 100.0) * (tank_height - 4))
        if fill_height > 0:
            pygame.draw.rect(self.screen, self.BROWN, 
                           (tank_x + 2, tank_y - 2 - fill_height, tank_width - 4, fill_height))
        
        # Draw separator vessel
        sep_x, sep_y = 327, 218
        pygame.draw.rect(self.screen, self.DARK_GRAY, (sep_x - 15, sep_y - 10, 30, 20))
        
        # Draw outlet valve
        valve_color = self.GREEN if self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE') else self.RED
        pygame.draw.rect(self.screen, valve_color, (70 - 14, 410 - 2, 28, 4))
        
        # Draw separator valve
        sep_valve_color = self.GREEN if self.modbus_bridge.get_tag_value('ACT_SEP_VALVE') else self.RED
        pygame.draw.rect(self.screen, sep_valve_color, (sep_x - 15, sep_y - 2, 30, 4))
        
        # Draw waste valve
        waste_valve_color = self.GREEN if self.modbus_bridge.get_tag_value('ACT_WASTE_VALVE') else self.RED
        pygame.draw.rect(self.screen, waste_valve_color, (225 - 8, 218 - 2, 16, 4))
        
        # Draw oil drops
        for drop in self.oil_drops:
            pygame.draw.circle(self.screen, self.BROWN, (int(drop['x']), int(drop['y'])), 2)
        
        # Draw spill sensor
        spill_x, spill_y = 0, 100
        pygame.draw.rect(self.screen, self.RED, (spill_x, spill_y, 137, 4))
    
    def _draw_ui(self):
        """Draw UI elements"""
        # Clear UI area with white background
        pygame.draw.rect(self.screen, self.WHITE, (0, 0, 300, self.SCREEN_HEIGHT))
        
        # Title
        title = self.font_medium.render(f"{self.plant_type.title()} Plant", True, self.BLACK)
        self.screen.blit(title, (10, 40))
        
        # VirtuaPlant branding
        name = self.font_big.render("VirtuaPlant", True, self.DARK_GRAY)
        self.screen.blit(name, (10, 10))
        
        # Instructions
        instructions = self.font_small.render("ESC=quit, SPACE=run, N=nozzle, M=motor, TAB=bottle", True, self.GRAY)
        self.screen.blit(instructions, (self.SCREEN_WIDTH - 350, 10))
        
        # Status information
        if self.plant_type == "bottle":
            self._draw_bottle_status()
        else:
            self._draw_refinery_status()
    
    def _draw_bottle_status(self):
        """Draw bottle plant status"""
        y_offset = 70
        
        # Run command status (most important) - LARGE TEXT
        run_cmd = self.modbus_bridge.get_tag_value('CMD_RUN')
        run_color = self.GREEN if run_cmd else self.RED
        run_text = self.font_big.render(f"RUN: {'ON' if run_cmd else 'OFF'}", True, run_color)
        self.screen.blit(run_text, (10, y_offset))
        
        # Current bottle info - LARGE TEXT
        current_bottle = self.bottles[self.current_bottle]
        pos_text = self.font_medium.render(f"Bottle {self.current_bottle+1} Pos: {current_bottle['position']:.1f}", True, self.BLACK)
        self.screen.blit(pos_text, (10, y_offset + 40))
        
        # Bottle level - LARGE TEXT
        level_text = self.font_medium.render(f"Bottle {self.current_bottle+1} Level: {current_bottle['level']:.2f}", True, self.BLACK)
        self.screen.blit(level_text, (10, y_offset + 70))
        
        # Bottle status
        status_color = self.GREEN if current_bottle['filled'] else self.RED
        status_text = self.font_medium.render(f"Bottle {self.current_bottle+1}: {'FILLED' if current_bottle['filled'] else 'EMPTY'}", True, status_color)
        self.screen.blit(status_text, (10, y_offset + 100))
        
        # Motor status - LARGE TEXT
        motor_on = self.modbus_bridge.get_tag_value('ACT_MOTOR')
        motor_color = self.GREEN if motor_on else self.RED
        motor_text = self.font_medium.render(f"MOTOR: {'ON' if motor_on else 'OFF'}", True, motor_color)
        self.screen.blit(motor_text, (10, y_offset + 100))
        
        # Nozzle status - LARGE TEXT
        nozzle_open = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
        nozzle_color = self.GREEN if nozzle_open else self.RED
        nozzle_text = self.font_medium.render(f"NOZZLE: {'OPEN' if nozzle_open else 'CLOSED'}", True, nozzle_color)
        self.screen.blit(nozzle_text, (10, y_offset + 130))
        
        # Add a flashing indicator when run is active
        if run_cmd:
            import time
            flash = int(time.time() * 2) % 2  # Flash every 0.5 seconds
            if flash:
                flash_text = self.font_big.render("*** RUNNING ***", True, self.GREEN)
                self.screen.blit(flash_text, (10, y_offset + 160))
    
    def _draw_refinery_status(self):
        """Draw refinery plant status"""
        y_offset = 70
        
        # Tank level
        level_text = self.font_small.render(f"Tank Level: {self.tank_level:.1f}%", True, self.BLACK)
        self.screen.blit(level_text, (10, y_offset))
        
        # Oil processed
        processed_text = self.font_small.render(f"Processed: {self.oil_processed:.1f}L", True, self.BLACK)
        self.screen.blit(processed_text, (10, y_offset + 20))
        
        # Oil spilled
        spilled_text = self.font_small.render(f"Spilled: {self.oil_spilled:.1f}L", True, self.RED)
        self.screen.blit(spilled_text, (10, y_offset + 40))
        
        # Feed pump status
        pump_on = self.modbus_bridge.get_tag_value('ACT_FEED_PUMP')
        pump_color = self.GREEN if pump_on else self.RED
        pump_text = self.font_small.render(f"Feed Pump: {'ON' if pump_on else 'OFF'}", True, pump_color)
        self.screen.blit(pump_text, (10, y_offset + 60))
    
    def _toggle_run(self):
        """Toggle run command"""
        try:
            current_run = self.modbus_bridge.get_tag_value('CMD_RUN')
            new_run = not current_run
            self.modbus_bridge.set_tag_value('CMD_RUN', new_run)
            print(f"Run command toggled: {current_run} -> {new_run}")
            
            # Also toggle motor automatically for better visual feedback
            if new_run:
                self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
                print("Motor automatically turned ON")
            else:
                self.modbus_bridge.set_tag_value('ACT_MOTOR', False)
                self.modbus_bridge.set_tag_value('ACT_NOZZLE', False)
                print("Motor and nozzle automatically turned OFF")
                
        except Exception as e:
            print(f"Error toggling run command: {e}")
    
    def _toggle_nozzle(self):
        """Toggle nozzle valve"""
        try:
            current_nozzle = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
            new_nozzle = not current_nozzle
            self.modbus_bridge.set_tag_value('ACT_NOZZLE', new_nozzle)
            print(f"Nozzle toggled: {current_nozzle} -> {new_nozzle}")
        except Exception as e:
            print(f"Error toggling nozzle: {e}")
    
    def _toggle_motor(self):
        """Toggle motor"""
        try:
            current_motor = self.modbus_bridge.get_tag_value('ACT_MOTOR')
            new_motor = not current_motor
            self.modbus_bridge.set_tag_value('ACT_MOTOR', new_motor)
            print(f"Motor toggled: {current_motor} -> {new_motor}")
        except Exception as e:
            print(f"Error toggling motor: {e}")
    
    def _switch_bottle(self):
        """Switch to next bottle"""
        self.current_bottle = (self.current_bottle + 1) % len(self.bottles)
        print(f"Switched to bottle {self.current_bottle + 1}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VirtuaPlant Pygame Frontend")
    parser.add_argument("plant", choices=["bottle", "refinery"], help="Plant type to visualize")
    parser.add_argument("--port", type=int, default=5020, help="Modbus port")
    
    args = parser.parse_args()
    
    frontend = PygameFrontend(args.plant, args.port)
    frontend.start()

if __name__ == "__main__":
    main()
