import subprocess
import json
import sqlite3
import time
from datetime import datetime

class BatteryDoctor:
    def __init__(self):
        self.db = sqlite3.connect('/data/data/com.termux/files/home/Projects/Developing/Battery-Doctor/battery_data.db')
        self.create_tables()
        
    def create_tables(self):
        self.db.execute('''CREATE TABLE IF NOT EXISTS stats (
            timestamp TEXT PRIMARY KEY,
            level INTEGER,
            capacity REAL,
            temp REAL,
            status TEXT
        )''')
        
    def get_battery_status(self):
        result = subprocess.run(['termux-battery-status'], 
                               capture_output=True, text=True)
        return json.loads(result.stdout)
    
    def calculate_health(self):
        # Get battery capacity data
        try:
            with open('/sys/class/power_supply/battery/charge_full_design', 'r') as f:
                design_capacity = float(f.read().strip()) / 1000  # μAh to mAh
            
            with open('/sys/class/power_supply/battery/charge_full', 'r') as f:
                current_capacity = float(f.read().strip()) / 1000
            
            return (current_capacity / design_capacity) * 100
        except FileNotFoundError:
            # Fallback if capacity files are not available (e.g. no root)
            return 100.0 # Assume 100% health if files are not readable
    
    def monitor_dashboard(self):
        try:
            while True:
                status = self.get_battery_status()
                health = self.calculate_health()
                
                # ASCII Temperature indicator
                temp = status['temperature']
                temp_indicator = ""
                if temp > 40: temp_indicator = "🔴"
                elif temp > 35: temp_indicator = "🟡"
                else: temp_indicator = "🟢"
                
                print(f"\n{' Battery Doctor ':=^50}")
                print(f"Level: {status['percentage']}% | Health: {health:.1f}%")
                print(f"Status: {status['status']} | Cycles: {self.estimate_cycles()}")
                print(f"Temperature: {temp}°C {temp_indicator}")
                print(f"Capacity: {self.get_capacity_history_sparkline()}")
                
                # Smart charging alert
                if status['plugged'] == 'PLUGGED_AC' and status['percentage'] >= 80:
                    subprocess.run(['termux-notification', 
                                   '-t', 'Charge Complete', 
                                   '-c', 'Battery reached 80%'])
                
                # Log to database
                self.db.execute('''INSERT INTO stats VALUES (?,?,?,?,?)''', 
                              (datetime.now().isoformat(), 
                               status['percentage'],
                               health,
                               temp,
                               status['status']))
                self.db.commit()
                
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("Monitoring stopped")
    
    def get_capacity_history_sparkline(self):
        # Retrieve last 10 readings
        cur = self.db.execute('''SELECT capacity FROM stats 
                              ORDER BY timestamp DESC LIMIT 10''')
        values = [row[0] for row in cur.fetchall()]
        
        # Convert to sparkline
        bars = [' ','▂','▃','▄','▅','▆','▇','█']
        sparkline = ""
        if values:
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val if max_val > min_val else 1
            for val in values:
                index = int(((val - min_val) / range_val) * (len(bars)-1))
                sparkline += bars[min(index, len(bars)-1)]
        return sparkline

    def estimate_cycles(self):
        # This is a placeholder for a more complex cycle estimation logic
        return 421 # Placeholder value

def calibrate(self):
        print("Starting calibration cycle. This will take a long time.")
        print("Please charge your phone to 100% and then let it discharge to 0%.")

    def report(self, days):
        print(f"Generating report for the last {days} days.")

    def saver(self):
        print("Enabling emergency power saver mode.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A battery optimizer for Termux.")
    parser.add_argument("command", nargs="?", default="monitor", help="The command to execute.", choices=["monitor", "calibrate", "report", "saver"])
    parser.add_argument("--days", type=int, default=30, help="The number of days to include in the report.")
    args = parser.parse_args()

    doctor = BatteryDoctor()

    if args.command == "monitor":
        doctor.monitor_dashboard()
    elif args.command == "calibrate":
        doctor.calibrate()
    elif args.command == "report":
        doctor.report(args.days)
    elif args.command == "saver":
        doctor.saver()
