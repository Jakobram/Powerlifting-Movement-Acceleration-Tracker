# Pico-Lift Tracker

## Project Overview
PicoLift is a specialized fitness tool designed to monitor The Big Three powerlifting movements: Squat, Bench Press, and Deadlift.

The system uses Cumulative Acceleration Analysis to detect the slow, heavy starts typical of a max-effort deadlift. It also features a Bi-Directional Logic Gate, allowing it to automatically recognize "Down-First" movements (Squats) and "Up-First" movements (Bench Press) without manual input.

## Device Functionality
- Bi-Directional Detection: Automatically identifies whether a movement starts with a descent (Squat/Bench) or an ascent (Deadlift).
- Motion Filtering: Uses a running sum window along with a threshold to distinguish deliberate lifting from random sensor noise or vibrations.
- State Tracking: Monitors four distinct phases of a rep: the initial drive, the pause/lockout, the return phase, and the final impact/stop.
- False-Pause Correction: A vector-gate check prevents "sticking points" or bar shakes from prematurely ending a rep recording.

## Data Reporting
The device generates a detailed performance summary for every completed repetition, saved to gym_log.txt and gym_data.csv.
### Metrics Captured:
1. Total Time: The full duration of the rep from start to finish.
2. Split Times: Individual durations for the Drive, Pause, and Return phases.
3. Drive Peak: The maximum acceleration generated during the first half of the movement.
4. Drive Brake: The force applied to decelerate and stop the weight at the midpoint/lockout.
5. Return Peak: The maximum acceleration during the second half of the movement.
6. Return Impact: The force measured when the weight comes to a complete stop or hits the floor.

## Hardware Config.
| Component | Connection |
| :--- | :--- |
| **MPU6050** | VCC/GND, 3V3 / GND |
| **MPU6050** | SDA/SCL, GP4 / GP5 |
| **Control** | Button, GP14 |
| **Onboard** | LED, Status & Calibration Indicator |

## Operation
1. Calibration: Power the device while stationary on a flat surface. The LED remains ON during calibration and turns OFF when ready.
2. Start Recording: Double-press the control button. The LED flashes 3 times to indicate the session is active.
3. End Recording: Double-press the button again. The LED provides a long pulse to confirm all data has been saved to the internal storage.
4. Data Retrieval: Connect the Pico to a PC to access the .txt logs or .csv spreadsheets.



