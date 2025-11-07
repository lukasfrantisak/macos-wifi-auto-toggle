#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, time, sys

PYV = sys.version.split()[0]
print(f"[boot] Python: {PYV}", flush=True)

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

def notify(msg):
    rc, _, err = run([
        "/opt/homebrew/bin/terminal-notifier",
        "-title", "Wi-Fi Auto-Toggle",
        "-message", msg,
        "-sound", "Submarine"
    ])
    if rc != 0:
        print(f"[note] notify failed: {err}", flush=True)

def default_iface():
    rc, out, err = run(["/sbin/route", "-n", "get", "default"])
    if rc != 0:
        print(f"[warn] route exit={rc} err={err}", flush=True)
        return ""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("interface:"):
            return line.split(":", 1)[1].strip()
    return ""

def wifi_is_on():
    rc, out, err = run(["/usr/sbin/networksetup", "-getairportpower", "Wi-Fi"])
    txt = (out or err).lower()
    if "on" in txt:  return True
    if "off" in txt: return False
    print(f"[warn] nejasný stav Wi-Fi: rc={rc} out={out!r} err={err!r}", flush=True)
    return None

def wifi_set(on: bool):
    state = "on" if on else "off"
    rc, out, err = run(["/usr/sbin/networksetup", "-setairportpower", "Wi-Fi", state])
    ok = (rc == 0)
    print(f"[wifi] set {state}: rc={rc} out={out!r} err={err!r}", flush=True)
    if ok:
        notify(f"Wi-Fi {'zapnuta' if on else 'vypnuta'}")
    return ok

def wired_active_now():
    iface = default_iface()
    if iface.startswith("en") and iface != "en0":
        return True, iface
    return False, iface

def loop():
    last_state = None
    last_iface = None

    wired, iface = wired_active_now()
    is_on = wifi_is_on()
    notify(f"Start (Python {PYV}) • default_if={iface or '-'} • kabel={'ANO' if wired else 'NE'} • Wi-Fi={'?' if is_on is None else ('zapnuta' if is_on else 'vypnuta')}")

    while True:
        wired, iface = wired_active_now()
        want_wifi_on = not wired
        is_on = wifi_is_on()
        print(f"[gate] default_if={iface or '-'} wired_active={wired} want_wifi_on={want_wifi_on} wifi_is_on={is_on}", flush=True)

        if iface != last_iface:
            notify(f"Default interface: {iface or '-'}")
            last_iface = iface

        if is_on is None:
            time.sleep(30)
            continue

        key = (wired, is_on)
        if key != last_state:
            if is_on != want_wifi_on:
                notify(f"Kabel {'PŘIPOJEN' if wired else 'ODPOJEN'} → Wi-Fi {'zapnout' if want_wifi_on else 'vypnout'}")
                wifi_set(want_wifi_on)
            last_state = (wired, wifi_is_on())

        time.sleep(30)

if __name__ == "__main__":
    try:
        loop()
    except KeyboardInterrupt:
        pass
