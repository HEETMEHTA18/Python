# arp_watch.py
# Detects suspicious ARP changes that could indicate ARP spoofing / MITM.
# Usage:
#   python arp_watch.py --gateway 192.168.1.1 --interval 5 --log arp_watch.log
#
# Notes:
# - Works without scapy; if scapy is installed, uses it for more reliable ARP queries.
# - Monitors ONLY and never injects packets.
# - Run with regular user privileges (reading ARP table is enough).
# - Cross-platform best effort: uses OS commands to read ARP cache if scapy isn't available.

import argparse
import platform
import subprocess
import sys
import time
from datetime import datetime

try:
    from scapy.all import ARP, Ether, srp, conf  # optional
    SCAPY_AVAILABLE = True
except Exception:
    SCAPY_AVAILABLE = False

def log(msg, logfile=None):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")

def normalize_mac(mac):
    if not mac:
        return None
    m = mac.replace("-", ":").lower()
    # zero-pad single-digit hex if needed
    parts = [p.zfill(2) for p in m.split(":")]
    return ":".join(parts)

def get_mac_from_arp_table(ip):
    system = platform.system().lower()
    try:
        if system == "windows":
            # route print doesn't show ARP; use 'arp -a'
            out = subprocess.check_output(["arp", "-a"], text=True, errors="ignore")
            # Lines look like: "  192.168.1.1           1c-1b-0d-xx-xx-xx     dynamic"
            for line in out.splitlines():
                if ip in line:
                    tokens = line.split()
                    if len(tokens) >= 3 and tokens[0] == ip:
                        return normalize_mac(tokens[1])
        elif system in ("linux", "darwin"):
            # Try 'ip neigh' first (Linux), fallback to 'arp -n'
            try:
                out = subprocess.check_output(["ip", "neigh", "show", ip], text=True, errors="ignore")
                # Example: "192.168.1.1 dev wlan0 lladdr 1c:1b:0d:xx:xx:xx REACHABLE"
                for tok in out.split():
                    if tok.count(":") == 5:  # naive MAC check
                        return normalize_mac(tok)
            except Exception:
                pass
            try:
                out = subprocess.check_output(["arp", "-n", ip], text=True, errors="ignore")
                # Example: "? (192.168.1.1) at 1c:1b:0d:xx:xx:xx [ether] on wlan0"
                for part in out.replace("(", " ").replace(")", " ").replace("@", " ").split():
                    if part.count(":") == 5:
                        return normalize_mac(part)
            except Exception:
                pass
    except Exception:
        return None
    return None

def get_mac_scapy(ip, timeout=2):
    if not SCAPY_AVAILABLE:
        return None
    try:
        conf.verb = 0
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip)
        ans, _ = srp(pkt, timeout=timeout, retry=1)
        for _, r in ans:
            return normalize_mac(r[Ether].src)
    except Exception:
        return None
    return None

def get_gateway_mac(ip):
    # Prefer scapy active query; fallback to ARP cache
    mac = get_mac_scapy(ip)
    if mac:
        return mac
    return get_mac_from_arp_table(ip)

def detect_default_gateway():
    system = platform.system().lower()
    try:
        if system == "windows":
            cmd = ["powershell", "-NoProfile", "-Command",
                   "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | Select-Object -First 1).IPv4DefaultGateway.NextHop"]
            out = subprocess.check_output(cmd, text=True, errors="ignore").strip()
            return out or None
        elif system == "linux":
            out = subprocess.check_output(["/bin/sh", "-c", "ip route | awk '/^default/ {print $3; exit}'"], text=True, errors="ignore").strip()
            return out or None
        elif system == "darwin":
            out = subprocess.check_output(["/usr/sbin/route", "-n", "get", "default"], text=True, errors="ignore")
            for line in out.splitlines():
                if line.strip().startswith("gateway:"):
                    return line.split()[1].strip()
    except Exception:
        return None
    return None

def main():
    parser = argparse.ArgumentParser(description="Monitor gateway MAC to detect ARP spoofing attempts.")
    parser.add_argument("--gateway", help="Gateway/router IPv4 address, e.g., 192.168.1.1")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between checks (default: 5)")
    parser.add_argument("--expect", help="(Optional) Expected gateway MAC; alert immediately if different")
    parser.add_argument("--log", dest="logfile", help="(Optional) Path to log file")
    parser.add_argument("--once", action="store_true", help="Check once and exit")
    parser.add_argument("--auto-detect", action="store_true", help="If provided gateway is unreachable, try system default gateway")
    args = parser.parse_args()

    gateway_ip = args.gateway
    if not gateway_ip and args.auto_detect:
        gateway_ip = detect_default_gateway()
        if gateway_ip:
            log(f"Auto-detected gateway: {gateway_ip}", args.logfile)

    if not gateway_ip:
        parser.error("No gateway specified and auto-detect not enabled or failed.")

    expected = normalize_mac(args.expect) if args.expect else None
    baseline = None

    # Initial read
    mac = get_gateway_mac(gateway_ip)
    if not mac and args.auto_detect:
        # try detecting system default gateway and retry once
        gw2 = detect_default_gateway()
        if gw2 and gw2 != gateway_ip:
            log(f"Retrying with detected gateway {gw2}", args.logfile)
            gateway_ip = gw2
            mac = get_gateway_mac(gateway_ip)

    if not mac:
        log(f"Could not resolve MAC for gateway {gateway_ip}. Is the IP correct and reachable?", args.logfile)
        sys.exit(1)

    baseline = mac
    log(f"Initial gateway MAC for {gateway_ip}: {baseline}", args.logfile)

    # If user provided expected MAC, verify immediately
    if expected and baseline != expected:
        log(f"ALERT: Gateway MAC {baseline} != expected {expected}. Possible ARP spoofing!", args.logfile)

    if args.once:
        sys.exit(0)

    while True:
        time.sleep(args.interval)
        current = get_gateway_mac(gateway_ip)
        if not current:
            log(f"Warning: Could not read current MAC for {gateway_ip}. Network hiccup?", args.logfile)
            continue

        if expected:
            if current != expected:
                log(f"ALERT: Gateway MAC changed to {current}, expected {expected}. Possible MITM!", args.logfile)
        else:
            if current != baseline:
                log(f"ALERT: Gateway MAC changed! was {baseline}, now {current}. Possible ARP spoofing.", args.logfile)
                # Optional: update baseline only if you know the change is legitimate
                # baseline = current

def _cli():
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")

if __name__ == "__main__":
    _cli()
