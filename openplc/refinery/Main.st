// Oil Refinery Plant - Main Program
// Implements BPCS + SIS with independent LSHH latch & reset

PROGRAM Main
VAR
    sis_tripped : BOOL := FALSE;   (* latched *)
END_VAR

(* --- SIS: Independent LSHH latch & manual reset --- *)
IF SIS_TANK_LSHH THEN
    sis_tripped := TRUE;
END_IF;

IF CMD_SIS_RESET AND NOT SIS_TANK_LSHH THEN
    sis_tripped := FALSE;
END_IF;

ALM_SIS_LSHH_TRIP := sis_tripped;

(* --- BPCS low-low protection (optional discrete LL) --- *)
ALM_LL_TRIP := SENSOR_TANK_LL;

(* --- Base permissives (no pump if LL or SIS trip) --- *)
IF ALM_LL_TRIP OR sis_tripped THEN
    ACT_FEED_PUMP := FALSE;
END_IF;

(* --- Overfill response --- *)
IF sis_tripped THEN
    (* Terminate inlet/receipt and divert liquid to slop *)
    ACT_INLET_VALVE  := FALSE;
    ACT_SLOP_VALVE   := TRUE;
    ACT_OUTLET_VALVE := TRUE;      (* keep outlet open to relieve tank to process/slop *)
    ACT_FLARE_VALVE  := FALSE;     (* open only if you model vapor relief *)
ELSE
    (* Normal BPCS band control on LT *)
    IF LT_TANK_LEVEL_PCT < SP_LO_PCT THEN
        ACT_INLET_VALVE  := TRUE;   (* allow inlet if low *)
        ACT_OUTLET_VALVE := TRUE;   (* keep outlet open by default *)
        IF NOT ALM_LL_TRIP THEN
            ACT_FEED_PUMP := TRUE;
        END_IF;
        ACT_SLOP_VALVE := FALSE;
        ACT_FLARE_VALVE := FALSE;
    ELSIF LT_TANK_LEVEL_PCT > SP_HI_PCT THEN
        ACT_INLET_VALVE  := FALSE;  (* stop inlet if high *)
        ACT_OUTLET_VALVE := TRUE;
        ACT_FEED_PUMP    := TRUE;   (* pump down *)
        ACT_SLOP_VALVE   := FALSE;  (* slop only on SIS trip*)
        ACT_FLARE_VALVE := FALSE;
    ELSE
        (* mid-band hold *)
        ACT_INLET_VALVE  := TRUE;
        ACT_OUTLET_VALVE := TRUE;
        IF NOT ALM_LL_TRIP THEN
            ACT_FEED_PUMP := FALSE; (* hold *)
        END_IF;
        ACT_SLOP_VALVE := FALSE;
        ACT_FLARE_VALVE := FALSE;
    END_IF;
END_IF;

(* --- Legacy compatibility - maintain existing valve controls for simulation --- *)
(* These will be controlled by the simulation based on the new SIS logic above *)
ACT_SEP_VALVE := ACT_OUTLET_VALVE;  (* separator valve follows outlet valve *)
ACT_WASTE_VALVE := ACT_SLOP_VALVE;  (* waste valve follows slop valve *)

END_PROGRAM

