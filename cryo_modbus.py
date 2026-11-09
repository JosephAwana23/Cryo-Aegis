#!/usr/bin/env python3
"""
CRYO-AEGIS v3.0 - Industrial Modbus/TCP & BACnet Bus Telemetry Poller
Monitors internal refrigeration holding registers to catch local OT network attacks
Author: Joseph Awana (Blue Teamers / MedAegis & Ghost-Aegis Project)
"""

import time
import json
import datetime
import sqlite3
import argparse

# Simulated Modbus Holding Register Map for Danfoss / Copeland Controllers
# Register 40001: Temperature Setpoint (Scaled by 10, e.g., -300 = -30.0°C)
# Register 40002: Defrost Relay State (0 = Off, 1 = Forced Heating/Defrost)
# Register 40003: High Alarm Suppression Flag (0 = Normal, 1 = Alarms Silenced)

class ModbusColdChainPoller:
    def __init__(self, target_ip="192.168.50.101", port=502):
        self.target_ip = target_ip
        self.port = port
        self.db_path = "cryo_forensics.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modbus_telemetry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                controller_ip TEXT,
                register_address INTEGER,
                raw_value INTEGER,
                parsed_metric TEXT,
                status TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_register_event(self, reg, raw_val, metric, status):
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO modbus_telemetry_logs (timestamp, controller_ip, register_address, raw_value, parsed_metric, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ts, self.target_ip, reg, raw_val, metric, status))
        conn.commit()
        conn.close()

    def poll_registers_simulation(self, setpoint_override=None, defrost_override=0, alarm_suppression=0):
        """
        Simulates polling Modbus/TCP holding registers directly off the physical bus.
        In production, this replaces the simulation with pymodbus.client.ModbusTcpClient.
        """
        simulated_regs = {
            40001: setpoint_override if setpoint_override is not None else -300, # -30.0°C
            40002: defrost_override,                                            # Defrost relay
            40003: alarm_suppression                                            # Alarm mute flag
        }

        print(f"\n[MODBUS POLATE] Querying {self.target_ip}:{self.port} (Modbus Unit ID: 1)...")
        time.sleep(0.5)

        # Parse Register 40001 (Setpoint)
        raw_temp = simulated_regs[40001]
        parsed_temp = raw_temp / 10.0
        
        # Parse Register 40002 (Defrost)
        defrost_state = "ACTIVE HEATING" if simulated_regs[40002] == 1 else "OFF (Cooling Nominal)"
        
        # Parse Register 40003 (Alarms)
        alarm_state = "SUPPRESSED (Denial of View)" if simulated_regs[40003] == 1 else "ACTIVE"

        print(f"    ├── Reg 40001 (Setpoint)   : {parsed_temp}°C (Raw: {raw_temp})")
        print(f"    ├── Reg 40002 (Defrost)    : {defrost_state}")
        print(f"    └── Reg 40003 (Alarm Mute) : {alarm_state}")

        # Safety Logic Check
        if parsed_temp > 5.0 or simulated_regs[40002] == 1 and simulated_regs[40003] == 1:
            print(f"    [!] CRITICAL ALERT: Unauthorized Modbus bus manipulation detected!")
            print(f"    [!] Triggering hardware fail-safe valve closure & firewall isolation...")
            self.log_register_event(40001, raw_temp, f"{parsed_temp}C", "CRITICAL_SABOTAGE")
            return False
        else:
            print(f"    [+] Status: Bus telemetry nominal. Cold-chain secure.")
            self.log_register_event(40001, raw_temp, f"{parsed_temp}C", "NOMINAL")
            return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cryo-Aegis Modbus/TCP Bus Poller")
    parser.add_argument("--simulate-sabotage", action="store_true", help="Simulate a local Modbus register injection attack (+50°C setpoint)")
    args = parser.parse_args()

    poller = ModbusColdChainPoller(target_ip="192.168.50.101")

    print("==================================================")
    print(" CRYO-AEGIS v3.0 - MODBUS/TCP HARDWARE BUS WATCHDOG")
    print("==================================================")
    
    # Baseline check (Normal Plasma Freezer at -30°C)
    poller.poll_registers_simulation(setpoint_override=-300, defrost_override=0, alarm_suppression=0)
    
    if args.simulate_sabotage:
        print("\n[!] INJECTING MALICIOUS MODBUS HOLDING REGISTER OVERRIDE...")
        # Attacker writes +500 (50.0°C) and enables defrost heater / mutes alarms directly over local network switch
        poller.poll_registers_simulation(setpoint_override=500, defrost_override=1, alarm_suppression=1)
    else:
        print("\n[*] Run with --simulate-sabotage to test the Modbus bus attack detection module.")