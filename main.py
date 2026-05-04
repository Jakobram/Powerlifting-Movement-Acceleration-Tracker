import machine
import time
from mpu6050 import init_mpu6050, get_mpu6050_data

# --- Configuration ---
INTENT_STRENGTH = 1.3      # Sum of recent movement to trigger start
STILLNESS_THRESHOLD = 0.6  # Sensitivity for detecting a pause/stop
PAUSE_SAMPLES = 25         # Frames of stillness required to confirm pause
TXT_LOG = "gym_log.txt"
CSV_LOG = "gym_data.csv"

# 1. Hardware Setup
# SDA=GP4 (Pin 6), SCL=GP5 (Pin 7)
i2c = machine.I2C(0, scl=machine.Pin(5), sda=machine.Pin(4))
button = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
led = machine.Pin("LED", machine.Pin.OUT)
init_mpu6050(i2c)

# --- State & Data Variables ---
is_logging = False 
state = "READY" 
direction = 0      # 1: Up-First (Curls), -1: Down-First (Squats)
accel_history = []
still_counter = 0

# Metrics
p1_peak, p2_brake = 0.0, 0.0
p3_peak, p4_impact = 0.0, 0.0
rep_start_time, top_enter_time, top_exit_time = 0, 0, 0

# --- Calibration ---
print("CALIBRATING... LEAVE DEVICE STILL")
led.on()
vals = [get_mpu6050_data(i2c)['accel']['z'] for _ in range(200)]
offset_z = sum(vals) / len(vals)
led.off()
print("CALIBRATION COMPLETE.")

# Prep CSV Header if it doesn't exist
try:
    with open(CSV_LOG, "r") as f: pass
except:
    with open(CSV_LOG, "w") as f:
        f.write("Total_s,Drive_s,Pause_s,Return_s,DrivePeak,DriveBrake,ReturnPeak,ReturnImpact\n")

while True:
    # 2. Button Check (Double-Click to Toggle)
    if button.value() == 0:
        time.sleep(0.05)
        while button.value() == 0: pass
        timeout = time.ticks_add(time.ticks_ms(), 400)
        double_press = False
        while time.ticks_diff(timeout, time.ticks_ms()) > 0:
            if button.value() == 0:
                double_press = True
                while button.value() == 0: pass
                break
        
        if double_press:
            is_logging = not is_logging
            if is_logging:
                print("\n>>> RECORDING STARTED")
                state = "READY"
                session_time = time.ticks_ms()/1000
                with open(TXT_LOG, "a") as f:
                    f.write(f"\n{'='*40}\n NEW SESSION: {session_time:.1f}s\n{'='*40}\n")
                for _ in range(3): led.on(); time.sleep(0.05); led.off(); time.sleep(0.05)
            else:
                print("\n>>> RECORDING STOPPED")
                led.on(); time.sleep(0.8); led.off()

    # 3. Movement Logic
    if is_logging:
        try:
            data = get_mpu6050_data(i2c)
            acc_z = data['accel']['z'] - offset_z
            still_counter = still_counter + 1 if abs(acc_z) < STILLNESS_THRESHOLD else 0

            # --- STAGE 1: READY (Detect Intent) ---
            if state == "READY":
                accel_history.append(acc_z)
                if len(accel_history) > 10: accel_history.pop(0)
                intent = sum(accel_history)
                
                if abs(intent) > INTENT_STRENGTH:
                    rep_start_time = time.ticks_ms()
                    direction = 1 if intent > 0 else -1
                    state = "DRIVE"
                    accel_history = [] # Reset for next use
                    p1_peak, p2_brake = 0.0, 0.0
                    print(f"MOTION DETECTED: {'UP' if direction == 1 else 'DOWN'}")

            # --- STAGE 2: DRIVE (Tracking Ascent/Descent 1) ---
            elif state == "DRIVE":
                # Track max push and max braking force
                if abs(acc_z) > abs(p1_peak): p1_peak = acc_z
                # Capture braking (opposite of initial movement)
                if (direction == 1 and acc_z < p2_brake) or (direction == -1 and acc_z > p2_brake):
                    p2_brake = acc_z
                
                if still_counter >= PAUSE_SAMPLES:
                    state = "POTENTIAL_PAUSE"
                    top_enter_time = time.ticks_ms()

            # --- STAGE 3: VECTOR GATE (Verify Flip) ---
            elif state == "POTENTIAL_PAUSE":
                # Check for "False Pause" (Keep moving in same direction)
                if (direction == 1 and acc_z > 0.6) or (direction == -1 and acc_z < -0.6):
                    state = "DRIVE"
                # Real Flip (Opposite direction detected)
                elif (direction == 1 and acc_z < -0.6) or (direction == -1 and acc_z > 0.6):
                    state = "RETURN"
                    top_exit_time = time.ticks_ms()
                    p3_peak, p4_impact = 0.0, 0.0

            # --- STAGE 4: RETURN (Tracking Ascent/Descent 2) ---
            elif state == "RETURN":
                if abs(acc_z) > abs(p3_peak): p3_peak = acc_z
                # Capture impact/stop force
                if (direction == 1 and acc_z > p4_impact) or (direction == -1 and acc_z < p4_impact):
                    p4_impact = acc_z
                
                if still_counter >= PAUSE_SAMPLES:
                    end_time = time.ticks_ms()
                    
                    # Math Calculations
                    up_dur = time.ticks_diff(top_enter_time, rep_start_time) / 1000.0
                    pause_dur = time.ticks_diff(top_exit_time, top_enter_time) / 1000.0
                    dn_dur = time.ticks_diff(end_time, top_exit_time) / 1000.0
                    ttl_dur = time.ticks_diff(end_time, rep_start_time) / 1000.0
                    
                    # Log Formatting
                    report = (
                        "----------------------------------------\n"
                        f"REP SUMMARY | Total Time: {ttl_dur:.2f}s\n"
                        f"Split: Drive: {up_dur:.2f}s | PAUSE: {pause_dur:.2f}s | Return: {dn_dur:.2f}s\n"
                        f"Drive Peak: {p1_peak:+.1f} | Drive Brake: {p2_brake:+.1f}\n"
                        f"Return Peak: {p3_peak:+.1f} | Return Impact: {p4_impact:+.1f}\n"
                        "----------------------------------------\n"
                    )
                    
                    # Save and Print
                    with open(TXT_LOG, "a") as f: f.write(report)
                    with open(CSV_LOG, "a") as f: 
                        f.write(f"{ttl_dur:.2f},{up_dur:.2f},{pause_dur:.2f},{dn_dur:.2f},{p1_peak:.2f},{p2_brake:.2f},{p3_peak:.2f},{p4_impact:.2f}\n")
                    
                    print(report)
                    state = "READY"

        except: pass
        time.sleep(0.02) 
    else:
        time.sleep(0.1)
