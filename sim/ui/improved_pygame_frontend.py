"""
Improved Pygame Frontend for VirtuaPlant
Incorporates original physics model with pymunk and better visuals
"""

import pygame
import pymunk
import random
import sys
import time
from typing import Dict, Any, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from sim.common.modbus_bridge import ModbusBridge

class ImprovedPygameFrontend:
    """Improved pygame frontend with pymunk physics"""
    
    def __init__(self, plant_type: str, modbus_port: int = 5020):
        print(f"Initializing ImprovedPygameFrontend with plant_type: '{plant_type}'")
        self.plant_type = plant_type
        self.modbus_port = modbus_port
        self.modbus_bridge = ModbusBridge(plant_type)
        
        # Screen dimensions (from original world.py files)
        if plant_type == "bottle":
            self.SCREEN_WIDTH = 600
            self.SCREEN_HEIGHT = 350
        else:  # refinery - much larger for complex layout
            self.SCREEN_WIDTH = 1200
            self.SCREEN_HEIGHT = 800
        
        self.FPS = 50
        self.running = False
        
        # Fixed timestep physics
        self.PHYSICS_DT = 1.0 / 120.0  # 120 FPS physics for better collision detection
        self.physics_accumulator = 0.0
        
        # Camera offset to ensure world coordinates map to visible screen space
        if plant_type == "bottle":
            self.CAMERA_Y = 100  # Offset to bring world objects into visible range
        else:  # refinery - much larger coordinate system
            self.CAMERA_Y = -50  # Optimized position from user testing
            self.CAMERA_X = 275  # Optimized position from user testing
        
        # Debug flags
        self.show_debug_rectangles = True
        self.show_world_axes = True
        
        # Manual camera controls for debugging
        self.camera_step = 10  # Pixels per keypress
        self.debug_mode = False  # Toggle for debug controls
        
        # Pymunk physics space with increased collision robustness
        self.space = pymunk.Space()
        self.space.gravity = (0.0, -900.0)  # Same as original
        self.space.iterations = 50  # Increase iterations for better collision detection
        self.space.damping = 0.8  # Add damping to reduce bouncing
        
        # Physics objects
        self.bottles = []
        self.water_balls = []
        self.oil_balls = []
        self.sensors = {}
        self.actuators = {}
        
        # Initialize valve states for refinery
        if plant_type == "refinery":
            self.outlet_valve_open = False
            self.sep_valve_open = False
            self.waste_valve_open = False
            print("Refinery valve states initialized: All valves CLOSED")
            
            # Force initial valve states in Modbus - EXACT original (all CLOSED)
            try:
                # New SIS actuators
                self.modbus_bridge.set_tag_value('ACT_INLET_VALVE', 1)      # 1 = OPEN (allow inlet flow)
                self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', 0)        # 0 = OFF (start idle)
                self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', 1)     # 1 = OPEN (allow outlet flow)
                self.modbus_bridge.set_tag_value('ACT_SLOP_VALVE', 0)       # 0 = CLOSED (no diversion)
                self.modbus_bridge.set_tag_value('ACT_FLARE_VALVE', 0)      # 0 = CLOSED (no flare)
                
                # Legacy compatibility
                self.modbus_bridge.set_tag_value('ACT_SEP_VALVE', 1)        # 1 = OPEN (follows outlet)
                self.modbus_bridge.set_tag_value('ACT_WASTE_VALVE', 0)      # 0 = CLOSED (follows slop)
                
                # Initialize SIS sensors
                self.modbus_bridge.set_tag_value('SIS_TANK_LSHH', 0)        # 0 = Normal level
                self.modbus_bridge.set_tag_value('SENSOR_TANK_LL', 0)       # 0 = Not low-low
                self.modbus_bridge.set_tag_value('SENSOR_SPILL_AREA', 0)    # 0 = No spill
                self.modbus_bridge.set_tag_value('LT_TANK_LEVEL_PCT', 5000) # 50% tank level
                self.modbus_bridge.set_tag_value('CMD_SIS_RESET', 0)        # 0 = No reset command
                
                # Initialize alarms
                self.modbus_bridge.set_tag_value('ALM_SIS_LSHH_TRIP', 0)    # 0 = No SIS trip
                self.modbus_bridge.set_tag_value('ALM_LL_TRIP', 0)          # 0 = No LL trip
                
                print("Initial SIS states set in Modbus: Normal operation")
            except Exception as e:
                print(f"Warning: Could not set initial SIS states: {e}")
            
            # Initialize PLC state
            self.processing_phase = 0  # Start in idle phase, let PLC logic handle transitions
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption(f"VirtuaPlant - {plant_type.title()} Plant (Improved)")
        
        # Fonts
        self.font_big = pygame.font.SysFont(None, 40)
        self.font_medium = pygame.font.SysFont(None, 26)
        self.font_small = pygame.font.SysFont(None, 18)
        
        # Colors (using pygame's THECOLORS)
        self.WHITE = pygame.color.THECOLORS['white']
        self.BLACK = pygame.color.THECOLORS['black']
        self.BLUE = pygame.color.THECOLORS['blue']
        self.RED = pygame.color.THECOLORS['red']
        self.GREEN = pygame.color.THECOLORS['green']
        self.BROWN = pygame.color.THECOLORS['brown']
        self.GRAY = pygame.color.THECOLORS['gray']
        self.DARK_GRAY = pygame.color.THECOLORS['gray20']
        self.DEEP_SKY_BLUE = pygame.color.THECOLORS['deepskyblue']
        self.DODGER_BLUE = pygame.color.THECOLORS['dodgerblue4']
        
        # Setup physics
        self._setup_physics()
        
    def _setup_physics(self):
        """Setup physics objects and collision handlers"""
        if self.plant_type == "bottle":
            self._setup_bottle_physics()
        else:
            self._setup_refinery_physics()
    
    def _setup_bottle_physics(self):
        """Setup bottle filling plant physics"""
        # Add base
        self._add_base()
        
        # Add nozzle
        self._add_nozzle()
        
        # Add sensors
        self._add_limit_switch()
        self._add_level_sensor()
        
        # Add initial bottle
        self._add_bottle()
        
        # Setup collision handlers
        self._setup_bottle_collisions()
    
    def _setup_refinery_physics(self):
        """Setup oil refinery physics - EXACT original implementation"""
        print("=" * 50)
        print("STARTING REFINERY PHYSICS SETUP")
        print("=" * 50)
        # Add pump
        self._add_pump()
        
        # Add oil unit (all the pipes and separator)
        self._add_oil_unit()
        
        # Add sensors
        print("Adding refinery sensors...")
        self._add_tank_level_sensor()
        self._add_spill_sensor()
        self._add_processed_sensor()
        print("Refinery sensors added!")
        
        # Add valves
        self._add_outlet_valve()
        self._add_separator_valve()
        self._add_waste_valve()
        
        # Setup collision handlers
        print("Setting up refinery collision handlers...")
        self._setup_refinery_collisions()
        print("Refinery setup complete!")
        print("=" * 50)
        print("REFINERY PHYSICS SETUP COMPLETE")
        print("=" * 50)
    
    def _add_base(self):
        """Add base platform"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (0, 550)  # Lower the base platform further
        shape = pymunk.Poly.create_box(body, (self.SCREEN_WIDTH, 20))
        shape.friction = 1.0
        shape.collision_type = 0x6  # base
        self.space.add(body, shape)
        self.actuators['base'] = shape
    
    def _add_nozzle(self):
        """Add water nozzle"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (400, 350)  # Lower nozzle to be visible on screen
        shape = pymunk.Poly.create_box(body, (15, 20))
        self.space.add(body, shape)
        self.actuators['nozzle'] = shape
    
    def _add_limit_switch(self):
        """Add limit switch sensor"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (200, 550)  # Lower to base level
        shape = pymunk.Circle(body, 2, (0, 0))
        shape.collision_type = 0x1  # switch
        self.space.add(body, shape)
        self.sensors['limit_switch'] = shape
    
    def _add_level_sensor(self):
        """Add level sensor"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (355, 350)  # Position near nozzle for bottle filling detection
        shape = pymunk.Circle(body, 3, (0, 0))
        shape.collision_type = 0x4  # level_sensor
        self.space.add(body, shape)
        self.sensors['level_sensor'] = shape
    
    def _add_bottle(self):
        """Add a bottle with proper geometry - EXACT original"""
        mass = 10
        moment = pymunk.moment_for_box(mass, (100, 150))  # width, height (updated for larger bottles)
        body = pymunk.Body(mass, moment)
        # Prevent bottles from falling due to gravity
        body.body_type = pymunk.Body.KINEMATIC
        # Ensure bottles only move horizontally, not vertically
        body.velocity = (0, 0)
        body.angular_velocity = 0
        
        # Space bottles out - start from right side and space them apart
        bottle_spacing = 120  # Space between bottles
        bottle_count = len(self.bottles)
        start_x = 300  # Start from center to ensure visibility
        bottle_x = start_x - (bottle_count * bottle_spacing)
        body.position = (bottle_x, 450)  # Raise bottles to be visible above base
        
        # Create bottle segments (left, right, bottom) - larger, more visible geometry
        l1 = pymunk.Segment(body, (-50, 0), (50, 0), 4.0)  # bottom (100 units wide, centered)
        l2 = pymunk.Segment(body, (-50, 0), (-50, 150), 4.0)  # left side
        l3 = pymunk.Segment(body, (50, 0), (50, 150), 4.0)  # right side
        
        # Glass friction
        l1.friction = 0.94
        l2.friction = 0.94
        l3.friction = 0.94
        
        # Set collision types
        l1.collision_type = 0x2  # bottle_bottom
        l2.collision_type = 0x3  # bottle_side
        l3.collision_type = 0x3  # bottle_side
        
        self.space.add(body, l1, l2, l3)
        self.bottles.append((l1, l2, l3, body))
    
    def _add_water_ball(self):
        """Add a water ball (drop) - EXACT original"""
        mass = 0.01
        radius = 3
        inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))
        body = pymunk.Body(mass, inertia)
        body.velocity_limit = 120
        body.angular_velocity_limit = 1
        x = random.randint(395, 405)  # Align with new nozzle position
        body.position = x, 330  # Lower water balls to be visible
        # Ensure no initial velocity and angular velocity
        body.velocity = (0, 0)
        body.angular_velocity = 0
        # Prevent any forces from being applied initially
        body.force = (0, 0)
        body.torque = 0
        shape = pymunk.Circle(body, radius, (0, 0))
        shape.collision_type = 0x5  # liquid
        self.space.add(body, shape)
        self.water_balls.append(shape)
        # Track total balls created
        self.total_balls_created = getattr(self, 'total_balls_created', 0) + 1
    
    def _add_oil_ball(self):
        """Add an oil ball - EXACT original with improved physics and collision prediction"""
        mass = 0.01
        radius = 2
        inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))
        body = pymunk.Body(mass, inertia)
        body.velocity_limit = 120
        body.angular_velocity_limit = 1
        x = random.randint(69, 70)
        body.position = x, 565
        
        # Ensure no initial velocity to prevent falling through
        body.velocity = (0, 0)
        body.angular_velocity = 0
        body.force = (0, 0)
        body.torque = 0
        
        shape = pymunk.Circle(body, radius, (0, 0))
        shape.friction = 0.0
        shape.collision_type = 0x5  # ball_collision (liquid)
        shape.filter = pymunk.ShapeFilter(categories=0b0010, mask=0xFFFF)  # CAT_OIL
        shape.sensor = False  # Ensure oil balls are solid, not sensors
        self.space.add(body, shape)
        self.oil_balls.append(shape)
        
        # Track oil ball creation with actual valve state info
        try:
            outlet_valve = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE')
            sep_valve = self.modbus_bridge.get_tag_value('ACT_SEP_VALVE')
            print(f"Oil ball created at position: ({x}, 565) | Outlet valve: {outlet_valve}, Sep valve: {sep_valve}")
            
            # COLLISION PREDICTION: Check if this ball would immediately fall through a closed valve
            # Outlet valve is at (70, 410) - if it's closed, prevent the ball from falling through
            if outlet_valve == 0:  # Valve is closed
                outlet_valve_pos = pymunk.Vec2d(70, 410)
                ball_pos = pymunk.Vec2d(x, 565)
                distance_to_valve = (ball_pos - outlet_valve_pos).length
                
                # If the ball is created very close to the closed valve, apply immediate stopping force
                if distance_to_valve < 200:  # Within 200 units of the valve
                    print(f"COLLISION PREDICTION: Oil ball created near CLOSED outlet valve (distance: {distance_to_valve:.1f})")
                    print("Applying immediate stopping force to prevent fall-through...")
                    body.force = (0, -500)  # Strong upward force to stop the ball
                    body.velocity = (0, 0)  # Stop all movement
                    body.angular_velocity = 0  # Stop rotation
        except Exception as e:
            print(f"Error reading valve states for collision prediction: {e}")
        

    
    def _setup_bottle_collisions(self):
        """Setup collision handlers for bottle plant"""
        # Temporarily disabled for debugging
        pass
        # Limit switch with bottle bottom
        # self.space.on_collision(0x1, 0x2, self._bottle_in_place)
        # Level sensor with water
        # self.space.on_collision(0x4, 0x5, self._level_ok)
    
    def _bottle_in_place(self, arbiter, space, data):
        """Bottle is in filling position"""
        self.modbus_bridge.update_sensors({
            'SENSOR_LIMIT_SWITCH': True,
            'SENSOR_LEVEL_SENSOR': False
        })
        return True
    
    def _level_ok(self, arbiter, space, data):
        """Water level reached"""
        self.modbus_bridge.update_sensors({
            'SENSOR_LIMIT_SWITCH': False,
            'SENSOR_LEVEL_SENSOR': True
        })
        return True
    
    def _add_pump(self):
        """Add feed pump - EXACT original"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (70, 585)
        shape = pymunk.Poly.create_box(body, (15, 20))
        self.space.add(body, shape)
        self.actuators['pump'] = shape
    
    def _add_oil_unit(self):
        """Add oil unit with all pipes - EXACT original implementation"""
        # Define collision categories
        CAT_PIPE = 0b0001
        CAT_OIL = 0b0010
        
        # Use space.static_body for all pipe segments to prevent transform errors
        # Adjust coordinates to account for missing body positioning (was at 300,300)
        # Oil storage unit
        l1 = pymunk.Segment(self.space.static_body, (22, 550), (22, 445), 3)  # left side line
        l2 = pymunk.Segment(self.space.static_body, (22, 445), (54, 407), 3) 
        l3 = pymunk.Segment(self.space.static_body, (120, 550), (120, 445), 3)  # right side line
        l4 = pymunk.Segment(self.space.static_body, (120, 445), (85, 407), 3) 

        # Pipe to separator vessel
        l5 = pymunk.Segment(self.space.static_body, (54, 407), (54, 353), 3)  # left side vertical line
        l6 = pymunk.Segment(self.space.static_body, (54, 353), (281, 353), 3)  # bottom horizontal line
        l7 = pymunk.Segment(self.space.static_body, (281, 353), (281, 333), 3)
        l8 = pymunk.Segment(self.space.static_body, (85, 407), (85, 380), 3)  # right side vertical line
        l9 = pymunk.Segment(self.space.static_body, (85, 380), (307, 380), 3)  # top horizontal line
        l10 = pymunk.Segment(self.space.static_body, (307, 380), (307, 333), 3) 

        # Separator vessel
        l11 = pymunk.Segment(self.space.static_body, (281, 331), (205, 331), 3)  # top left horizontal line
        l12 = pymunk.Segment(self.space.static_body, (205, 331), (205, 277), 3)  # left side vertical line
        l13 = pymunk.Segment(self.space.static_body, (205, 277), (217, 277), 3) 
        l14 = pymunk.Segment(self.space.static_body, (217, 277), (220, 220), 3)  # left waste exit line
        l15 = pymunk.Segment(self.space.static_body, (232, 220), (235, 277), 3)  # right waste exit line
        l16 = pymunk.Segment(self.space.static_body, (235, 277), (255, 277), 3) 
        l17 = pymunk.Segment(self.space.static_body, (255, 277), (255, 233), 3)  # elevation vertical line 
        l18 = pymunk.Segment(self.space.static_body, (255, 233), (313, 233), 3)  # left bottom line
        l19 = pymunk.Segment(self.space.static_body, (313, 233), (313, 218), 3)  # left side separator exit line
        l20 = pymunk.Segment(self.space.static_body, (343, 218), (343, 233), 3)  # right side separator exit line
        l21 = pymunk.Segment(self.space.static_body, (343, 233), (365, 238), 3)  # right side diagonal line
        l22 = pymunk.Segment(self.space.static_body, (365, 238), (377, 331), 3)  # right vertical line
        l23 = pymunk.Segment(self.space.static_body, (377, 331), (307, 331), 3)  # top right horizontal line
        l24 = pymunk.Segment(self.space.static_body, (297, 233), (297, 310), 5)  # center separator line (thicker)
        l35 = pymunk.Segment(self.space.static_body, (297, 310), (235, 277), 3)
     
        # Separator exit pipe
        l25 = pymunk.Segment(self.space.static_body, (343, 215), (343, 187), 3)  # right side vertical line
        l26 = pymunk.Segment(self.space.static_body, (343, 187), (880, 187), 3)  # top horizontal line
        l27 = pymunk.Segment(self.space.static_body, (313, 215), (313, 160), 3)  # left vertical line
        l28 = pymunk.Segment(self.space.static_body, (313, 160), (880, 160), 3)  # bottom horizontal line

        # Waste water pipe
        l29 = pymunk.Segment(self.space.static_body, (213, 215), (213, 188), 3)  # left side waste line
        l30 = pymunk.Segment(self.space.static_body, (240, 215), (240, 160), 3)  # right side waste line
        l31 = pymunk.Segment(self.space.static_body, (213, 188), (137, 188), 3)  # top horizontal line
        l32 = pymunk.Segment(self.space.static_body, (240, 160), (166, 160), 3)  # bottom horizontal line
        l33 = pymunk.Segment(self.space.static_body, (137, 188), (137, 115), 3)  # left side vertical line
        l34 = pymunk.Segment(self.space.static_body, (166, 160), (166, 115), 3)  # right side vertical line

        # Add collision filters to all pipe segments
        pipe_segments = [l1, l2, l3, l4, l5, l6, l7, l8, l9, l10, l11, l12, l13, l14, l15, 
                        l16, l17, l18, l19, l20, l21, l22, l23, l24, l25, 
                        l26, l27, l28, l29, l30, l31, l32, l33, l34, l35]
        
        # Set collision filters for all pipe segments
        for segment in pipe_segments:
            segment.filter = pymunk.ShapeFilter(categories=CAT_PIPE, mask=0xFFFF)
            segment.sensor = False  # Ensure segments are solid, not sensors
        
        # Add only the shapes to the space (static body is already in space)
        self.space.add(l1, l2, l3, l4, l5, l6, l7, l8, l9, l10, l11, l12, l13, l14, l15, 
                        l16, l17, l18, l19, l20, l21, l22, l23, l24, l25, 
                        l26, l27, l28, l29, l30, l31, l32, l33, l34, l35)
        print(f"Added {len(pipe_segments)} pipe segments to space.static_body with increased radius")
        
        # Debug: Check if segments are actually in the space
        print(f"Space has {len(self.space.shapes)} shapes total")
        static_shapes = [s for s in self.space.shapes if s.body.body_type == pymunk.Body.STATIC]
        print(f"Space has {len(static_shapes)} static shapes")
        
        # Debug: Check a few pipe segment positions
        print(f"Static body position: {self.space.static_body.position}")
        print(f"First pipe segment (l1) position: {l1.a} to {l1.b}")
        print(f"Second pipe segment (l2) position: {l2.a} to {l2.b}")
        
        # Collision detection verified - test ball removed

        self.actuators['oil_unit'] = pipe_segments
    
    def _add_outlet_valve(self):
        """Add outlet valve - RE-ENABLED WITH IMPROVED PHYSICS"""
        # Use space.static_body for valve segments
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (70, 410)
        a = (-14, 0)
        b = (14, 0)
        radius = 3  # Increased radius for better collision detection
        shape = pymunk.Segment(body, a, b, radius)
        shape.collision_type = 0x6  # outlet_valve_collision
        shape.filter = pymunk.ShapeFilter(categories=0b0001, mask=0xFFFF)  # CAT_PIPE
        shape.sensor = False
        
        # Store valve components for dynamic control
        self.outlet_valve_body = body
        self.outlet_valve_shape = shape
        self.actuators['outlet_valve'] = shape
        
        # Initially add to space (valve starts closed)
        self.space.add(body, shape)
        print("Outlet valve physical geometry created and added to space (CLOSED)")
    
    def _add_separator_valve(self):
        """Add separator valve - RE-ENABLED WITH IMPROVED PHYSICS"""
        # Use space.static_body for valve segments
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (327, 218)
        radius = 3  # Increased radius for better collision detection
        a = (-15, 0)
        b = (15, 0)
        shape = pymunk.Segment(body, a, b, radius)
        shape.collision_type = 0x7  # sep_valve_collision
        shape.filter = pymunk.ShapeFilter(categories=0b0001, mask=0xFFFF)  # CAT_PIPE
        shape.sensor = False
        
        # Store valve components for dynamic control
        self.sep_valve_body = body
        self.sep_valve_shape = shape
        self.actuators['sep_valve'] = shape
        
        # Initially add to space (valve starts closed)
        self.space.add(body, shape)
        print("Separator valve physical geometry created and added to space (CLOSED)")
    
    def _add_waste_valve(self):
        """Add waste valve - RE-ENABLED WITH IMPROVED PHYSICS"""
        # Use space.static_body for valve segments
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (225, 218)
        radius = 3  # Increased radius for better collision detection
        a = (-8, 0)
        b = (9, 0)
        shape = pymunk.Segment(body, a, b, radius)
        shape.collision_type = 0x8  # waste_valve_collision
        shape.filter = pymunk.ShapeFilter(categories=0b0001, mask=0xFFFF)  # CAT_PIPE
        shape.sensor = False
        
        # Store valve components for dynamic control
        self.waste_valve_body = body
        self.waste_valve_shape = shape
        self.actuators['waste_valve'] = shape
        
        # Initially add to space (valve starts closed)
        self.space.add(body, shape)
        print("Waste valve physical geometry created and added to space (CLOSED)")
    
    def _add_tank_level_sensor(self):
        """Add tank level sensor - EXACT original"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (115, 535)
        radius = 10  # Reasonable radius for collision detection
        shape = pymunk.Circle(body, radius, (0, 0))
        shape.collision_type = 0x4  # tank_level_collision
        self.space.add(body, shape)
        self.sensors['tank_level'] = shape
        print(f"Tank level sensor created at position: {body.position} with radius: {radius}")
    
    def _add_spill_sensor(self):
        """Add spill sensor - EXACT original"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (0, 100)
        radius = 7
        a = (0, 75)
        b = (137, 75)
        shape = pymunk.Segment(body, a, b, radius)
        shape.collision_type = 0x9  # oil_spill_collision
        self.space.add(body, shape)
        self.sensors['spill_sensor'] = shape
    
    def _add_processed_sensor(self):
        """Add processed sensor - EXACT original"""
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (327, 218)
        radius = 7
        a = (-12, -5)
        b = (12, -5)
        shape = pymunk.Segment(body, a, b, radius)
        shape.collision_type = 0x3  # oil_processed_collision
        shape.sensor = True  # Make it a sensor so it doesn't block oil flow
        self.space.add(body, shape)
        self.sensors['processed_sensor'] = shape
    
    def _setup_refinery_collisions(self):
        """Setup collision handlers for refinery - EXACT original implementation"""
        try:
            print("Setting up refinery collision handlers...")
            
            # When oil collides with tank_level, call level_reached
            self.space.on_collision(0x4, 0x5, begin=self._level_reached)
            print("Tank level collision handler set up successfully")
            
            # When oil touches the oil_spill marker, call oil_spilled
            self.space.on_collision(0x9, 0x5, begin=self._oil_spilled)
            print("Oil spill collision handler set up successfully")
            
            # When oil touches the oil_process marker, call oil_processed
            self.space.on_collision(0x3, 0x5, begin=self._oil_processed)
            print("Oil processed collision handler set up successfully")
            
            # Add collision handler for debugging pipe collisions
            self.space.on_collision(0x5, 0x0, begin=self._debug_pipe_collision)
            print("Debug pipe collision handler set up successfully")
            
            # VALVE COLLISIONS DISABLED - Using physical geometry instead
            # Valves will be controlled by adding/removing physical segments
            print("Valve collision handlers DISABLED - using physical geometry control")
            
            # Pipe segments are solid walls - no collision handlers needed
            # They will naturally block oil balls as static objects
            print("Pipe segments are solid walls - no collision handlers needed")
                
            print("All refinery collision handlers setup complete!")
        except Exception as e:
            print(f"Warning: Could not setup all collision handlers: {e}")
    
    def _level_reached(self, arbiter, space, data):
        """Level sensor hit - EXACT original"""
        print("TANK LEVEL SENSOR TRIGGERED!")
        print(f"Oil ball position: {arbiter.shapes[0].body.position}")
        print(f"Sensor position: {arbiter.shapes[1].body.position}")
        
        # Update legacy tank level sensor (binary)
        self.modbus_bridge.update_sensors({'SENSOR_TANK_LEVEL': 1})
        
        # Update continuous tank level (0-10000 for 0-100%)
        current_level = self.modbus_bridge.get_tag_value('LT_TANK_LEVEL_PCT') or 5000
        new_level = min(10000, current_level + 500)  # Increase by 5%
        self.modbus_bridge.update_sensors({'LT_TANK_LEVEL_PCT': new_level})
        
        # Check for LSHH trip (independent high-high switch)
        if new_level >= 9500:  # 95% threshold for LSHH
            self.modbus_bridge.update_sensors({'SIS_TANK_LSHH': 1})
            print("SIS: LSHH switch triggered at 95% level!")
        
        # Check for low-low sensor
        if new_level <= 1000:  # 10% threshold for LL
            self.modbus_bridge.update_sensors({'SENSOR_TANK_LL': 1})
            print("SIS: Low-Low sensor triggered at 10% level!")
        else:
            self.modbus_bridge.update_sensors({'SENSOR_TANK_LL': 0})
        
        return True
    
    def _oil_spilled(self, arbiter, space, data):
        """Oil spilled - EXACT original"""
        print("Oil Spilled")
        # Update spill counter
        current_spill = self.modbus_bridge.get_tag_value('SENSOR_OIL_SPILL') or 0
        self.modbus_bridge.update_sensors({'SENSOR_OIL_SPILL': current_spill + 1})
        return True
    
    def _oil_processed(self, arbiter, space, data):
        """Oil processed - EXACT original"""
        print("Oil Processed")
        # Update processed counter
        current_processed = self.modbus_bridge.get_tag_value('SENSOR_OIL_PROCESSED') or 0
        new_processed = current_processed + 1
        if new_processed >= 65000:
            self.modbus_bridge.update_sensors({'SENSOR_OIL_PROCESSED': 65000})
            self.modbus_bridge.update_sensors({'SENSOR_OIL_UPPER': new_processed - 65000})
        else:
            self.modbus_bridge.update_sensors({'SENSOR_OIL_PROCESSED': new_processed})
        return True
    
    def _no_collision(self, arbiter, space, data):
        """No collision - EXACT original"""
        return True
    
    def _debug_pipe_collision(self, arbiter, space, data):
        """Debug collision handler for pipe segments"""
        # Determine which shape is the oil ball and which is the pipe
        if arbiter.shapes[0].collision_type == 0x5:  # Oil ball
            oil_ball = arbiter.shapes[0]
            pipe_segment = arbiter.shapes[1]
        else:
            oil_ball = arbiter.shapes[1]
            pipe_segment = arbiter.shapes[0]
        
        print(f"*** PIPE COLLISION DETECTED ***")
        print(f"Oil ball position: {oil_ball.body.position}")
        print(f"Oil ball velocity: {oil_ball.body.velocity}")
        print(f"Pipe segment: {pipe_segment}")
        print(f"Collision normal: {arbiter.normal}")
        print("*** END PIPE COLLISION ***")
        
        return True  # Allow normal collision (bounce off pipe)
    

    
    def _update_valve_collisions(self):
        """Update valve physical geometry based on current valve states - FIXED APPROACH"""
        try:
            outlet_valve = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE')
            sep_valve = self.modbus_bridge.get_tag_value('ACT_SEP_VALVE')
            waste_valve = self.modbus_bridge.get_tag_value('ACT_WASTE_VALVE')
            feed_pump = self.modbus_bridge.get_tag_value('ACT_FEED_PUMP')
            tank_level = self.modbus_bridge.get_tag_value('SENSOR_TANK_LEVEL')
            
            # SIS CONTROL LOGIC - Integrated into simulation
            # This simulates the OpenPLC runtime behavior with SIS protection
            
            # Get SIS state (stored as internal state)
            sis_tripped = getattr(self, 'sis_tripped', False)
            
            # Get current sensor values
            sis_lshh = self.modbus_bridge.get_tag_value('SIS_TANK_LSHH') or 0
            tank_level_pct = self.modbus_bridge.get_tag_value('LT_TANK_LEVEL_PCT') or 5000
            sensor_ll = self.modbus_bridge.get_tag_value('SENSOR_TANK_LL') or 0
            cmd_reset = self.modbus_bridge.get_tag_value('CMD_SIS_RESET') or 0
            
            # Get setpoints
            sp_hi = self.modbus_bridge.get_tag_value('SP_HI_PCT') or 8000  # 80%
            sp_lo = self.modbus_bridge.get_tag_value('SP_LO_PCT') or 2000  # 20%
            
            print(f"SIS Control - LSHH: {sis_lshh}, Level: {tank_level_pct/100:.1f}%, Trip: {sis_tripped}")
            
            # SIS: Independent LSHH latch & manual reset
            if sis_lshh == 1:
                sis_tripped = True
                print("SIS: LSHH triggered - trip latched")
            
            if cmd_reset == 1 and sis_lshh == 0:
                sis_tripped = False
                print("SIS: Reset command - trip cleared")
            
            # Store SIS state
            self.sis_tripped = sis_tripped
            
            # Update alarms
            self.modbus_bridge.set_tag_value('ALM_SIS_LSHH_TRIP', 1 if sis_tripped else 0)
            self.modbus_bridge.set_tag_value('ALM_LL_TRIP', 1 if sensor_ll == 1 else 0)
            
            # Base permissives (no pump if LL or SIS trip)
            if sensor_ll == 1 or sis_tripped:
                self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', 0)
                print("SIS: Pump stopped due to LL or SIS trip")
            
            # Overfill response
            if sis_tripped:
                # Terminate inlet/receipt and divert liquid to slop
                self.modbus_bridge.set_tag_value('ACT_INLET_VALVE', 0)
                self.modbus_bridge.set_tag_value('ACT_SLOP_VALVE', 1)
                self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', 1)
                self.modbus_bridge.set_tag_value('ACT_FLARE_VALVE', 0)
                print("SIS: Overfill response - inlet closed, slop open")
            else:
                # Normal BPCS band control on LT
                if tank_level_pct < sp_lo:
                    self.modbus_bridge.set_tag_value('ACT_INLET_VALVE', 1)
                    self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', 1)
                    if sensor_ll == 0:
                        self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', 1)
                    self.modbus_bridge.set_tag_value('ACT_SLOP_VALVE', 0)
                    self.modbus_bridge.set_tag_value('ACT_FLARE_VALVE', 0)
                    print("BPCS: Low level - inlet open, pump on")
                elif tank_level_pct > sp_hi:
                    self.modbus_bridge.set_tag_value('ACT_INLET_VALVE', 0)
                    self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', 1)
                    self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', 1)
                    self.modbus_bridge.set_tag_value('ACT_SLOP_VALVE', 0)
                    self.modbus_bridge.set_tag_value('ACT_FLARE_VALVE', 0)
                    print("BPCS: High level - inlet closed, pump down")
                else:
                    # mid-band hold
                    self.modbus_bridge.set_tag_value('ACT_INLET_VALVE', 1)
                    self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', 1)
                    if sensor_ll == 0:
                        self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', 0)
                    self.modbus_bridge.set_tag_value('ACT_SLOP_VALVE', 0)
                    self.modbus_bridge.set_tag_value('ACT_FLARE_VALVE', 0)
                    print("BPCS: Mid-band - holding")
            
            # Legacy compatibility - maintain existing valve controls for simulation
            outlet_valve = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE') or 0
            slop_valve = self.modbus_bridge.get_tag_value('ACT_SLOP_VALVE') or 0
            self.modbus_bridge.set_tag_value('ACT_SEP_VALVE', outlet_valve)  # separator follows outlet
            self.modbus_bridge.set_tag_value('ACT_WASTE_VALVE', slop_valve)  # waste follows slop
            
            # Auto-control waste valve: open when separator valve is open (for simulation compatibility)
            if sep_valve == 1 and waste_valve == 0:
                self.modbus_bridge.set_tag_value('ACT_WASTE_VALVE', 1)
                waste_valve = 1
                print("Auto-opening waste valve (separator valve is open)")
            elif sep_valve == 0 and waste_valve == 1:
                self.modbus_bridge.set_tag_value('ACT_WASTE_VALVE', 0)
                waste_valve = 0
                print("Auto-closing waste valve (separator valve is closed)")
            
            print(f"Current valve states - Outlet: {outlet_valve}, Sep: {sep_valve}, Waste: {waste_valve}")
            
            # Update outlet valve physical geometry
            if outlet_valve == 1:  # Valve is OPEN - remove physical barrier
                if hasattr(self, 'outlet_valve_shape') and self.outlet_valve_shape in self.space.shapes:
                    self.space.remove(self.outlet_valve_shape)
                    print("Outlet valve physical geometry REMOVED (OPEN)")
                elif hasattr(self, 'outlet_valve_shape'):
                    print("Outlet valve shape exists but not in space (already removed)")
                else:
                    print("Outlet valve shape does not exist")
            else:  # Valve is CLOSED - add physical barrier
                if hasattr(self, 'outlet_valve_shape') and self.outlet_valve_shape not in self.space.shapes:
                    self.space.add(self.outlet_valve_shape)
                    print("Outlet valve physical geometry ADDED (CLOSED)")
                elif hasattr(self, 'outlet_valve_shape') and self.outlet_valve_shape in self.space.shapes:
                    print("Outlet valve shape already in space (already closed)")
                else:
                    print("Outlet valve shape does not exist")
            
            # Update separator valve physical geometry
            if sep_valve == 1:  # Valve is OPEN - remove physical barrier
                if hasattr(self, 'sep_valve_shape') and self.sep_valve_shape in self.space.shapes:
                    self.space.remove(self.sep_valve_shape)
                    print("Separator valve physical geometry REMOVED (OPEN)")
                elif hasattr(self, 'sep_valve_shape'):
                    print("Separator valve shape exists but not in space (already removed)")
                else:
                    print("Separator valve shape does not exist")
            else:  # Valve is CLOSED - add physical barrier
                if hasattr(self, 'sep_valve_shape') and self.sep_valve_shape not in self.space.shapes:
                    self.space.add(self.sep_valve_shape)
                    print("Separator valve physical geometry ADDED (CLOSED)")
                elif hasattr(self, 'sep_valve_shape') and self.sep_valve_shape in self.space.shapes:
                    print("Separator valve shape already in space (already closed)")
                else:
                    print("Separator valve shape does not exist")
            
            # Update waste valve physical geometry
            if waste_valve == 1:  # Valve is OPEN - remove physical barrier
                if hasattr(self, 'waste_valve_shape') and self.waste_valve_shape in self.space.shapes:
                    self.space.remove(self.waste_valve_shape)
                    print("Waste valve physical geometry REMOVED (OPEN)")
                elif hasattr(self, 'waste_valve_shape'):
                    print("Waste valve shape exists but not in space (already removed)")
                else:
                    print("Waste valve shape does not exist")
            else:  # Valve is CLOSED - add physical barrier
                if hasattr(self, 'waste_valve_shape') and self.waste_valve_shape not in self.space.shapes:
                    self.space.add(self.waste_valve_shape)
                    print("Waste valve physical geometry ADDED (CLOSED)")
                elif hasattr(self, 'waste_valve_shape') and self.waste_valve_shape in self.space.shapes:
                    print("Waste valve shape already in space (already closed)")
                else:
                    print("Waste valve shape does not exist")
                
        except Exception as e:
            print(f"Error updating valve physical geometry: {e}")
    
    def _outlet_valve_open(self, arbiter, space, data):
        """Outlet valve open - FIXED to allow flow"""
        print("=== OUTLET VALVE COLLISION DETECTED ===")
        print("Outlet valve open - oil ball passing through")
        # Get the oil ball that's passing through
        oil_ball = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 0x5 else arbiter.shapes[1]
        print(f"Oil ball position at valve: {oil_ball.body.position}")
        
        # Don't apply any forces - just let the oil pass through naturally
        print("=== END OUTLET VALVE COLLISION ===")
        
        return False  # Allow collision (oil passes through)
    
    def _outlet_valve_closed(self, arbiter, space, data):
        """Outlet valve closed - FIXED to block flow"""
        print("=== OUTLET VALVE COLLISION DETECTED ===")
        print("Outlet valve closed - oil ball blocked")
        # Get the oil ball that's being blocked
        oil_ball = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 0x5 else arbiter.shapes[1]
        print(f"Oil ball position at closed outlet valve: {oil_ball.body.position}")
        print("=== END OUTLET VALVE COLLISION ===")
        return True  # Block collision (oil stops)
    
    def _sep_valve_open(self, arbiter, space, data):
        """Separator valve open - FIXED to allow flow"""
        print("=== SEPARATOR VALVE COLLISION DETECTED ===")
        print("Separator valve open - oil ball passing through")
        # Get the oil ball that's passing through
        oil_ball = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 0x5 else arbiter.shapes[1]
        print(f"Oil ball position at separator valve: {oil_ball.body.position}")
        print("=== END SEPARATOR VALVE COLLISION ===")
        return False  # Allow collision (oil passes through)
    
    def _sep_valve_closed(self, arbiter, space, data):
        """Separator valve closed - FIXED to block flow"""
        print("=== SEPARATOR VALVE COLLISION DETECTED ===")
        print("Separator valve closed - oil ball blocked")
        # Get the oil ball that's being blocked
        oil_ball = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 0x5 else arbiter.shapes[1]
        print(f"Oil ball position at closed separator valve: {oil_ball.body.position}")
        print("=== END SEPARATOR VALVE COLLISION ===")
        return True  # Block collision (oil stops)
    
    def _waste_valve_open(self, arbiter, space, data):
        """Waste valve open - FIXED to allow flow"""
        print("=== WASTE VALVE COLLISION DETECTED ===")
        print("Waste valve open - oil ball passing through")
        # Get the oil ball that's passing through
        oil_ball = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 0x5 else arbiter.shapes[1]
        print(f"Oil ball position at waste valve: {oil_ball.body.position}")
        print("=== END WASTE VALVE COLLISION ===")
        return False  # Allow collision (oil passes through)
    
    def _waste_valve_closed(self, arbiter, space, data):
        """Waste valve closed - FIXED to block flow"""
        print("=== WASTE VALVE COLLISION DETECTED ===")
        print("Waste valve closed - oil ball blocked")
        # Get the oil ball that's being blocked
        oil_ball = arbiter.shapes[0] if arbiter.shapes[0].collision_type == 0x5 else arbiter.shapes[1]
        print(f"Oil ball position at closed waste valve: {oil_ball.body.position}")
        print("=== END WASTE VALVE COLLISION ===")
        return True  # Block collision (oil stops)
    
    def _move_camera(self, dx, dy):
        """Move camera by delta x, y"""
        if self.plant_type == "refinery":
            self.CAMERA_X += dx
            self.CAMERA_Y += dy
            print(f"Camera moved to: X={self.CAMERA_X}, Y={self.CAMERA_Y}")
    
    def _reset_camera(self):
        """Reset camera to default position"""
        if self.plant_type == "refinery":
            self.CAMERA_X = 275
            self.CAMERA_Y = -50
            print(f"Camera reset to: X={self.CAMERA_X}, Y={self.CAMERA_Y}")
    
    def _toggle_debug_mode(self):
        """Toggle debug mode for manual controls"""
        self.debug_mode = not self.debug_mode
        print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
    
    def _adjust_camera_step(self, delta):
        """Adjust camera movement step size"""
        self.camera_step = max(1, min(50, self.camera_step + delta))
        print(f"Camera step size: {self.camera_step}")
    
    def _to_pygame(self, p):
        """Convert pymunk world coordinates to pygame screen coordinates"""
        if self.plant_type == "bottle":
            return int(p.x), int(self.SCREEN_HEIGHT - (p.y - self.CAMERA_Y))
        else:  # refinery - center the view
            return int(p.x + self.CAMERA_X), int(self.SCREEN_HEIGHT - (p.y - self.CAMERA_Y))
    
    def _to_world(self, screen_x, screen_y):
        """Convert pygame screen coordinates to pymunk world coordinates"""
        if self.plant_type == "bottle":
            return screen_x, self.SCREEN_HEIGHT - screen_y + self.CAMERA_Y
        else:  # refinery - center the view
            return screen_x - self.CAMERA_X, self.SCREEN_HEIGHT - screen_y + self.CAMERA_Y
    
    def _draw_ball(self, screen, ball, color=None):
        """Draw a ball"""
        if color is None:
            color = self.BLUE
        p = self._to_pygame(ball.body.position)
        pygame.draw.circle(screen, color, p, int(ball.radius), 2)
    
    def _draw_lines(self, screen, lines, color=None):
        """Draw bottle lines"""
        if color is None:
            color = self.DODGER_BLUE
        for line in lines:
            body = line.body
            pv1 = body.position + line.a.rotated(body.angle)
            pv2 = body.position + line.b.rotated(body.angle)
            p1 = self._to_pygame(pv1)
            p2 = self._to_pygame(pv2)
            pygame.draw.lines(screen, color, False, [p1, p2])
    
    def _draw_line(self, screen, line, color=None):
        """Draw a single line - EXACT original"""
        body = line.body
        pv1 = body.position + line.a.rotated(body.angle)
        pv2 = body.position + line.b.rotated(body.angle)
        p1 = self._to_pygame(pv1)
        p2 = self._to_pygame(pv2)
        if color is None:
            pygame.draw.lines(screen, self.BLACK, False, [p1, p2])
        else:
            pygame.draw.lines(screen, color, False, [p1, p2])
    
    def _draw_polygon(self, screen, shape, color=None):
        """Draw a polygon"""
        if color is None:
            color = self.BLACK
        points = shape.get_vertices()
        fpoints = []
        for p in points:
            fpoints.append(self._to_pygame(p))
        pygame.draw.polygon(screen, color, fpoints)
    
    def start(self):
        """Start the improved pygame frontend"""
        self.running = True
        clock = pygame.time.Clock()
        
        print(f"Starting improved {self.plant_type} plant visualization...")
        print("Physics setup complete, entering main loop...")
        
        ticks_to_next_ball = 1
        
        while self.running:
            clock.tick(self.FPS)
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self._toggle_run()
                    elif event.key == pygame.K_n:
                        self._toggle_nozzle()
                    elif event.key == pygame.K_m:
                        self._toggle_motor()
                    elif event.key == pygame.K_TAB:
                        self._add_bottle()  # Add new bottle
                    elif event.key == pygame.K_d:
                        self.show_debug_rectangles = not self.show_debug_rectangles  # Toggle debug rectangles
                    elif event.key == pygame.K_a:
                        self.show_world_axes = not self.show_world_axes  # Toggle world axes
                    elif event.key == pygame.K_c:
                        self._toggle_debug_mode()  # Toggle debug mode
                    elif event.key == pygame.K_r:
                        self._reset_camera()  # Reset camera
                    elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                        self._adjust_camera_step(1)  # Increase step size
                    elif event.key == pygame.K_MINUS:
                        self._adjust_camera_step(-1)  # Decrease step size
                    
                    # Camera movement controls (only in debug mode)
                    if self.debug_mode:
                        if event.key == pygame.K_LEFT:
                            self._move_camera(-self.camera_step, 0)  # Move left
                        elif event.key == pygame.K_RIGHT:
                            self._move_camera(self.camera_step, 0)  # Move right
                        elif event.key == pygame.K_UP:
                            self._move_camera(0, -self.camera_step)  # Move up
                        elif event.key == pygame.K_DOWN:
                            self._move_camera(0, self.camera_step)  # Move down
            
            # Fixed order: spawn → physics → cleanup → count → draw
            try:
                # 1. Spawn new objects
                ticks_to_next_ball = self._update_physics(ticks_to_next_ball)
                
                # 2. Fixed timestep physics with accumulator and substeps for better collision detection
                self.physics_accumulator += 1.0 / self.FPS
                while self.physics_accumulator >= self.PHYSICS_DT:
                    self._step_with_substeps(self.PHYSICS_DT)
                    self.physics_accumulator -= self.PHYSICS_DT
                
                # 3. Cleanup off-screen objects (after physics step)
                self._cleanup_objects()
                
                # 4. Draw everything (after cleanup, so counts are accurate)
                self._draw()
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                import traceback
                traceback.print_exc()
            
            # Update display
            pygame.display.flip()
        
        pygame.quit()
    
    def _step_with_substeps(self, dt):
        """Step physics with substeps to prevent tunneling"""
        # Use substeps for better collision detection when objects move fast
        max_substep_size = 1.0 / 240.0  # 240 Hz substeps
        num_substeps = max(1, int(dt / max_substep_size))
        substep_dt = dt / num_substeps
        
        for _ in range(num_substeps):
            self.space.step(substep_dt)
    
    def _update_physics(self, ticks_to_next_ball):
        """Update physics simulation - EXACT original logic"""
        if self.plant_type == "bottle":
            return self._update_bottle_physics(ticks_to_next_ball)
        else:
            return self._update_refinery_physics(ticks_to_next_ball)
    
    def _update_bottle_physics(self, ticks_to_next_ball):
        """Update bottle physics - EXACT original"""
        run_cmd = self.modbus_bridge.get_tag_value('CMD_RUN')
        
        if run_cmd:
            # Motor Logic (EXACT from original)
            limit_switch = self.modbus_bridge.get_tag_value('SENSOR_LIMIT_SWITCH')
            level_sensor = self.modbus_bridge.get_tag_value('SENSOR_LEVEL_SENSOR')
            
            if limit_switch == 1:
                self.modbus_bridge.set_tag_value('ACT_MOTOR', False)
            
            if level_sensor == 1:
                self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
            
            if not limit_switch:
                self.modbus_bridge.set_tag_value('ACT_MOTOR', True)
            
            # Add water balls
            nozzle_open = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
            if ticks_to_next_ball <= 0 and nozzle_open:
                ticks_to_next_ball = 1
                self._add_water_ball()
            
            # Decrement ticks
            ticks_to_next_ball -= 1
            
            # Move bottles - RIGHT TO LEFT (reversed from original)
            motor_on = self.modbus_bridge.get_tag_value('ACT_MOTOR')
            if motor_on == 1:
                for bottle in self.bottles:
                    current_pos = bottle[3].position
                    bottle[3].position = (current_pos.x - 0.01, current_pos.y)  # Move left much slower
        else:
            self.modbus_bridge.set_tag_value('ACT_MOTOR', False)
        
        return ticks_to_next_ball
    
    def _update_refinery_physics(self, ticks_to_next_ball):
        """Update refinery physics - EXACT original"""
        feed_pump = self.modbus_bridge.get_tag_value('ACT_FEED_PUMP')
        
        # Update valve collision handlers based on current valve states
        self._update_valve_collisions()
        
        # Debug: Track oil ball positions every 60 frames (more frequent)
        if hasattr(self, 'frame_count') and self.frame_count % 60 == 0:
            print(f"\n=== OIL BALL POSITION DEBUG (Frame {self.frame_count}) ===")
            tank_count = 0
            separator_count = 0
            waste_count = 0
            other_count = 0
            
            for ball in self.oil_balls:
                pos = ball.body.position
                if pos.y > 400:  # Tank area
                    tank_count += 1
                elif pos.y > 200 and pos.y <= 400:  # Separator area
                    separator_count += 1
                elif pos.y <= 200:  # Waste/processed area
                    waste_count += 1
                else:
                    other_count += 1
            
            print(f"Oil balls in tank area (Y>400): {tank_count}")
            print(f"Oil balls in separator area (200<Y<=400): {separator_count}")
            print(f"Oil balls in waste/processed area (Y<=200): {waste_count}")
            print(f"Oil balls in other areas: {other_count}")
            print(f"Total oil balls: {len(self.oil_balls)}")
            
            # Check if any oil balls are actually flowing through the system
            if separator_count > 0:
                print("*** OIL BALLS ARE FLOWING TO SEPARATOR! ***")
            if waste_count > 0:
                print("*** OIL BALLS ARE REACHING WASTE/PROCESSED AREA! ***")
            
            # Check if any oil balls are near the pipe path
            pipe_near_count = 0
            for ball in self.oil_balls:
                pos = ball.body.position
                # Check if oil ball is near the pipe path (around X=70, Y=410 to Y=200)
                if abs(pos.x - 70) < 20 and pos.y < 410 and pos.y > 200:
                    pipe_near_count += 1
                    print(f"Oil ball near pipe path: {pos}")
            
            print(f"Oil balls near pipe path: {pipe_near_count}")
            print("=" * 50)
        
        # Add oil balls
        if ticks_to_next_ball <= 0 and feed_pump == 1:
            ticks_to_next_ball = 1
            self._add_oil_ball()
        
        # Decrement ticks
        ticks_to_next_ball -= 1
        
        return ticks_to_next_ball
    
    def _cleanup_objects(self):
        """Remove off-screen objects with proper coordinate handling"""
        if self.plant_type == "bottle":
            # Clean water balls - use world coordinates for bounds checking
            balls_to_remove = []
            for ball in self.water_balls:
                # Convert world position to screen coordinates for bounds check
                screen_x, screen_y = self._to_pygame(ball.body.position)
                if screen_y > self.SCREEN_HEIGHT + 50 or screen_x < -50 or screen_x > self.SCREEN_WIDTH + 50:
                    balls_to_remove.append(ball)
            
            # Remove balls without in-place mutation
            for ball in balls_to_remove:
                self.space.remove(ball, ball.body)
            self.water_balls = [ball for ball in self.water_balls if ball not in balls_to_remove]
            
            # Clean bottles - use world coordinates for bounds checking
            bottles_to_remove = []
            for bottle in self.bottles:
                # Convert world position to screen coordinates for bounds check
                screen_x, screen_y = self._to_pygame(bottle[3].position)
                if screen_x < -100 or screen_x > self.SCREEN_WIDTH + 100 or screen_y < -100 or screen_y > self.SCREEN_HEIGHT + 100:
                    bottles_to_remove.append(bottle)
                    print(f"Removing bottle at world position {bottle[3].position} (screen: {screen_x}, {screen_y})")
            
            # Remove bottles without in-place mutation
            for bottle in bottles_to_remove:
                self.space.remove(bottle[0], bottle[1], bottle[2], bottle[3])
            self.bottles = [bottle for bottle in self.bottles if bottle not in bottles_to_remove]
        else:
            # Clean oil balls
            balls_to_remove = []
            for ball in self.oil_balls:
                screen_x, screen_y = self._to_pygame(ball.body.position)
                # Debug: Print oil ball positions occasionally
                if len(self.oil_balls) > 0 and random.random() < 0.01:  # 1% chance
                    print(f"Oil ball at world pos: {ball.body.position}, screen pos: ({screen_x}, {screen_y})")

                    
                    # Track oil ball positions near valves
                    outlet_valve_pos = pymunk.Vec2d(70, 410)  # Outlet valve position
                    sep_valve_pos = pymunk.Vec2d(327, 218)    # Separator valve position
                    waste_valve_pos = pymunk.Vec2d(225, 218)  # Waste valve position
                    
                    outlet_distance = (ball.body.position - outlet_valve_pos).length
                    sep_distance = (ball.body.position - sep_valve_pos).length
                    waste_distance = (ball.body.position - waste_valve_pos).length
                    
                    if outlet_distance < 20:
                        print(f"Oil ball near outlet valve! Distance: {outlet_distance:.2f}, Valve state: {getattr(self, 'outlet_valve_open', 'Unknown')}")
                    
                    if sep_distance < 20:
                        sep_valve_state = self.modbus_bridge.get_tag_value('ACT_SEP_VALVE')
                        print(f"Oil ball near separator valve! Distance: {sep_distance:.2f}, Valve state: {sep_valve_state}")
                    
                    if waste_distance < 20:
                        waste_valve_state = self.modbus_bridge.get_tag_value('ACT_WASTE_VALVE')
                        print(f"Oil ball near waste valve! Distance: {waste_distance:.2f}, Valve state: {waste_valve_state}")
                    

                if screen_y > self.SCREEN_HEIGHT + 50 or screen_x < -50 or screen_x > self.SCREEN_WIDTH + 50:
                    balls_to_remove.append(ball)
            
            for ball in balls_to_remove:
                self.space.remove(ball, ball.body)
            self.oil_balls = [ball for ball in self.oil_balls if ball not in balls_to_remove]
    
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

        
        # Draw water balls
        for ball in self.water_balls:
            self._draw_ball(self.screen, ball, self.BLUE)
        
        # Draw bottles
        for i, bottle in enumerate(self.bottles):
            self._draw_lines(self.screen, bottle[:3], self.DODGER_BLUE)
            
            # Debug: Draw bottle position indicator
            screen_pos = self._to_pygame(bottle[3].position)
            pygame.draw.circle(self.screen, self.RED, screen_pos, 3)
            
            # Debug: Draw bottle number
            if i < 5:  # Only show first 5 bottles to avoid clutter
                text = self.font_small.render(f"B{i+1}", True, self.RED)
                self.screen.blit(text, (screen_pos[0] + 10, screen_pos[1] - 10))
            
            # Debug: Draw bottle AABB rectangle
            if self.show_debug_rectangles:
                # Calculate AABB for bottle segments
                min_x = min_y = float('inf')
                max_x = max_y = float('-inf')
                
                for segment in bottle[:3]:
                    body = segment.body
                    p1 = body.position + segment.a.rotated(body.angle)
                    p2 = body.position + segment.b.rotated(body.angle)
                    screen_p1 = self._to_pygame(p1)
                    screen_p2 = self._to_pygame(p2)
                    
                    min_x = min(min_x, screen_p1[0], screen_p2[0])
                    max_x = max(max_x, screen_p1[0], screen_p2[0])
                    min_y = min(min_y, screen_p1[1], screen_p2[1])
                    max_y = max(max_y, screen_p1[1], screen_p2[1])
                
                # Draw AABB rectangle
                if min_x != float('inf'):
                    rect = pygame.Rect(min_x - 2, min_y - 2, max_x - min_x + 4, max_y - min_y + 4)
                    pygame.draw.rect(self.screen, self.GREEN, rect, 1)
        
        # Draw base and nozzle
        self._draw_polygon(self.screen, self.actuators['base'], self.BLACK)
        self._draw_polygon(self.screen, self.actuators['nozzle'], self.DARK_GRAY)
        
        # Debug: Draw world origin axes
        if self.show_world_axes:
            # World origin (0, 0) in screen coordinates
            origin_screen = self._to_pygame(pymunk.Vec2d(0, 0))
            pygame.draw.circle(self.screen, self.RED, origin_screen, 5)
            
            # X-axis (red line)
            x_end = self._to_pygame(pymunk.Vec2d(100, 0))
            pygame.draw.line(self.screen, self.RED, origin_screen, x_end, 2)
            
            # Y-axis (green line)
            y_end = self._to_pygame(pymunk.Vec2d(0, 100))
            pygame.draw.line(self.screen, self.GREEN, origin_screen, y_end, 2)
            
            # Label axes
            x_text = self.font_small.render("X", True, self.RED)
            y_text = self.font_small.render("Y", True, self.GREEN)
            self.screen.blit(x_text, (x_end[0] + 5, x_end[1] - 10))
            self.screen.blit(y_text, (y_end[0] - 10, y_end[1] - 5))
        
        # Draw sensors
        self._draw_ball(self.screen, self.sensors['limit_switch'], self.GREEN)
        self._draw_ball(self.screen, self.sensors['level_sensor'], self.RED)
        
        # Draw status indicators
        self._draw_status_indicators()
    
    def _draw_refinery_plant(self):
        """Draw oil refinery plant - EXACT original"""
        # Draw oil balls
        for ball in self.oil_balls:
            self._draw_ball(self.screen, ball, self.BROWN)
        
        # Draw pump
        self._draw_polygon(self.screen, self.actuators['pump'], self.BLACK)
        
        # Draw oil unit lines
        self._draw_lines(self.screen, self.actuators['oil_unit'], self.GRAY)
        
        # Draw sensors
        self._draw_ball(self.screen, self.sensors['tank_level'], self.BLACK)
        
        # Draw valves as lines - only show when closed (RE-ENABLED)
        outlet_valve = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE')
        sep_valve = self.modbus_bridge.get_tag_value('ACT_SEP_VALVE')
        waste_valve = self.modbus_bridge.get_tag_value('ACT_WASTE_VALVE')
        
        # Only draw valves when they are closed (blocking flow)
        if not outlet_valve:
            self._draw_line(self.screen, self.actuators['outlet_valve'], self.RED)
        if not sep_valve:
            self._draw_line(self.screen, self.actuators['sep_valve'], self.RED)
        if not waste_valve:
            self._draw_line(self.screen, self.actuators['waste_valve'], self.RED)
        
        # Draw spill and processed sensors
        self._draw_line(self.screen, self.sensors['spill_sensor'], self.RED)
        self._draw_line(self.screen, self.sensors['processed_sensor'], self.RED)
        
        # Draw status indicators
        self._draw_status_indicators()
        
        # Draw component labels
        self._draw_refinery_labels()
    
    def _draw_status_indicators(self):
        """Draw status indicators"""
        if self.plant_type == "bottle":
            # Bottle plant status indicators
            # Run status
            run_cmd = self.modbus_bridge.get_tag_value('CMD_RUN')
            status_color = self.GREEN if run_cmd else self.RED
            pygame.draw.circle(self.screen, status_color, (self.SCREEN_WIDTH - 30, 30), 15)
            
            # Motor status
            motor_on = self.modbus_bridge.get_tag_value('ACT_MOTOR')
            motor_color = self.GREEN if motor_on else self.RED
            pygame.draw.circle(self.screen, motor_color, (self.SCREEN_WIDTH - 30, 60), 10)
            
            # Nozzle status
            nozzle_open = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
            nozzle_color = self.GREEN if nozzle_open else self.RED
            pygame.draw.circle(self.screen, nozzle_color, (self.SCREEN_WIDTH - 30, 90), 10)
        else:
            # Refinery status indicators - positioned for larger screen
            # Feed pump status
            feed_pump = self.modbus_bridge.get_tag_value('ACT_FEED_PUMP')
            pump_color = self.GREEN if feed_pump else self.RED
            pygame.draw.circle(self.screen, pump_color, (self.SCREEN_WIDTH - 50, 30), 15)
            
            # Outlet valve status
            outlet_valve = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE')
            outlet_color = self.GREEN if outlet_valve else self.RED
            pygame.draw.circle(self.screen, outlet_color, (self.SCREEN_WIDTH - 50, 60), 10)
            
            # Separator valve status
            sep_valve = self.modbus_bridge.get_tag_value('ACT_SEP_VALVE')
            sep_color = self.GREEN if sep_valve else self.RED
            pygame.draw.circle(self.screen, sep_color, (self.SCREEN_WIDTH - 50, 90), 10)
    
    def _draw_ui(self):
        """Draw UI elements"""
        # Clear UI area - smaller for refinery to show more plant
        ui_width = 250 if self.plant_type == "refinery" else 300
        pygame.draw.rect(self.screen, self.WHITE, (0, 0, ui_width, self.SCREEN_HEIGHT))
        
        # Title
        title = self.font_medium.render(f"{self.plant_type.title()} Plant", True, self.DEEP_SKY_BLUE)
        self.screen.blit(title, (10, 40))
        
        # VirtuaPlant branding
        name = self.font_big.render("VirtuaPlant", True, self.DARK_GRAY)
        self.screen.blit(name, (10, 10))
        
        # Instructions
        if self.plant_type == "bottle":
            instructions = self.font_small.render("ESC=quit, SPACE=run, N=nozzle, M=motor, TAB=add bottle, D=debug rect, A=axes", True, self.GRAY)
        else:
            if self.debug_mode:
                instructions = self.font_small.render("DEBUG: ARROWS=move, +/-=step, R=reset, C=exit debug", True, self.RED)
            else:
                instructions = self.font_small.render("ESC=quit, SPACE=pump, N=outlet, M=separator, D=debug rect, A=axes, C=camera", True, self.GRAY)
        self.screen.blit(instructions, (self.SCREEN_WIDTH - 500, 10))
        
        # Status information
        self._draw_status_text()
    
    def _draw_refinery_labels(self):
        """Draw labels for refinery components"""
        if self.plant_type != "refinery":
            return
        
        # Component labels with positions - adjusted to avoid overlap
        labels = [
            ("Feed Pump", (70, 585), self.BLUE),
            ("Oil Storage Tank", (300, 300), self.BLUE),
            ("Tank Level Sensor", (115, 535), self.BLUE),
            ("Outlet Valve", (70, 410), self.BLUE),
            ("Separator Vessel", (300, 200), self.BLUE),
            ("Separator Valve", (327, 218), self.BLUE),
            ("Waste Valve", (225, 218), self.BLUE),
            ("Oil Spill Sensor", (0, 100), self.RED),
            ("Oil Processed Sensor", (327, 180), self.RED),  # Moved up to avoid overlap
        ]
        
        for text, world_pos, color in labels:
            # Convert tuple to pymunk.Vec2d for coordinate conversion
            world_vec = pymunk.Vec2d(world_pos[0], world_pos[1])
            screen_pos = self._to_pygame(world_vec)
            # Adjust position to avoid overlapping with components
            label_x = screen_pos[0] + 20
            label_y = screen_pos[1] - 10
            
            # Only draw if label is in visible area
            if 250 < label_x < self.SCREEN_WIDTH - 100 and 0 < label_y < self.SCREEN_HEIGHT - 20:
                label_surface = self.font_small.render(text, True, color)
                self.screen.blit(label_surface, (label_x, label_y))
    
    def _draw_status_text(self):
        """Draw status text"""
        y_offset = 70
        
        if self.plant_type == "bottle":
            # Bottle plant status text
            # Run command status
            run_cmd = self.modbus_bridge.get_tag_value('CMD_RUN')
            run_color = self.GREEN if run_cmd else self.RED
            run_text = self.font_big.render(f"RUN: {'ON' if run_cmd else 'OFF'}", True, run_color)
            self.screen.blit(run_text, (10, y_offset))
            
            # Motor status
            motor_on = self.modbus_bridge.get_tag_value('ACT_MOTOR')
            motor_color = self.GREEN if motor_on else self.RED
            motor_text = self.font_medium.render(f"MOTOR: {'ON' if motor_on else 'OFF'}", True, motor_color)
            self.screen.blit(motor_text, (10, y_offset + 40))
            
            # Nozzle status
            nozzle_open = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
            nozzle_color = self.GREEN if nozzle_open else self.RED
            nozzle_text = self.font_medium.render(f"NOZZLE: {'OPEN' if nozzle_open else 'CLOSED'}", True, nozzle_color)
            self.screen.blit(nozzle_text, (10, y_offset + 70))
            
            # Bottle count
            bottle_text = self.font_medium.render(f"Bottles: {len(self.bottles)}", True, self.BLACK)
            self.screen.blit(bottle_text, (10, y_offset + 100))
            
            # Water balls count
            water_text = self.font_medium.render(f"Water drops: {len(self.water_balls)}", True, self.BLACK)
            self.screen.blit(water_text, (10, y_offset + 130))
            # Debug: Show total balls created
            total_balls = getattr(self, 'total_balls_created', 0)
            total_text = self.font_small.render(f"Total created: {total_balls}", True, self.RED)
            self.screen.blit(total_text, (10, y_offset + 160))
            
            # Debug: Show coordinate info
            if self.bottles:
                first_bottle = self.bottles[0]
                world_pos = first_bottle[3].position
                screen_pos = self._to_pygame(world_pos)
                coord_text = self.font_small.render(f"B1: world({world_pos.x:.1f},{world_pos.y:.1f}) screen({screen_pos[0]},{screen_pos[1]})", True, self.BLUE)
                self.screen.blit(coord_text, (10, y_offset + 180))
        else:
            # Refinery status text
            # Feed pump status
            feed_pump = self.modbus_bridge.get_tag_value('ACT_FEED_PUMP')
            pump_color = self.GREEN if feed_pump else self.RED
            pump_text = self.font_big.render(f"FEED PUMP: {'ON' if feed_pump else 'OFF'}", True, pump_color)
            self.screen.blit(pump_text, (10, y_offset))
            
            # Outlet valve status
            outlet_valve = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE')
            outlet_color = self.GREEN if outlet_valve else self.RED
            outlet_text = self.font_medium.render(f"OUTLET: {'OPEN' if outlet_valve else 'CLOSED'}", True, outlet_color)
            self.screen.blit(outlet_text, (10, y_offset + 40))
            
            # Separator valve status
            sep_valve = self.modbus_bridge.get_tag_value('ACT_SEP_VALVE')
            sep_color = self.GREEN if sep_valve else self.RED
            sep_text = self.font_medium.render(f"SEPARATOR: {'OPEN' if sep_valve else 'CLOSED'}", True, sep_color)
            self.screen.blit(sep_text, (10, y_offset + 70))
            
            # Oil balls count
            oil_text = self.font_medium.render(f"Oil drops: {len(self.oil_balls)}", True, self.BLACK)
            self.screen.blit(oil_text, (10, y_offset + 100))
            
            # Tank level
            tank_level = self.modbus_bridge.get_tag_value('SENSOR_TANK_LEVEL')
            tank_text = self.font_medium.render(f"Tank Level: {tank_level}", True, self.BLACK)
            self.screen.blit(tank_text, (10, y_offset + 130))
            
            # Camera position (debug info)
            if self.debug_mode:
                camera_text = self.font_small.render(f"Camera: X={self.CAMERA_X}, Y={self.CAMERA_Y}, Step={self.camera_step}", True, self.BLUE)
                self.screen.blit(camera_text, (10, y_offset + 160))
    
    def _toggle_run(self):
        """Toggle run command"""
        try:
            if self.plant_type == "bottle":
                current_run = self.modbus_bridge.get_tag_value('CMD_RUN')
                new_run = not current_run
                self.modbus_bridge.set_tag_value('CMD_RUN', new_run)
                print(f"Run command toggled: {current_run} -> {new_run}")
            else:
                # For refinery, toggle feed pump
                current_pump = self.modbus_bridge.get_tag_value('ACT_FEED_PUMP')
                new_pump = not current_pump
                self.modbus_bridge.set_tag_value('ACT_FEED_PUMP', new_pump)
                print(f"Feed pump toggled: {current_pump} -> {new_pump}")
        except Exception as e:
            print(f"Error toggling run command: {e}")
    
    def _toggle_nozzle(self):
        """Toggle nozzle valve"""
        try:
            if self.plant_type == "bottle":
                current_nozzle = self.modbus_bridge.get_tag_value('ACT_NOZZLE')
                new_nozzle = not current_nozzle
                self.modbus_bridge.set_tag_value('ACT_NOZZLE', new_nozzle)
                print(f"Nozzle toggled: {current_nozzle} -> {new_nozzle}")
            else:
                # For refinery, toggle outlet valve
                current_outlet = self.modbus_bridge.get_tag_value('ACT_OUTLET_VALVE')
                new_outlet = not current_outlet
                self.modbus_bridge.set_tag_value('ACT_OUTLET_VALVE', new_outlet)
                print(f"=== OUTLET VALVE TOGGLE ===")
                print(f"Current state: {current_outlet} -> New state: {new_outlet}")
                print(f"===========================")
                # Update collision handlers for the valve
                self._update_valve_collisions()
        except Exception as e:
            print(f"Error toggling nozzle: {e}")
    
    def _toggle_motor(self):
        """Toggle motor"""
        try:
            if self.plant_type == "bottle":
                current_motor = self.modbus_bridge.get_tag_value('ACT_MOTOR')
                new_motor = not current_motor
                self.modbus_bridge.set_tag_value('ACT_MOTOR', new_motor)
                print(f"Motor toggled: {current_motor} -> {new_motor}")
            else:
                # For refinery, toggle separator valve
                current_sep = self.modbus_bridge.get_tag_value('ACT_SEP_VALVE')
                new_sep = not current_sep
                self.modbus_bridge.set_tag_value('ACT_SEP_VALVE', new_sep)
                print(f"=== SEPARATOR VALVE TOGGLE ===")
                print(f"Current state: {current_sep} -> New state: {new_sep}")
                print(f"===========================")
                # Update collision handlers for the valve
                self._update_valve_collisions()
        except Exception as e:
            print(f"Error toggling motor: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VirtuaPlant Improved Pygame Frontend")
    parser.add_argument("plant", choices=["bottle", "refinery"], help="Plant type to visualize")
    parser.add_argument("--port", type=int, default=5020, help="Modbus port")
    
    args = parser.parse_args()
    
    frontend = ImprovedPygameFrontend(args.plant, args.port)
    frontend.start()

if __name__ == "__main__":
    main()
