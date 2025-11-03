#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
macOS Wi-Fi Auto Toggle – Lukáš Františák
-----------------------------------------
Cíl: Pokud je aktivní kabel (QNAP Thunderbolt 10G), vypnout Wi-Fi.
     Pokud kabel zmizí, Wi-Fi znovu zapnout.

Zásadní body:
- „Opravdu aktivní drát“ = ifconfig status: active + platná IPv4 (ne 169.254.*).
- TB pseudo-rozhraní (Thunderbolt 1/2/Bridge) ignorujeme.
- Lze omezit jen na tvoji QNAP kartu přes ALLOWED_WIRED_PORT_NAMES.
- Rate limiting: nepřepínat dokola, dej čas Wi-Fi naběhnout (grace period).
- Když Wi-Fi povolíme (po odpojení tb), nedáme hned idle – počkáme.

Pozn.: Běží bez externích knihoven, jen subprocess.
"""

import os
import re
import time
import ipaddress
import subprocess
from typing import Dict, Optional, Tuple, List

# ------------- KONFIGURACE (přizpůsob si podle potřeby) ----------------------

# SSID v kanceláři (jakmile je detekujeme, skript je „aktivní“):
OFFICE_SSIDS = {
    "Marketing 5.0GHz",
    # případně další kancelářské SSID
}

# Volitelný allowlist: povolené názvy HW portů, které smíme považovat za „drát“.
# Nech prázdné set(), pokud chceš autodetekovat jakýkoliv ethernet (USB LAN apod.).
ALLOWED_WIRED_PORT_NAMES = {
    "Thunderbolt Ethernet Slot 1",  # tvoje QNAP karta
}

# Porty, které NIKDY nepočítáme (TB pseudo-rozhraní)
TB_IGNORED_PORT_NAMES = {"Thunderbolt 1", "Thunderbolt 2", "Thunderbolt Bridge"}

# Jak dlouho po posledním přepnutí nebudeme přepínat znovu (rate limiting)
ACTION_COOLDOWN_SECONDS = 8

# Po zapnutí Wi-Fi (po zjištění, že drát zmizel) čekáme, než se stačí připojit
GRACE_AFTER_WIFI_ON_SECONDS = 20

# „Idle“ spánek mimo kancelář a bez drátu
IDLE_SLEEP_SECONDS = 60

# Verbózní výstup
VERBOSE = True


# ------------- NÁSTROJOVÉ FUNKCE --------------------------------------------

def run(cmd: List[str]) -> Tuple[int, str, str]:
    """Spusť příkaz a vrať (rc, stdout, stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def get_hw_ports() -> Dict[str, str]:
    """
    Vrátí mapu {HW Port Name -> device} z 'networksetup -listallhardwareports'.
    Např. {'Wi-Fi': 'en0', 'Thunderbolt Ethernet Slot 1': 'en10', ...}
    """
    rc, out, err = run(["/usr/sbin/networksetup", "-listallhardwareports"])
    ports: Dict[str, str] = {}
    if rc != 0:
        return ports

    name, dev = None, None
    for line in out.splitlines():
        if line.startswith("Hardware Port: "):
            name = line.split("Hardware Port: ", 1)[1].strip()
        elif line.startswith("Device: "):
            dev = line.split("Device: ", 1)[1].strip()
        elif line.strip() == "" and name and dev:
            ports[name] = dev
            name, dev = None, None

    if name and dev:
        ports[name] = dev

    return ports


def get_wifi_service_name() -> Optional[str]:
    """
    Zkusí najít název Wi-Fi služby pro networksetup (někdy ‚Wi-Fi‘).
    Pokud se nepodaří, vrací None a použijeme fallback přes device en0.
    """
    rc, out, err = run(["/usr/sbin/networksetup", "-listallnetworkservices"])
    if rc != 0:
        return None

    services = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith("An asterisk")]
    # Dejte přednost přesnému „Wi-Fi“
    for s in services:
        if s.lower() in ("wi-fi", "wifi"):
            return s
    # Nebo něco, co obsahuje „wi-fi“
    for s in services:
        if "wi-fi" in s.lower() or "wifi" in s.lower():
            return s
    return None


