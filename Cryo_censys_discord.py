#!/usr/bin/env python3
"""
CRYO-AEGIS v5.2 - Censys ASM Gateway Auditor & Discord Mobile Push Notifier
Fixes:
  1. Interactive Webhook Setup (Saves your #soc-alerts URL automatically)
  2. Adds @everyone push banner so Discord Mobile buzzes your phone
  3. Uses native curl.exe -4 with rate-limit spacing so multi-alerts never time out
Author: Joseph Awana (Blue Teamers / MedAegis & Ghost-Aegis Project)
"""

import os
import time
import json
import base64
import datetime
import subprocess
import urllib.request
import urllib.error
import argparse

WEBHOOK_CONFIG_FILE = "discord_webhook_url.txt"
OT_SIGNATURES = ["danfoss", "ak-sm", "storeview", "xweb", "copeland", "dixell", "modbus"]


def get_or_prompt_webhook(cli_webhook=None, reset=False):
    """Loads saved webhook URL or prompts the user interactively in PowerShell."""
    if cli_webhook and cli_webhook.startswith("https://discord"):
        with open(WEBHOOK_CONFIG_FILE, "w") as f:
            f.write(cli_webhook.strip())
        return cli_webhook.strip()

    if not reset and os.path.exists(WEBHOOK_CONFIG_FILE):
        with open(WEBHOOK_CONFIG_FILE, "r") as f:
            saved = f.read().strip()
            if saved.startswith("https://discord"):
                return saved

    print("\n" + "=" * 70)
    print(" DISCORD #soc-alerts WEBHOOK SETUP")
    print("=" * 70)
    print(" 1. In Discord, click the Gear icon next to #soc-alerts")
    print(" 2. Go to Integrations -> Webhooks -> New Webhook -> Copy Webhook URL")
    url = input("\n[?] Paste your Discord Webhook URL here (Right-Click to paste): ").strip()

    if url.startswith("https://discord"):
        with open(WEBHOOK_CONFIG_FILE, "w") as f:
            f.write(url)
        print("[+] Saved Webhook URL to 'discord_webhook_url.txt'!")
        return url
    else:
        print("[!] That doesn't look like a valid https://discord.com/api/webhooks/1569427864992878674/KjVFKT6nLhWgvjzWqAUBGm6xlIt23rL9ByCq0BZzYnjKQNdGA5COL9rCyR2M-wENJMw4 link.")
        return None


class CryoDiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url

    def send_emergency_embed(self, title, description, severity="CRITICAL", fields=None):
        """Sends an @everyone mobile push notification + color-coded SOC embed to #soc-alerts."""
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        print(f"\n[DISCORD SOC DISPATCH] [{severity}] {title}")
        print(f"    └── {description}")

        if not self.webhook_url:
            print("    [!] No Webhook URL configured. Skipping Discord send.")
            return False

        color_map = {
            "CRITICAL": 15548997,  # Discord Red
            "HIGH": 15105570,      # Orange
            "INFO": 5763719        # Green
        }

        # Top-level 'content' with @everyone forces Discord to trigger mobile push notifications!
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
                    "footer": {
                        "text": f"Cryo-Aegis v5.2 Cold-Chain Defense • {ts}"
                    }
                }
            ]
        }

        json_str = json.dumps(payload)

        # Use native Windows curl.exe over IPv4 (-4) for instant, zero-timeout delivery
        try:
            cmd = [
                "curl.exe", "-4", "-s", "-S", "-i",
                "-H", "Content-Type: application/json",
                "-H", "User-Agent: DiscordBot (https://github.com/JosephAwana23/Cryo-Aegis, 5.2)",
                "-X", "POST",
                "-d", json_str,
                self.webhook_url
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if "204" in res.stdout or "200" in res.stdout:
                print("    [+] DELIVERED TO #soc-alerts! (Check your Discord channel & phone)")
                return True
            else:
                print(f"    [!] Discord returned error: {res.stdout[:150]} {res.stderr[:150]}")
        except Exception as e:
            print(f"    [!] Failed to dispatch webhook: {e}")
        return False


def run_simulation(notifier):
    print("\n" + "=" * 72)
    print(" CRYO-AEGIS v5.2 — DISPATCHING LIVE ALERTS TO #soc-alerts")
    print("=" * 72)

    # Alert 1: Censys Exposure Finding
    notifier.send_emergency_embed(
        title="Censys ASM Alert: Exposed Refrigeration HMI on 4G Gateway",
        description="Proactive Censys scan identified an external HTTP/Modbus interface exposed on the facility edge.",
        severity="HIGH",
        fields=[
            {"name": "Facility Asset", "value": "EFS Plasma Storage Site (Gateway #2)", "inline": True},
            {"name": "Exposed Service", "value": "Port 80/HTTP (`Danfoss-AK-SM-800A/4.1.0`)", "inline": True},
            {"name": "Vulnerability Risk", "value": "`CVE-2025-41450` (Auth Bypass) & `ONEDAY` Default Login", "inline": False}
        ]
    )

    # Brief 1.5s pause so Discord doesn't rate-limit or stall back-to-back alerts
    time.sleep(1.5)

    # Alert 2: Active Thermal Sabotage Blocked
    notifier.send_emergency_embed(
        title="THERMAL SABOTAGE BLOCKED — Cold-Chain Fail-Safe Engaged",
        description="Unauthorized remote command attempted to push **Plasma Freezer #1** from **-30.0°C to +110.0°C**.",
        severity="CRITICAL",
        fields=[
            {"name": "Target Controller", "value": "`192.168.50.101` (Zone A)", "inline": True},
            {"name": "MITRE ATT&CK ICS", "value": "`T0836` (Modify Parameter) / `T0815` (Denial of View)", "inline": True},
            {"name": "Automated Response", "value": "✅ External 4G Vendor Link Severed (`CryoIsolate_192.168.50.101`)\n✅ Hardware Thermostat Locked at **-30.0°C**", "inline": False}
        ]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cryo-Aegis v5.2 Discord Mobile Push & Censys Auditor")
    parser.add_argument("--discord-webhook", help="Paste Discord Webhook URL")
    parser.add_argument("--reset-webhook", action="store_true", help="Clear saved webhook and enter a new one")
    args = parser.parse_args()

    webhook_url = get_or_prompt_webhook(cli_webhook=args.discord_webhook, reset=args.reset_webhook)
    if webhook_url:
        bot = CryoDiscordNotifier(webhook_url=webhook_url)
        run_simulation(bot)