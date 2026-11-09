# 🛡️ CRYO-AEGIS v6.0 — OT Cold-Chain & Blood Bank Active Defense Suite

**Author:** Homero "Joseph Awana"Antillon (`JosephAwana23`) — Blue Teamer Cybersecurity Student 
**Ecosystem Integration:** MedAegis Clinical XDR & Ghost-Aegis Active Defense  
**Target Environment:** Hospital Blood Banks (Plasma/Whole Blood), Pharmaceutical Cold Storage, & Retail Supermarket Refrigeration (OT/ICS)  
**Primary Threat Coverage:** `CVE-2025-41450`, `CVE-2025-41451`, `CVE-2025-41452`, & `ONEDAY` / Code-of-the-Day Credential Abuse  

---

## 🚨 Executive Threat Overview

Across Europe and North America, threat actors have targeted exposed Operational Technology (OT) refrigeration controllers—specifically **Danfoss AK-SM 800A (StoreView)** and **Copeland/Dixell XWEB** systems—deployed across hundreds of supermarkets, military commissaries, and clinical transfusion centers such as the **Établissement Français du Sang (EFS)**.

Because third-party HVAC contractors frequently attach standalone 4G cellular modems directly to refrigeration Human-Machine Interfaces (HMIs) for remote maintenance, attackers bypass corporate firewalls entirely. Once connected, adversaries exploit authentication bypasses or predictable daily maintenance logins (`ONEDAY` / Code-of-the-Day) to:
1. **Trigger Thermal Sabotage (`MITRE ICS T0836`):** Force supermarket chillers into continuous **+50.0°C (122°F)** defrost heating cycles, or push **-30.0°C** clinical plasma freezers toward **+110.0°C**.
2. **Execute Denial of View (`MITRE ICS T0815` / `T0838`):** Disable built-in controller temperature alarms and email alerts so local staff remain unaware until critical medical supplies or food inventories are destroyed.

**Cryo-Aegis v6.0** provides a zero-cost, open-source independent monitoring, deception, and automated quarantine engine that severs compromised vendor links and locks cold-storage units to local hardware failsafes before thermal thresholds are breached.

---

## 🏗️ System Architecture

```text
                        [ EXTERNAL 4G / WAN GATEWAY ]
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         ▼                                                         ▼
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│  PORT 8080 DECEPTION HONEYPOT   │               │   PRODUCTION OT CONTROLLERS     │
│  Fake Danfoss AK-SM 800A HMI    │               │   • Zone A: EFS Plasma (-30°C)  │
│  Traps CVE-2025-41450 & POST    │               │   • Zone B: Whole Blood (+4°C)  │
│  Setpoint Sabotage Payloads     │               │   • Zone C: Retail Chiller(+2°C)│
└────────────────┬────────────────┘               └────────────────┬────────────────┘
                 │                                                 │
                 │            ┌───────────────────────┐            │ Modbus/TCP (Port 502)
                 └───────────►│   CRYO-AEGIS v6.0     │◄───────────┘ Holding Regs 40001-40003
                              │   MASTER SOC ENGINE   │
                              └───────────┬───────────┘
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
┌───────────────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
│  OS FIREWALL ISOLATE  │     │  LOCAL SIEM & SQLITE  │     │  DISCORD #soc-alerts  │
│  netsh / iptables     │     │  cryo_forensics.db &  │     │  @everyone Mobile     │
│  Severs 4G Vendor Link│     │  cryo_siem_stream.json│     │  Push Webhook Embeds  │
└───────────────────────┘     └───────────────────────┘     └───────────────────────┘