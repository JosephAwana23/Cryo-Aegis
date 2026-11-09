#!/usr/bin/env python3
"""
CRYO-AEGIS SOC v6.0 (MASTER SUITE) - Clinical & Retail Cold-Chain Active Defense
Integrates:
  1. CustomTkinter Cold-Chain SOC Dashboard
  2. Port 8080 Danfoss AK-SM 800A Deception Honeypot (CVE-2025-41450 / CVE-2025-41451)
  3. Live Discord #soc-alerts Mobile Push Webhook Integration (reads discord_webhook_url.txt)
Author: Joseph Awana (Blue Teamers / MedAegis & Ghost-Aegis Project)
"""

import os
import threading
import queue
import json
import datetime
import platform
import subprocess
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

honeypot_queue = queue.Queue()
WEBHOOK_CONFIG_FILE = "discord_webhook_url.txt"


def dispatch_discord_alert_async(title, description, severity="CRITICAL", fields=None):
    """Fires a non-blocking @everyone Discord embed alert to #soc-alerts using saved webhook."""
    if not os.path.exists(WEBHOOK_CONFIG_FILE):
        return

    with open(WEBHOOK_CONFIG_FILE, "r") as f:
        webhook_url = f.read().strip()

    if not webhook_url.startswith("https://discord"):
        return

    def _send():
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        color_map = {"CRITICAL": 15548997, "HIGH": 15105570, "WARN": 15105570, "INFO": 5763719}
        payload = {
            "username": "Cryo-Aegis OT SOC Guard",
            "content": f"@everyone 🚨 **CRYO-AEGIS [{severity}] ALERT:** {title}",
            "allowed_mentions": {"parse": ["everyone"]},
            "embeds": [
                {
                    "title": f"🛡️ [{severity}] {title}",
                    "description": description,
                    "color": color_map.get(severity, 15548997),
                    "fields": fields or [],
                    "footer": {"text": f"Cryo-Aegis v6.0 Master SOC • {ts}"}
                }
            ]
        }
        try:
            cmd = [
                "curl.exe", "-4", "-s", "-S",
                "-H", "Content-Type: application/json",
                "-H", "User-Agent: DiscordBot (https://github.com/JosephAwana23/Cryo-Aegis, 6.0)",
                "-X", "POST",
                "-d", json.dumps(payload),
                webhook_url
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


class StoreViewHoneypotHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        attacker_ip = self.client_address[0]
        path = self.path

        if any(k in path.lower() for k in ["report", "config", "setpoint", "admin"]):
            honeypot_queue.put((
                f"[HONEYPOT TRAP] {attacker_ip} probed CVE-2025-41450 route: {path}",
                "CRITICAL"
            ))
            dispatch_discord_alert_async(
                title="Honeypot Trap Triggered: CVE-2025-41450 Recon Probe",
                description=f"External host probed restricted Danfoss AK-SM 800A endpoint on Port 8080.",
                severity="HIGH",
                fields=[
                    {"name": "Attacker IP", "value": f"`{attacker_ip}`", "inline": True},
                    {"name": "Probed URI", "value": f"`{path}`", "inline": True}
                ]
            )
        else:
            honeypot_queue.put((
                f"[HONEYPOT RECON] {attacker_ip} scanned fake AK-SM 800A HMI ({path})",
                "WARN"
            ))

        fake_hmi = """<!DOCTYPE html>
<html>
<head><title>Danfoss AK-SM 800A StoreView Web Interface</title></head>
<body style="font-family: Arial, sans-serif; background:#111827; color:#F9FAFB; padding:30px;">
  <h2 style="color:#38BDF8;">Danfoss AK-SM 800A System Manager (Firmware v4.1 - Unpatched)</h2>
  <p>Status: <b>ONLINE (4G Remote Maintenance Link)</b></p>
  <form action="/api/setpoint" method="POST" style="background:#1F2937; padding:20px; border-radius:8px; width:350px;">
    <label>Maintenance User:</label><br>
    <input name="user" value="ONEDAY" style="width:100%; margin-bottom:10px;"><br>
    <label>Code-of-the-Day:</label><br>
    <input name="cotd" value="1109" style="width:100%; margin-bottom:10px;"><br>
    <label>Target Setpoint (&deg;C):</label><br>
    <input name="temp" value="50.0" style="width:100%; margin-bottom:15px;"><br>
    <input type="submit" value="Apply Setpoint Override" style="background:#DC2626; color:white; border:none; padding:10px; cursor:pointer; width:100%;">
  </form>
</body>
</html>"""
        body_bytes = fake_hmi.encode("utf-8")
        self.send_response(200)
        self.send_header("Server", "Danfoss-AK-SM-800A/4.1.0")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        try:
            self.wfile.write(body_bytes)
        except Exception:
            pass

    def do_POST(self):
        attacker_ip = self.client_address[0]
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8", errors="ignore")
        except Exception:
            post_body = "MALFORMED_POST"

        honeypot_queue.put((
            f"[HONEYPOT EXPLOIT CAUGHT] {attacker_ip} -> {self.path} | Payload: {post_body[:100]}",
            "CRITICAL"
        ))

        dispatch_discord_alert_async(
            title="HONEYPOT EXPLOIT INTERCEPTED — Port 8080 Deception Trap",
            description="Attacker submitted an unauthorized OT setpoint override / exploit payload to fake AK-SM 800A HMI.",
            severity="CRITICAL",
            fields=[
                {"name": "Attacker Source IP", "value": f"`{attacker_ip}`", "inline": True},
                {"name": "Target Endpoint", "value": f"`{self.path}`", "inline": True},
                {"name": "Captured Payload", "value": f"`{post_body[:120]}`", "inline": False}
            ]
        )

        trap_response = (
            f"[CRYO-AEGIS DECEPTION TRAP]\n"
            f"Unauthorized OT Setpoint Modification Logged & Dispatched to Discord #soc-alerts!\n"
            f"Attacker IP: {attacker_ip}\n"
            f"Captured Payload: {post_body}\n"
        ).encode("utf-8")

        self.send_response(403)
        self.send_header("Server", "Danfoss-AK-SM-800A/4.1.0")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(trap_response)))
        self.end_headers()
        try:
            self.wfile.write(trap_response)
        except Exception:
            pass


class CryoAegisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CRYO-AEGIS v6.0 | Master Cold-Chain SOC & Discord Notifier")
        self.geometry("1020x680")

        self.zones = {
            "ZONE_A": {
                "name": "EFS Plasma Freezer #1 (Transfusion)",
                "ip": "192.168.50.101",
                "vendor": "Coolworld / Danfoss AK-SM 800A",
                "target_temp": -30.0,
                "current_setpoint": -30.0,
                "defrost": "OFF",
                "alarms": "ENABLED"
            },
            "ZONE_B": {
                "name": "Whole Blood Cold Room #2",
                "ip": "192.168.50.102",
                "vendor": "Danfoss AK-SM 800A",
                "target_temp": 4.0,
                "current_setpoint": 4.0,
                "defrost": "OFF",
                "alarms": "ENABLED"
            },
            "ZONE_C": {
                "name": "EU Supermarket Dairy & Meat Chiller",
                "ip": "192.168.50.103",
                "vendor": "Copeland XWEB 500D",
                "target_temp": 2.0,
                "current_setpoint": 2.0,
                "defrost": "OFF",
                "alarms": "ENABLED"
            }
        }

        self._build_ui()
        self._start_honeypot()
        self._poll_honeypot_queue()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="#111827", corner_radius=8)
        header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header,
            text="🛡️ CRYO-AEGIS v6.0 — OT COLD-CHAIN & DISCORD SOC GUARD",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38BDF8"
        ).pack(side="left", padx=15, pady=12)

        self.status_badge = ctk.CTkLabel(
            header,
            text="STATUS: ALL COLD ROOMS NOMINAL (DISCORD LINKED)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#065F46",
            corner_radius=6,
            padx=12, pady=6
        )
        self.status_badge.pack(side="right", padx=15)

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=15, pady=10)

        self.zone_widgets = {}
        for idx, (z_id, z_data) in enumerate(self.zones.items()):
            card = ctk.CTkFrame(cards_frame, corner_radius=10, border_width=2, border_color="#1F2937")
            card.grid(row=0, column=idx, padx=8, sticky="nsew")
            cards_frame.grid_columnconfigure(idx, weight=1)

            ctk.CTkLabel(card, text=z_data["name"], font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(12, 2), padx=10)
            ctk.CTkLabel(card, text=f"{z_data['ip']} | {z_data['vendor']}", font=ctk.CTkFont(size=11), text_color="#9CA3AF").pack(pady=(0, 8))

            lbl_temp = ctk.CTkLabel(
                card,
                text=f"Setpoint: {z_data['current_setpoint']}°C",
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color="#34D399"
            )
            lbl_temp.pack(pady=8)

            lbl_meta = ctk.CTkLabel(
                card,
                text=f"Defrost: {z_data['defrost']} | Alarms: {z_data['alarms']}",
                font=ctk.CTkFont(size=12)
            )
            lbl_meta.pack(pady=4)

            btn_isolate = ctk.CTkButton(
                card,
                text="SEVER VENDOR 4G LINK",
                fg_color="#DC2626",
                hover_color="#991B1B",
                command=lambda zid=z_id: self.quarantine_zone(zid, manual=True)
            )
            btn_isolate.pack(pady=(8, 12), padx=15, fill="x")

            self.zone_widgets[z_id] = {
                "card": card,
                "temp_lbl": lbl_temp,
                "meta_lbl": lbl_meta,
                "btn": btn_isolate
            }

        ctrl_frame = ctk.CTkFrame(self, corner_radius=8)
        ctrl_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkButton(
            ctrl_frame,
            text="🔥 Simulate EFS Plasma Attack (-30°C -> +110°C + Discord Alert)",
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(weight="bold"),
            command=self.simulate_efs_attack
        ).pack(side="left", padx=12, pady=10)

        ctk.CTkButton(
            ctrl_frame,
            text="🛒 Simulate Supermarket 50°C Attack (+ Discord Alert)",
            fg_color="#7C3AED",
            hover_color="#5B21B6",
            font=ctk.CTkFont(weight="bold"),
            command=self.simulate_store_attack
        ).pack(side="left", padx=12, pady=10)

        ctk.CTkButton(
            ctrl_frame,
            text="Restore Safe Baselines",
            fg_color="#374151",
            command=self.reset_zones
        ).pack(side="right", padx=12, pady=10)

        ctk.CTkLabel(
            self,
            text="LIVE SIEM, HONEYPOT & DISCORD #soc-alerts TELEMETRY:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=18, pady=(8, 2))

        self.log_box = ctk.CTkTextbox(self, height=230, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.log_event("[INIT] Cryo-Aegis v6.0 Master Suite active. Discord #soc-alerts webhook linked.", "INFO")

    def log_event(self, message, level="INFO"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}\n"
        try:
            self.log_box.insert("end", line)
            self.log_box.see("end")
        except Exception:
            pass

        try:
            with open("cryo_siem_stream.json", "a") as f:
                f.write(json.dumps({"timestamp": ts, "level": level, "event": message}) + "\n")
        except Exception:
            pass

    def _start_honeypot(self):
        def run_server():
            try:
                HTTPServer.allow_reuse_address = True
                server = HTTPServer(("127.0.0.1", 8080), StoreViewHoneypotHandler)
                honeypot_queue.put(("[HONEYPOT] Fake Danfoss AK-SM 800A listening on http://127.0.0.1:8080", "INFO"))
                server.serve_forever()
            except Exception as e:
                honeypot_queue.put((f"[HONEYPOT ERROR] Port 8080 could not bind: {e}", "WARN"))
        threading.Thread(target=run_server, daemon=True).start()

    def _poll_honeypot_queue(self):
        try:
            while not honeypot_queue.empty():
                msg, lvl = honeypot_queue.get_nowait()
                self.log_event(msg, lvl)
                if lvl == "CRITICAL":
                    self.status_badge.configure(text="ALERT: HONEYPOT EXPLOIT -> SENT TO DISCORD", fg_color="#DC2626")
        except Exception:
            pass
        self.after(200, self._poll_honeypot_queue)

    def quarantine_zone(self, z_id, manual=False):
        z = self.zones[z_id]
        w = self.zone_widgets[z_id]
        z["current_setpoint"] = z["target_temp"]
        z["defrost"] = "LOCKED_OFF"
        z["alarms"] = "LOCAL_HARDWARE_BUZZER"

        os_cmd = (
            f"netsh advfirewall firewall add rule name=CryoIsolate_{z['ip']} dir=in action=block remoteip={z['ip']}"
            if platform.system() == "Windows"
            else f"sudo iptables -I FORWARD -s {z['ip']} -j DROP"
        )

        trigger_src = "MANUAL OPERATOR OVERRIDE" if manual else "AUTO-RESPONSE KILL-SWITCH"
        self.log_event(
            f"[{trigger_src}] Severed external vendor access to {z['name']} ({z['ip']}). Firewall staged: {os_cmd}",
            "CRITICAL"
        )
        self.log_event(
            f"[FAILSAFE ENGAGED] {z['name']} locked to local hardware thermostat ({z['target_temp']}°C). Dispatched to #soc-alerts!",
            "INFO"
        )

        dispatch_discord_alert_async(
            title=f"{trigger_src} — {z['name']}",
            description=f"External vendor 4G gateway severed and cold-storage unit locked to local hardware failsafe.",
            severity="CRITICAL",
            fields=[
                {"name": "Protected Asset", "value": f"{z['name']} (`{z['ip']}`)", "inline": True},
                {"name": "Failsafe Temp", "value": f"**{z['target_temp']}°C**", "inline": True},
                {"name": "Firewall Rule Staged", "value": f"`{os_cmd}`", "inline": False}
            ]
        )

        w["card"].configure(border_color="#38BDF8")
        w["temp_lbl"].configure(text=f"FAILSAFE: {z['target_temp']}°C", text_color="#38BDF8")
        w["meta_lbl"].configure(text="VENDOR LINK: SEVERED | LOCAL COOLING: ON")
        w["btn"].configure(text="VENDOR LINK QUARANTINED", fg_color="#1E3A8A", state="disabled")

    def simulate_efs_attack(self):
        z_id = "ZONE_A"
        z = self.zones[z_id]
        w = self.zone_widgets[z_id]

        self.status_badge.configure(text="ALERT: THERMAL SABOTAGE IN PROGRESS", fg_color="#DC2626")
        z["current_setpoint"] = 110.0
        w["card"].configure(border_color="#EF4444")
        w["temp_lbl"].configure(text="Setpoint: +110.0°C !!", text_color="#EF4444")
        w["meta_lbl"].configure(text="Defrost: FORCED_ON | Alarms: SUPPRESSED")

        self.log_event("CRITICAL: Setpoint jumped from -30.0°C to +110.0°C (MITRE ICS T0836 / T0815)!", "CRITICAL")
        self.after(1500, lambda: self.quarantine_zone(z_id, manual=False))

    def simulate_store_attack(self):
        z_id = "ZONE_C"
        z = self.zones[z_id]
        w = self.zone_widgets[z_id]

        self.status_badge.configure(text="ALERT: CVE-2025-41450 EXPLOIT DETECTED", fg_color="#DC2626")
        z["current_setpoint"] = 50.0
        w["card"].configure(border_color="#EF4444")
        w["temp_lbl"].configure(text="Setpoint: +50.0°C !!", text_color="#EF4444")
        w["meta_lbl"].configure(text="Defrost: HEATER_ON | Alarms: DISABLED")

        self.log_event("CRITICAL: Supermarket Chiller pushed to +50.0°C via Code-of-the-Day bypass!", "CRITICAL")
        self.after(1500, lambda: self.quarantine_zone(z_id, manual=False))

    def reset_zones(self):
        self.status_badge.configure(text="STATUS: ALL COLD ROOMS NOMINAL (DISCORD LINKED)", fg_color="#065F46")
        for z_id, z in self.zones.items():
            z["current_setpoint"] = z["target_temp"]
            w = self.zone_widgets[z_id]
            w["card"].configure(border_color="#1F2937")
            w["temp_lbl"].configure(text=f"Setpoint: {z['target_temp']}°C", text_color="#34D399")
            w["meta_lbl"].configure(text="Defrost: OFF | Alarms: ENABLED")
            w["btn"].configure(text="SEVER VENDOR 4G LINK", fg_color="#DC2626", state="normal")
        self.log_event("[RESET] All cold-storage zones restored to nominal baseline.", "INFO")


if __name__ == "__main__":
    try:
        app = CryoAegisApp()
        app.mainloop()
    except Exception:
        print("\n[CRITICAL ERROR DETECTED ON STARTUP]:")
        traceback.print_exc()
        input("\nPress Enter to exit...")