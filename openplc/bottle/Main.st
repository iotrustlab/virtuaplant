// Bottle Filling Plant - Main Program
// Implements bottle filling control logic

PROGRAM Main
VAR
    // Internal state variables
    start_latch : BOOL := FALSE;
    motor_running : BOOL := FALSE;
    nozzle_open : BOOL := FALSE;
    bottle_filling : BOOL := FALSE;
    
    // Timer for filling process
    fill_timer : TON;
    
    // Alarm conditions
    high_level_alarm : BOOL := FALSE;
    low_level_alarm : BOOL := FALSE;
    
END_VAR

// Main control logic
// Start latch logic - system starts when CMD_RUN is activated
IF CMD_RUN AND NOT start_latch THEN
    start_latch := TRUE;
    system_running := TRUE;
END_IF

// Stop system when CMD_RUN is deactivated
IF NOT CMD_RUN THEN
    start_latch := FALSE;
    system_running := FALSE;
    motor_running := FALSE;
    nozzle_open := FALSE;
    bottle_filling := FALSE;
END_IF

// Only run when system is started
IF system_running THEN
    
    // Update internal states from sensors
    bottle_in_position := SENSOR_LIMIT_SWITCH;
    bottle_filled := SENSOR_LEVEL_SENSOR;
    
    // Motor control logic
    // Motor stops when bottle is in position (limit switch activated)
    IF bottle_in_position THEN
        motor_running := FALSE;
    END_IF
    
    // Motor starts when bottle is filled (level sensor activated) or no bottle in position
    IF bottle_filled OR NOT bottle_in_position THEN
        motor_running := TRUE;
    END_IF
    
    // Nozzle control logic
    // Open nozzle when bottle is in position and not filled
    IF bottle_in_position AND NOT bottle_filled THEN
        nozzle_open := TRUE;
        bottle_filling := TRUE;
    ELSE
        nozzle_open := FALSE;
        bottle_filling := FALSE;
    END_IF
    
    // Fill timer logic
    fill_timer(IN := bottle_filling, PT := T#5S);
    
    // Close nozzle after fill timer expires
    IF fill_timer.Q THEN
        nozzle_open := FALSE;
        bottle_filling := FALSE;
    END_IF
    
    // Alarm logic
    // High level alarm when bottle is overfilled
    IF bottle_filled AND bottle_in_position AND nozzle_open THEN
        high_level_alarm := TRUE;
    ELSE
        high_level_alarm := FALSE;
    END_IF
    
    // Low level alarm when no bottle detected but system running
    IF system_running AND NOT bottle_in_position AND NOT bottle_filled THEN
        low_level_alarm := TRUE;
    ELSE
        low_level_alarm := FALSE;
    END_IF
    
ELSE
    // System not running - reset all outputs
    motor_running := FALSE;
    nozzle_open := FALSE;
    bottle_filling := FALSE;
    high_level_alarm := FALSE;
    low_level_alarm := FALSE;
END_IF

// Update physical outputs
ACT_MOTOR := motor_running;
ACT_NOZZLE := nozzle_open;

END_PROGRAM


