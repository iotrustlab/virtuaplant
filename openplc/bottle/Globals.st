// Bottle Filling Plant - Global Variables
// Modbus mapping for sensors and actuators

// Input Variables (Sensors) - %IX (Discrete Inputs)
SENSOR_LIMIT_SWITCH AT %IX2.0 : BOOL;  // Limit switch detects bottle in position
SENSOR_LEVEL_SENSOR AT %IX1.0 : BOOL;  // Level sensor detects bottle filled

// Output Variables (Actuators) - %QX (Coils)
ACT_MOTOR AT %QX3.0 : BOOL;     // Conveyor motor control
ACT_NOZZLE AT %QX4.0 : BOOL;    // Water nozzle valve control
CMD_RUN AT %QX16.0 : BOOL;      // System run command

// Internal Variables
bottle_in_position : BOOL;      // Internal state for bottle position
bottle_filled : BOOL;           // Internal state for bottle filled
system_running : BOOL;          // Internal system running state


