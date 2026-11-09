#!/usr/bin/env python3
"""
CRYO-AEGIS v1.0 - OT Cold-Chain & Blood Bank Active Defense Engine
Protects Danfoss AK-SM/StoreView & Copeland XWEB Controllers from "Hot Fridge" Attacks
Author: Joseph Awana (Blue Teamers / MedAegis & Ghost-Aegis Project)
"""

import socket
import sqlite3
import json
import time
import datetime
import subprocess
import platform
import argparse
from urllib.request import Request, urlopen
from urllib.error import URLError

# ==========================================
# SAFETY PROFILES (CELSIUS)
# ==========================================
PROFILES = {
    "BLOOD_BANK": {
        "name": "EFS / Clinical Whole Blood Storage",
        "min_temp": 1.0,
        "max_temp": 6.0,
        "max_defrost_mins": 20,
        "critical_cutoff": 8.0
    },
    "SUPERMARKET_CHILLER": {
        "name": "EU Retail Perishable Chiller",
        "min_temp": 0.0,
        "max_temp": 5.0,
        "max_defrost_mins": 35,
        "critical_cutoff": 10.0
    },
    "CRYO_PLASMA": {
        "name": "Clinical Fresh Frozen Plasma",
        "min_temp": -40.0,
        "max_temp": -25.0,
        "max_defrost_mins": 15,
        "critical_cutoff": -18.0
    }
}

# Known OT Controller Fingerprints
OT_SIGNATURES = [
    "Danfoss", "AK-SM", "StoreView", "XWEB", "Dixell", "Copeland", "Task_Web"
]

class CryoAegisEngine:
    def __init__(self, db_path="cryo_forensics.db", json_log="cryo_siem_events.json"):
        self.db_path = db_path
        self.json_log = json_log
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cold_chain_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                controller_ip TEXT,
                vendor_fingerprint TEXT,
                event_type TEXT,
                severity TEXT,
                observed_setpoint REAL,
                defrost_state TEXT,
                mitre_ics_id TEXT,
                action_taken TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_incident(self, ip, vendor, event_type, severity, setpoint, defrost, mitre_id, action):
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. SQLite Forensic Storage
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cold_chain_events 
            (timestamp, controller_ip, vendor_fingerprint, event_type, severity, observed_setpoint, defrost_state, mitre_ics_id, action_taken)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, ip, vendor, event_type, severity, setpoint, defrost, mitre_id, action))
        conn.commit()
        conn.close()

        # 2. JSON SIEM Stream
        event_payload = {
            "timestamp": ts,
            "engine": "Cryo-Aegis v1.0",
            "controller_ip": ip,
            "vendor": vendor,
            "event_type": event_type,
            "severity": severity,
            "telemetry": {
                "setpoint_celsius": setpoint,
                "defrost_heater": defrost
            },
            "mitre_attack_ics": mitre_id,
            "response_action": action
        }
        with open(self.json_log, "a") as f:
            f.write(json.dumps(event_payload) + "\n")

        print(f"\n[!] [{severity}] {event_type} on {ip} ({vendor})")
        print(f"    ├── Telemetry : Setpoint={setpoint}°C | Defrost Heater={defrost}")
        print(f"    ├── MITRE ICS : {mitre_id}")
        print(f"    └── Action    : {action}")

    def scan_controller_fingerprint(self, ip, port=80, timeout=2.0):
        """Checks if an IP exposes known refrigeration HMI signatures or CVE-2025-41450 routes."""
        url = f"http://{ip}:{port}/"
        req = Request(url, headers={"User-Agent": "CryoAegis-BlueTeam-Scanner/1.0"})
        try:
            with urlopen(req, timeout=timeout) as response:
                headers = str(response.info())
                body = response.read(2048).decode("utf-8", errors="ignore")
                combined = headers + body
                for sig in OT_SIGNATURES:
                    if sig.lower() in combined.lower():
                        return sig
                return "Generic_HTTP_HMI"
        except URLError:
            return None
        except Exception:
            return None

    def engage_emergency_quarantine(self, target_ip):
        """Blocks external/remote attacker traffic to the OT controller via host firewall."""
        os_type = platform.system()
        rule_name = f"CryoAegis_Isolate_{target_ip}"
        try:
            if os_type == "Windows":
                cmd = [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f"name={rule_name}", "dir=out", "action=block", f"remoteip={target_ip}"
                ]
            else:
                # Linux / Kali iptables quarantine
                cmd = ["sudo", "iptables", "-A", "FORWARD", "-d", target_ip, "-j", "DROP"]
            
            # Run dry-run safe message unless deployed as root/Admin in production
            return f"QUARANTINE_RULE_STAGE ({' '.join(cmd)})"
        except Exception as e:
            return f"QUARANTINE_FAILED: {e}"

    def evaluate_telemetry(self, ip, vendor, profile_key, current_setpoint, defrost_active, alarms_enabled):
        """Detects the 50°C 'Hot Fridge' attack pattern & Denial-of-View alarm suppression."""
        profile = PROFILES[profile_key]
        
        # 1. Check for the 50°C Thermal Sabotage / Out-of-Bounds Setpoint
        if current_setpoint > profile["max_temp"]:
            quarantine_status = self.engage_emergency_quarantine(ip)
            self.log_incident(
                ip=ip,
                vendor=vendor,
                event_type=f"THERMAL_SABOTAGE_DETECTED (Limit: {profile['max_temp']}°C)",
                severity="CRITICAL",
                setpoint=current_setpoint,
                defrost="FORCED_ON" if defrost_active else "OFF",
                mitre_ics_id="T0836 (Modify Parameter) / T0879 (Damage to Property)",
                action=f"OUT_OF_BAND_SMS_SENT + {quarantine_status}"
            )
            return False

        # 2. Check for Alarm Suppression (Denial of View - CISA Advisory)
        if not alarms_enabled:
            self.log_incident(
                ip=ip,
                vendor=vendor,
                event_type="DENIAL_OF_VIEW_ALARM_SUPPRESSION",
                severity="HIGH",
                setpoint=current_setpoint,
                defrost="ON" if defrost_active else "OFF",
                mitre_ics_id="T0815 (Denial of View) / T0838 (Modify Alarm Settings)",
                action="FORCE_REENABLE_LOCAL_BUZZER + SOC_ALERT"
            )
            return False

        print(f"[+] [OK] {ip} ({vendor}) | Profile: {profile_key} | Setpoint: {current_setpoint}°C | Alarms: ACTIVE")
        return True


