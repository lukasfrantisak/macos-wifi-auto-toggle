#!/usr/bin/env python3
# ==============================================
# MACOS AUTOMATICKÝ PŘEPÍNAČ WIFI A 10G ETHERNETU
# ==============================================
#
# Co dělá:
# ----------
# - Pokud je aktivní jakékoliv "drátové" rozhraní (např. Thunderbolt 10G karta),
#   skript vypne Wi-Fi, aby se používalo to rychlejší spojení.
# - Pokud se drátové připojení odpojí, skript Wi-Fi zase zapne.
# - Pokud jsi připojený k určité kancelářské Wi-Fi (např. "Marketing 5.0GHz"),
#   skript zůstane aktivní i bez připojené karty (aby mohl reagovat, když ji zapojíš).
# - Mimo kancelář (jiné Wi-Fi) usíná – tzv. idle režim, aby šetřil zdroje.
#
# Klíčové vlastnosti:
# --------------------
# ✅ Funguje pro jakékoliv Thunderbolt / Ethernet adaptéry, ne jen konkrétní model QNAP.
# ✅ Automaticky najde rozhraní – nepotřebuješ znát jejich názvy.
# ✅ Má "grace period" (okno po zapnutí Wi-Fi), kdy čeká, než se Wi-Fi připojí.
# ✅ Nezahltí CPU (polluje každé 3 sekundy).
# ✅ Vše funguje i při běhu jako LaunchDaemon.
#
# ==============================================

import subprocess
import time
import sys
from typing import Dict, Optional, Tuple, List

# ====== KONFIGURAČNÍ ČÁST ======

# Název kancelářské Wi-Fi sítě, kterou skript pozná a při níž zůstává aktivní
OFFICE_SSIDS = ["Marketing 5.0GHz"]

# Interval, jak často skript kontroluje stav rozhraní (v sekundách)
POLL_INTERVAL_SECONDS = 3

# Jak dlouho má spát (neprovádět nic), pokud jsi mimo kancelář i bez připojené karty
IDLE_SLEEP_SECONDS = 60

# Čas, po který musí být stav sítě stabilní, než skript zareaguje (ochrana proti výkyvům)
DEBOUNCE_SEC = 2

# Minimální odstup mezi dvěma přepnutími Wi-Fi (ochrana proti "cvakání")
MIN_TOGGLE_GAP = 4

# Jak dlouho po zapnutí Wi-Fi čekat, než se může přejít do idle (čas na připojení k síti)
WIFI_GRACE_SEC = 20

# Zapnout výpis informací do konzole (logy v terminálu)
VERBOSE = True

# ====== CESTY K NÁSTROJŮM (kvůli běhu pod launchd) ======
NETWORKSETUP = "/usr/sbin/networksetup"
IFCONFIG = "/sbin/ifconfig"

# ==============================================
# Pomocné funkce – tady začíná logika
# ==============================================

def run(cmd: List[str]) -> Tuple[int, str, str]:
    """Spustí shell příkaz a vrátí (return_code, stdout, stderr)."""
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def list_hardware_ports() -> Dict[str, str]:
    """Vrátí slovník {Hardware Port -> Device}, např. {'Wi-Fi': 'en0', 'Thunderbolt Ethernet Slot 1': 'en10'}"""
    rc, out, err = run([NETWORKSETUP, "-listallhardwareports"])
    if rc != 0:
        raise RuntimeError(f"networksetup selhal: {err or out}")
    mapping, current_port = {}, None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Hardware Port:"):
            current_port = s.split("Hardware Port:", 1)[1].strip()
        elif s.startswith("Device:") and current_port:
            dev = s.split("Device:", 1)[1].strip()
            mapping[current_port] = dev
        elif s == "":
            current_port = None
    return mapping


def current_ssid(dev_or_service: str) -> str:
    """Zjistí, ke které Wi-Fi síti je zařízení aktuálně připojené (SSID)."""
    rc, out, _ = run([NETWORKSETUP, "-getairportnetwork", dev_or_service])
    if rc == 0 and "Current Wi-Fi Network:" in out:
        return out.split(":", 1)[1].strip()
    return ""


def is_interface_active(dev: str) -> bool:
    """Vrátí True, pokud má síťové rozhraní (např. en10) status 'active'."""
    rc, out, _ = run([IFCONFIG, dev])
    if rc != 0:
        return False
    for line in out.splitlines():
        if "status:" in line:
            return "active" in line.lower()
    return False


def wifi_power_is_on(dev_or_service: str) -> Optional[bool]:
    """Zjistí, jestli je Wi-Fi zapnutá nebo vypnutá."""
    rc, out, _ = run([NETWORKSETUP, "-getairportpower", dev_or_service])
    if rc == 0 and ":" in out:
        state = out.split(":", 1)[1].strip().lower()
        if "on" in state:
            return True
        if "off" in state:
            return False
    return None


