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
        self.db.execute('''CREATE TABLE IF NOT EXISTS screen_on_time (
            date TEXT PRIMARY KEY,
            duration_seconds INTEGER
        )''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS calibration_history (
            timestamp TEXT PRIMARY KEY
        )''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
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
        # Estimate charging cycles based on significant charge/discharge events
        # This is a simplified estimation and not as accurate as hardware-based cycle counts.
        cur = self.db.execute('''SELECT level FROM stats ORDER BY timestamp ASC''')
        levels = [row[0] for row in cur.fetchall()]

        cycles = 0
        charge_start = -1
        discharge_start = -1

        for i in range(1, len(levels)):
            if levels[i] > levels[i-1]: # Charging
                if discharge_start != -1: # Was discharging, now charging
                    # Consider a discharge cycle complete if it went down significantly
                    if levels[i-1] - levels[discharge_start] >= 80: # Discharged by at least 80%
                        cycles += 0.5 # Half cycle for discharge
                    discharge_start = -1
                if charge_start == -1: # Start of a new charge
                    charge_start = i-1
            elif levels[i] < levels[i-1]: # Discharging
                if charge_start != -1: # Was charging, now discharging
                    # Consider a charge cycle complete if it went up significantly
                    if levels[charge_start] - levels[i-1] >= 80: # Charged by at least 80%
                        cycles += 0.5 # Half cycle for charge
                    charge_start = -1
                if discharge_start == -1: # Start of a new discharge
                    discharge_start = i-1
        return int(cycles)

    def calibrate(self):
        last_calibration_cur = self.db.execute('''SELECT timestamp FROM calibration_history ORDER BY timestamp DESC LIMIT 1''')
        last_calibration = last_calibration_cur.fetchone()

        if last_calibration:
            last_calibration_date = datetime.fromisoformat(last_calibration[0])
            if (datetime.now() - last_calibration_date).days < 30:
                print(f"Last calibration was on {last_calibration_date.strftime('%Y-%m-%d')}. Next calibration due in {(30 - (datetime.now() - last_calibration_date).days)} days.")
                print("It is recommended to calibrate your battery once a month.")
                return

        print("Starting calibration cycle. This will take a long time.")
        print("Please charge your phone to 100% and then let it discharge to 0%.")
        print("Once completed, run 'python battery_doctor.py calibrate' again to record the calibration.")
        
        # Record calibration if it's being run to confirm completion
        if last_calibration and (datetime.now() - last_calibration_date).days >= 30:
            self.db.execute('''INSERT INTO calibration_history (timestamp) VALUES (?)''', (datetime.now().isoformat(),))
            self.db.commit()
            print("Calibration recorded successfully!")
        elif not last_calibration:
            # First time running calibrate, just provide instructions
            pass

    def report(self, days):
        

        print(f"Generating report for the last {days} days.")

        # Fetch data from the database
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cur = self.db.execute('''SELECT timestamp, level FROM stats 
                              WHERE timestamp BETWEEN ? AND ?
                              ORDER BY timestamp ASC''', 
                              (start_date.isoformat(), end_date.isoformat()))
        
        rows = cur.fetchall()
        
        if not rows:
            print("No data available for the selected period.")
            return

        timestamps = [datetime.fromisoformat(row[0]) for row in rows]
        levels = [row[1] for row in rows]

        # Generate the plot
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, levels, marker='o', linestyle='-')
        plt.title(f'Battery Level Over the Last {days} Days')
        plt.xlabel('Date')
        plt.ylabel('Battery Level (%)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save the plot
        report_path = f'/data/data/com.termux/files/home/Projects/Developing/Battery-Doctor/battery_report_{end_date.strftime("%Y%m%d")}.png'
        plt.savefig(report_path)
        print(f"Report saved to {report_path}")

    def daily_health_report(self):
        print("Generating daily health report...")
        # This function would generate a summary of the day's battery usage and health.
        # It could include average temperature, charging cycles, screen-on time, etc.
        # For now, it's a placeholder.
        print("Daily health report generated (placeholder).")

    def export_history(self, format='csv'):
        if format == 'csv':
            filename = '/data/data/com.termux/files/home/Projects/Developing/Battery-Doctor/battery_history.csv'
            with open(filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['timestamp', 'level', 'capacity', 'temp', 'status'])
                cur = self.db.execute('''SELECT * FROM stats ORDER BY timestamp ASC''')
                for row in cur.fetchall():
                    csv_writer.writerow(row)
            print(f"Battery history exported to {filename}")
        else:
            print("Unsupported export format.")

    def estimate_battery_age(self):
        # This is a very rough estimation based on the first recorded data point
        cur = self.db.execute('''SELECT timestamp FROM stats ORDER BY timestamp ASC LIMIT 1''')
        first_record = cur.fetchone()
        if first_record:
            first_date = datetime.fromisoformat(first_record[0])
            age_days = (datetime.now() - first_date).days
            print(f"Estimated battery age: {age_days} days.")
        else:
            print("Not enough data to estimate battery age.")

    def saver(self):
        print("Enabling emergency power saver mode.")
        print("Attempting to kill high-consumption background apps...")
        
        # Identify and kill processes with high CPU/memory usage
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # You might need to adjust these thresholds based on your device's typical usage
                if proc.info['cpu_percent'] > 5.0 or proc.info['memory_percent'] > 5.0:
                    print(f"Killing process: {proc.info['name']} (PID: {proc.info['pid']}) - CPU: {proc.info['cpu_percent']:.2f}%, Mem: {proc.info['memory_percent']:.2f}%")
                    proc.terminate() # or proc.kill() for a more forceful termination
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        print("Emergency power saver mode activated. Some apps may have been closed.")

    def schedule_monitoring(self):
        print("To schedule daily monitoring using termux-job-scheduler, run the following command:")
        print("termux-job-scheduler --persisted --period 86400 --command 'python /data/data/com.termux/files/home/Projects/Developing/Battery-Doctor/battery_doctor.py monitor'")
        print("This will run the monitor command every 24 hours (86400 seconds).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A battery optimizer for Termux.")
    parser.add_argument("command", nargs="?", default="monitor", help="The command to execute.", choices=["monitor", "calibrate", "report", "saver", "daily_report", "export", "age"])
    parser.add_argument("--days", type=int, default=30, help="The number of days to include in the report.")
    parser.add_argument("--format", type=str, default="csv", help="Export format (e.g., csv).")
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
    elif args.command == "daily_report":
        doctor.daily_health_report()
    elif args.command == "export":
        doctor.export_history(args.format)
    elif args.command == "age":
        doctor.estimate_battery_age()