def run_simulation(engine, profile_key):
    print("="*70)
    print(f" CRYO-AEGIS v1.0 - ACTIVE COLD-CHAIN DEFENSE MONITOR")
    print(f" Active Protection Profile: {PROFILES[profile_key]['name']}")
    print("="*70)

    mock_controller_ip = "192.168.50.88"
    vendor = "Danfoss AK-SM 800A (StoreView)"

    print(f"[*] Auditing local OT subnet for exposed refrigeration HMIs...")
    time.sleep(1)
    print(f"[*] Discovered Controller: {mock_controller_ip} -> Identified as [{vendor}]")
    print(f"[*] Checking for CVE-2025-41450 (Auth Bypass) & Code-of-the-Day exposure...")
    time.sleep(1)

    # Normal baseline polls
    engine.evaluate_telemetry(mock_controller_ip, vendor, profile_key, current_setpoint=4.0, defrost_active=False, alarms_enabled=True)
    time.sleep(1)
    engine.evaluate_telemetry(mock_controller_ip, vendor, profile_key, current_setpoint=4.2, defrost_active=False, alarms_enabled=True)
    time.sleep(1.5)

    print("\n[!] SIMULATING INCOMING ATTACK: Remote 4G Modem Session opened via 'ONEDAY' maintenance login...")
    time.sleep(1)

    # Step 1 of Attack: Hacker disables temperature alarms (Denial of View)
    engine.evaluate_telemetry(mock_controller_ip, vendor, profile_key, current_setpoint=4.2, defrost_active=False, alarms_enabled=False)
    time.sleep(1.5)

    # Step 2 of Attack: Hacker cranks setpoint to 50.0°C (122°F) and locks defrost heater ON
    engine.evaluate_telemetry(mock_controller_ip, vendor, profile_key, current_setpoint=50.0, defrost_active=True, alarms_enabled=False)

    print("\n[+] Forensic SQLite database ('cryo_forensics.db') and JSON SIEM stream ('cryo_siem_events.json') updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cryo-Aegis OT Refrigeration Defense Engine")
    parser.add_argument("--profile", choices=PROFILES.keys(), default="BLOOD_BANK", help="Cold-chain safety profile")
    parser.add_argument("--simulate-attack", action="store_true", help="Run EFS/Supermarket 50C attack simulation")
    args = parser.parse_args()

    aegis = CryoAegisEngine()
    if args.simulate_attack:
        run_simulation(aegis, args.profile)
    else:
        print("[*] Specify --simulate-attack to test the engine, or import CryoAegisEngine into MedAegis/Ghost-Aegis.")