def set_wifi(dev_or_service: str, enable: bool) -> bool:
    """Zapne nebo vypne Wi-Fi."""
    state = "on" if enable else "off"
    rc, out, err = run([NETWORKSETUP, "-setairportpower", dev_or_service, state])
    if VERBOSE:
        print(f"[wifi] {dev_or_service} -> {state} (rc={rc}) {err or out}")
    if rc == 0:
        return True
    # fallback: když networksetup selže, použij ifconfig
    rc, out, err = run([IFCONFIG, dev_or_service, "up" if enable else "down"])
    if VERBOSE:
        print(f"[wifi-ifcfg] {dev_or_service} -> {'up' if enable else 'down'} (rc={rc}) {err or out}")
    return rc == 0


# ==============================================
# Hlavní logika skriptu
# ==============================================

def main():
    # Získání seznamu všech síťových rozhraní
    hw = list_hardware_ports()
    if VERBOSE:
        print("[info] HW porty:", hw)

    # Typicky: Wi-Fi bývá 'en0'
    wifi_dev = hw.get("Wi-Fi", "en0")

    # Všechna rozhraní začínající na "en" kromě Wi-Fi považujeme za „drátové“ (ethernet, thunderbolt, USB LAN…)
    wired_candidates = sorted({d for d in hw.values() if d.startswith("en") and d != wifi_dev})
    wired_candidates = [d for d in wired_candidates if not d.startswith("bridge")]

    if VERBOSE:
        print("[info] Drátová rozhraní:", wired_candidates or "(nic nenalezeno)")

    # Uložení výchozího stavu
    last_toggle = 0.0
    last_wifi_state = wifi_power_is_on(wifi_dev)
    last_wired_seen: Optional[bool] = None
    last_change = time.monotonic()
    grace_until = 0.0  # do kdy trvá "grace period" po zapnutí Wi-Fi

    # === Hlavní nekonečný cyklus ===
    while True:

        # 1️⃣ — Zjisti, jestli je nějaké drátové rozhraní aktivní
        wired_active = any(is_interface_active(d) for d in wired_candidates)

        # Pokud se stav drátu změnil (např. zapojil/odpojil se kabel), zapamatuj si čas změny
        if last_wired_seen is None or wired_active != last_wired_seen:
            last_wired_seen = wired_active
            last_change = time.monotonic()

        # Debounce — ignoruj krátkodobé výkyvy linku (např. při zapojování kabelu)
        if time.monotonic() - last_change < DEBOUNCE_SEC:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        # 2️⃣ — Pokud není drát aktivní a Wi-Fi je vypnutá, zapni ji (recovery)
        if not wired_active and (last_wifi_state is False):
            if VERBOSE:
                print("[recover] Žádný drát → zapínám Wi-Fi a čekám na připojení…")
            if set_wifi(wifi_dev, True):
                last_wifi_state = True
                last_toggle = time.monotonic()
                grace_until = last_toggle + WIFI_GRACE_SEC  # zapamatuj si, že Wi-Fi má čas na připojení

        # 3️⃣ — Zjisti aktuální SSID (název Wi-Fi sítě)
        ssid = current_ssid(wifi_dev) if (last_wifi_state is True) else ""
        in_office = ssid in OFFICE_SSIDS if ssid else False  # jsme v kancelářské síti?
        in_grace = time.monotonic() < grace_until            # jsme ještě ve fázi připojování?

        if VERBOSE:
            print(f"[gate] SSID='{ssid or '-'}' in_office={in_office} wired_active={wired_active} grace={in_grace}")

        # 4️⃣ — Pokud nejsme v kanceláři, žádný drát není aktivní a nejsme v "grace", přejdi do idle
        if not in_office and not wired_active and not in_grace:
            if VERBOSE:
                print(f"[idle] Mimo kancelář a bez drátu → spím {IDLE_SLEEP_SECONDS}s")
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        # 5️⃣ — Hlavní rozhodovací logika: zapnout nebo vypnout Wi-Fi?
        desired_wifi_on = not wired_active  # drát aktivní → Wi-Fi OFF, jinak ON
        now = time.monotonic()
        if last_wifi_state is None or desired_wifi_on != last_wifi_state:
            # ochrana proti příliš častému přepínání
            if now - last_toggle >= MIN_TOGGLE_GAP:
                if VERBOSE:
                    print(f"[action] wired_active={wired_active} → Wi-Fi {'ON' if desired_wifi_on else 'OFF'}")
                if set_wifi(wifi_dev, desired_wifi_on):
                    last_wifi_state = desired_wifi_on
                    last_toggle = now
                    # pokud jsme Wi-Fi zapli, přidej novou grace period
                    if desired_wifi_on:
                        grace_until = now + WIFI_GRACE_SEC
                else:
                    print("[warn] Nastavení Wi-Fi se nepovedlo – zkusím znovu později.")
            else:
                if VERBOSE:
                    print("[ratelimit] Přepínal jsem nedávno, čekám…")

        # 6️⃣ — Počkej pár sekund a opakuj kontrolu
        time.sleep(POLL_INTERVAL_SECONDS)


# ==============================================
# Spuštění hlavní funkce
# ==============================================

if __name__ == "__main__":
    main()