def get_wifi_device(hw_ports: Dict[str, str]) -> Optional[str]:
    """Najde device pro Wi-Fi (typicky en0)."""
    # Nejprve přes HW porty
    for name, dev in hw_ports.items():
        if name.lower() in ("wi-fi", "wifi") or "wi-fi" in name.lower() or "wifi" in name.lower():
            return dev
    # Fallback: en0 bývá Wi-Fi
    return "en0" if "en0" in hw_ports.values() or True else None


def get_current_ssid(dev: str) -> Optional[str]:
    """
    Vrátí aktuální SSID pro airport device (např. en0).
    Poznámka: `networksetup -getairportnetwork en0` funguje jen pro Wi-Fi.
    """
    rc, out, err = run(["/usr/sbin/networksetup", "-getairportnetwork", dev])
    if rc != 0:
        return None
    # Output: "Current Wi-Fi Network: <SSID>"
    m = re.search(r"Current Wi-Fi Network:\s*(.+)", out)
    return m.group(1).strip() if m else None


def wifi_set_power(service_or_dev: str, on: bool) -> bool:
    """
    Zapne/vypne Wi-Fi. Pokud máme service name (např. 'Wi-Fi'), použijeme ho.
    Když ne, použijeme device (např. 'en0').
    """
    # networksetup přijme jak název služby, tak device
    state = "on" if on else "off"
    rc, out, err = run(["/usr/sbin/networksetup", "-setairportpower", service_or_dev, state])
    if VERBOSE:
        print(f"[wifi] {service_or_dev} -> {state} (rc={rc}) ", flush=True)
    return rc == 0


def get_ipv4_addr(dev: str) -> Optional[str]:
    """Vrátí IPv4 adresu daného enX, nebo None (když není)."""
    rc, out, err = run(["/usr/sbin/ipconfig", "getifaddr", dev])
    if rc != 0 or not out:
        return None
    return out.strip()


def is_self_assigned(ip: str) -> bool:
    """True, pokud je IP v self-assigned rozsahu 169.254.0.0/16 (link-local)."""
    try:
        return ipaddress.ip_address(ip).is_link_local
    except Exception:
        return False


def if_status_active(dev: str) -> bool:
    """True, pokud ifconfig hlásí status: active."""
    rc, out, err = run(["/sbin/ifconfig", dev])
    return ("status: active" in out) if rc == 0 else False


