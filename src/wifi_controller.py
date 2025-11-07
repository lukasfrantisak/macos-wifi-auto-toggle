# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
WIFI CONTROLLER - Ovládání Wi-Fi rozhraní
=============================================================================
Tento modul se stará o:
- Zjištění stavu Wi-Fi (zapnuto/vypnuto)
- Zapínání a vypínání Wi-Fi
- Získání aktuálního SSID (název sítě)

Používá macOS příkazy:
- networksetup -getairportpower DEVICE  (zjistí stav)
- networksetup -setairportpower DEVICE on/off  (zapne/vypne)
- airport -I  (získá info o Wi-Fi včetně SSID)
=============================================================================
"""

import subprocess
from typing import Optional, Tuple
from enum import Enum


class WiFiState(Enum):
    """
    Enum = výčtový typ (enumeration)
    Používá se pro omezený počet možných hodnot.
    """
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"


class WiFiController:
    """
    Třída pro ovládání Wi-Fi na macOS.
    """

    def __init__(self, service_name: str = "Wi-Fi", logger=None):
        """
        Inicializace Wi-Fi controlleru.

        Args:
            service_name: Název Wi-Fi služby v System Preferences (např. "Wi-Fi")
            logger: Logger instance
        """
        self.service_name = service_name
        self.logger = logger
        self.airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"

        # Zjistíme device name (en0) pro tento service
        self.device_name = self._get_device_name_for_service(service_name)

        if not self.device_name:
            self._log("error", f"Nelze najít device pro Wi-Fi službu '{service_name}'")
            self._log("error", "Zkus: networksetup -listallhardwareports")
        else:
            self._log("info", f"Wi-Fi služba '{service_name}' používá device: {self.device_name}")

    def _log(self, level: str, message: str):
        """Pomocná metoda pro logování."""
        if self.logger:
            log_method = getattr(self.logger, level, None)
            if log_method:
                log_method(message)

    def _run_command(self, cmd: list, timeout: int = 10) -> Tuple[int, str, str]:
        """Spustí systémový příkaz a vrátí výsledek."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            self._log("error", f"Příkaz timeout: {' '.join(cmd)}")
            return -1, "", "Timeout"
        except Exception as e:
            self._log("error", f"Chyba při spuštění příkazu: {e}")
            return -1, "", str(e)

    def _get_device_name_for_service(self, service_name: str) -> Optional[str]:
        """
        Najde device name (např. en0) pro danou službu (např. "Wi-Fi").

        networksetup -getairportpower potřebuje DEVICE NAME, ne service name!

        Args:
            service_name: Název služby (např. "Wi-Fi")

        Returns:
            Device name (např. "en0") nebo None
        """
        rc, stdout, _ = self._run_command(["networksetup", "-listallhardwareports"])

        if rc != 0:
            return None

        # Parsujeme výstup:
        # Hardware Port: Wi-Fi
        # Device: en0
        # Ethernet Address: xx:xx:xx:xx:xx:xx

        lines = stdout.split("\n")
        found_service = False

        for line in lines:
            line = line.strip()

            # Našli jsme náš service?
            if line.startswith("Hardware Port:") and service_name in line:
                found_service = True
                continue

            # Pokud jsme našli service, hledáme Device na dalším řádku
            if found_service and line.startswith("Device:"):
                device = line.split(":", 1)[1].strip()
                return device

        return None

    def get_state(self) -> WiFiState:
        """
        Zjistí aktuální stav Wi-Fi (zapnuto/vypnuto).

        Volá: networksetup -getairportpower DEVICE
        Výstup: "Wi-Fi Power (en0): On" nebo "Off"

        Returns:
            WiFiState.ON, WiFiState.OFF nebo WiFiState.UNKNOWN
        """
        if not self.device_name:
            self._log("error", "Device name není známo, nelze zjistit stav")
            return WiFiState.UNKNOWN

        # DŮLEŽITÉ: Používáme DEVICE NAME (en0), ne service name!
        rc, stdout, stderr = self._run_command([
            "networksetup",
            "-getairportpower",
            self.device_name  # ← Tady je změna!
        ])

        # Pokud příkaz selhal
        if rc != 0:
            self._log("warning", f"Nelze zjistit stav Wi-Fi: {stderr}")
            return WiFiState.UNKNOWN

        # Parsování výstupu
        output_lower = stdout.lower()

        if ": on" in output_lower:
            self._log("debug", "Wi-Fi je zapnuto")
            return WiFiState.ON
        elif ": off" in output_lower:
            self._log("debug", "Wi-Fi je vypnuto")
            return WiFiState.OFF
        else:
            self._log("warning", f"Neočekávaný výstup při zjišťování stavu Wi-Fi: {stdout}")
            return WiFiState.UNKNOWN

    def is_on(self) -> Optional[bool]:
        """
        Zkratka pro zjištění zda je Wi-Fi zapnuto.

        Returns:
            True = zapnuto
            False = vypnuto
            None = stav nelze určit
        """
        state = self.get_state()
        if state == WiFiState.ON:
            return True
        elif state == WiFiState.OFF:
            return False
        else:
            return None

    def set_power(self, turn_on: bool) -> bool:
        """
        Zapne nebo vypne Wi-Fi.

        Volá: networksetup -setairportpower DEVICE on/off

        Args:
            turn_on: True = zapnout, False = vypnout

        Returns:
            True pokud se operace podařila, False při chybě
        """
        if not self.device_name:
            self._log("error", "Device name není známo, nelze změnit stav")
            return False

        state_str = "on" if turn_on else "off"
        action = "Zapínám" if turn_on else "Vypínám"

        self._log("info", f"{action} Wi-Fi...")

        # DŮLEŽITÉ: Používáme DEVICE NAME (en0), ne service name!
        rc, stdout, stderr = self._run_command([
            "networksetup",
            "-setairportpower",
            self.device_name,  # ← Tady je změna!
            state_str
        ])

        if rc != 0:
            self._log("error", f"Chyba při {action.lower()} Wi-Fi: {stderr}")
            return False

        # Ověříme, že se to skutečně povedlo
        import time
        time.sleep(1)  # Chvilku počkáme, než se stav změní

        new_state = self.get_state()
        expected_state = WiFiState.ON if turn_on else WiFiState.OFF

        if new_state != expected_state:
            self._log("warning", f"Wi-Fi se {action.lower()}, ale stav je: {new_state.value}")
            return False

        self._log("info", f"✓ Wi-Fi úspěšně {'zapnuto' if turn_on else 'vypnuto'}")
        return True

    def turn_on(self) -> bool:
        """Zapne Wi-Fi (zkratka pro set_power(True))."""
        return self.set_power(True)

    def turn_off(self) -> bool:
        """Vypne Wi-Fi (zkratka pro set_power(False))."""
        return self.set_power(False)

    def get_current_ssid(self) -> Optional[str]:
        """
        Získá SSID aktuálně připojené Wi-Fi sítě.

        Volá: airport -I
        Parsuje řádek: "SSID: název_sítě"

        Returns:
            SSID jako string, nebo None pokud není připojeno
        """
        # Nejdřív zkontrolujeme, že Wi-Fi je zapnuto
        if self.get_state() != WiFiState.ON:
            self._log("debug", "Wi-Fi je vypnuto, nemůže být připojeno k síti")
            return None

        # Spustíme airport -I (capital I = info)
        rc, stdout, stderr = self._run_command([self.airport_path, "-I"])

        if rc != 0:
            self._log("warning", f"Nelze získat Wi-Fi info: {stderr}")
            return None

        # Parsujeme výstup - hledáme řádek se SSID
        for line in stdout.split("\n"):
            line = line.strip()

            if line.startswith("SSID:"):
                ssid = line.split(":", 1)[1].strip()

                if not ssid:
                    self._log("debug", "Wi-Fi není připojeno k žádné síti")
                    return None

                self._log("debug", f"Připojeno k Wi-Fi: {ssid}")
                return ssid

        self._log("debug", "SSID nenalezeno ve výstupu airport")
        return None

    def is_connected_to_ssid(self, ssid_list: list) -> bool:
        """
        Zkontroluje, zda jsme připojeni k některému ze zadaných SSID.

        Args:
            ssid_list: Seznam SSID

        Returns:
            True pokud jsme připojeni k některému z nich
        """
        current_ssid = self.get_current_ssid()

        if not current_ssid:
            return False

        return current_ssid in ssid_list