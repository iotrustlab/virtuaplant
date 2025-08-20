// Oil Refinery Plant - Global Variables
// Modbus mapping for sensors and actuators with SIS (Safety Instrumented System)

VAR_GLOBAL
    (* Sensors — Discrete *)
    SIS_TANK_LSHH    AT %IX20001.0 : BOOL;  (* independent HH switch *)
    SENSOR_TANK_LL   AT %IX20002.0 : BOOL;  (* low-low switch *)
    SENSOR_SPILL_AREA AT %IX20003.0 : BOOL; (* area/leak *)

    (* Sensor — Analog *)
    LT_TANK_LEVEL_PCT AT %IW30011 : INT;   (* 0..10000 for 0..100.00% *)

    (* Commands/Actuators *)
    ACT_INLET_VALVE   AT %QX1.0 : BOOL;
    ACT_FEED_PUMP     AT %QX2.0 : BOOL;
    ACT_OUTLET_VALVE  AT %QX3.0 : BOOL;
    ACT_SLOP_VALVE    AT %QX4.0 : BOOL;
    ACT_FLARE_VALVE   AT %QX5.0 : BOOL; (* optional *)

    CMD_SIS_RESET     AT %IX20004.0 : BOOL;  (* operator reset *)

    (* Alarms/Status *)
    ALM_SIS_LSHH_TRIP AT %QX6.0 : BOOL;
    ALM_LL_TRIP       AT %QX7.0 : BOOL;

    (* Setpoints/Params *)
    SP_HI_PCT         AT %QW10 : INT := 8000;   (* 80.00% *)
    SP_LO_PCT         AT %QW11 : INT := 2000;   (* 20.00% *)

    (* Legacy compatibility - keep for now *)
    SENSOR_OIL_UPPER AT %IX9.0 : BOOL;     // Upper tank level sensor
    SENSOR_OIL_SPILL AT %IW6 : INT;        // Oil spill detection sensor (L)
    SENSOR_OIL_PROCESSED AT %IW7 : INT;    // Oil processed counter (L)
    ACT_SEP_VALVE AT %QX4.1 : BOOL;        // Separator valve control
    ACT_WASTE_VALVE AT %QX8.0 : BOOL;      // Waste valve control

    (* Internal Variables *)
    tank_level_high : BOOL;                // Internal state for high tank level
    tank_level_low : BOOL;                 // Internal state for low tank level
    spill_detected : BOOL;                 // Internal state for spill detection
    processing_active : BOOL;              // Internal state for processing
END_VAR