def list_wired_candidates(hw_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Vrátí kandidáty (port_name, dev) pro drátová rozhraní:
    - ignoruje Wi-Fi a TB pseudo-porty,
    - pokud je definovaný ALLOWED_WIRED_PORT_NAMES, bere jen tyto porty,
      jinak projde všechny ne-Wi-Fi ethernety (USB LAN apod.).
    """
    candidates: List[Tuple[str, str]] = []
    for port_name, dev in hw_map.items():
        lower = port_name.lower()
        if port_name in TB_IGNORED_PORT_NAMES:
            continue
        if lower.startswith("wi-fi") or lower == "wifi":
            continue
        if ALLOWED_WIRED_PORT_NAMES and port_name not in ALLOWED_WIRED_PORT_NAMES:
            continue
        candidates.append((port_name, dev))
    return candidates


def wired_really_active(hw_map: Dict[str, str]) -> bool:
    """
    „Opravdu aktivní drát“ = ifconfig status: active + má IPv4, která není self-assigned (ne 169.254.*).
    Tím odfiltrujeme TB pseudo rozhraní i USB hub bez kabelu/DHCP.
    """
    for port_name, dev in list_wired_candidates(hw_map):
        if if_status_active(dev):
            ip = get_ipv4_addr(dev)
            if ip and not is_self_assigned(ip):
                return True
    return False


# ------------- HLAVNÍ SMYČKA ------------------------------------------------

def main():
    last_switch_ts = 0.0             # kdy jsme naposledy přepínali (rate limit)
    last_wifi_on_ts = 0.0            # kdy jsme naposledy zapnuli Wi-Fi (grace)
    last_wifi_state: Optional[bool] = None   # None/True/False (Wi-Fi je zapnutá?)
    grace_until = 0.0                # dokdy nedává smysl usínat (čekáme na připojení)

    # Zjisti HW porty + Wi-Fi identifikátory
    hw = get_hw_ports()
    if VERBOSE:
        print(f"[info] HW porty: {hw}", flush=True)

    wifi_service = get_wifi_service_name()
    wifi_dev = get_wifi_device(hw)
    if VERBOSE:
        print(f"[info] Wi-Fi service: {wifi_service if wifi_service else '(nenalezeno – fallback)'}", flush=True)
        print(f"[info] Wi-Fi device: {wifi_dev}", flush=True)

    # Helper pro zap/vyp Wi-Fi s rate limitingem a book-keeping
    def ensure_wifi(desired_on: bool):
        nonlocal last_switch_ts, last_wifi_state, last_wifi_on_ts, grace_until

        now = time.time()
        if last_wifi_state is desired_on:
            return  # nic neměníme

        # Rate limit – nepřepínat moc často
        if (now - last_switch_ts) < ACTION_COOLDOWN_SECONDS:
            if VERBOSE:
                print("[ratelimit] Přepínal jsem nedávno, čekám…", flush=True)
            return

        target = wifi_service or wifi_dev
        if not target:
            if VERBOSE:
                print("[err] Neznám Wi-Fi službu ani device – nemohu přepnout.", flush=True)
            return

        ok = wifi_set_power(target, desired_on)
        if ok:
            last_switch_ts = now
            last_wifi_state = desired_on
            if desired_on:
                last_wifi_on_ts = now
                # po zapnutí Wi-Fi necháme čas, aby naskočilo připojení
                grace_until = now + GRACE_AFTER_WIFI_ON_SECONDS
            if VERBOSE:
                print(f"[action] Wi-Fi -> {'ON' if desired_on else 'OFF'}", flush=True)
        else:
            if VERBOSE:
                print("[err] Přepnutí Wi-Fi selhalo.", flush=True)

    # První odhad stavu Wi-Fi (pokud chceme)
    # (nemusí být 100% přesný, ale stačí pro logiku – a stejně to udržíme idempotentní)
    last_wifi_state = None  # necháme rozhodovat přes ensure_wifi

    while True:
        hw = get_hw_ports()
        wired_active = wired_really_active(hw)

        # SSID – když je Wi-Fi off, networksetup vrací nic
        ssid = get_current_ssid(wifi_dev) if wifi_dev else None
        in_office = bool(ssid and ssid in OFFICE_SSIDS)

        now = time.time()
        grace = now < grace_until

        if VERBOSE:
            print(f"[gate] SSID='{ssid or '-'}' in_office={in_office} wired_active={wired_active} grace={grace}", flush=True)

        if wired_active:
            # Máme validní drát → Wi-Fi vypnout
            ensure_wifi(False)

        else:
            # Drát není → Wi-Fi zapnout (aby ses připojil i mimo kancelář)
            # (Tohle zajistí, že po vytažení TB se Wi-Fi skutečně rozsvítí.)
            ensure_wifi(True)

            # Když zrovna Wi-Fi nahazujeme, dejme jí chvilku (grace period)
            if grace:
                time.sleep(2)
                continue

            # Když nejsme v kanceláři a není drát, můžeme si schrupnout
            if not in_office:
                print(f"[idle] Mimo kancelář a bez drátu → spím {IDLE_SLEEP_SECONDS}s", flush=True)
                time.sleep(IDLE_SLEEP_SECONDS)
                continue

        # Když jsme v kanclu nebo máme drát, běž rychleji (nižší latence na reakci)
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[exit] Ukončeno uživatelem (Ctrl+C).")