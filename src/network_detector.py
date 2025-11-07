#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
NETWORK DETECTOR - Detekce síťových rozhraní
=============================================================================
Tento modul se stará o detekci:
- Thunderbolt QNAP karty (en10)
- Stavu Wi-Fi (en0)
- Aktivního síťového rozhraní
- SSID Wi-Fi sítě (pro detekci kanceláře)

Používá macOS příkazy:
- networksetup - správa síťových nastavení
- ifconfig - informace o rozhraních
- /System/Library/PrivateFrameworks/Apple80211.framework - Wi-Fi info
=============================================================================
"""

import subprocess
import re
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class NetworkInterface:
    """
    Datová třída reprezentující síťové rozhraní.

    @dataclass = dekorátor který automaticky vytvoří __init__, __repr__ atd.
    Je to moderní pythonic způsob jak vytvářet jednoduché třídy pro data.
    """
    hardware_port: str  # Název hardware portu (např. "Thunderbolt Ethernet Slot 1")
    device: str  # Device name (např. "en10")
    mac_address: str  # MAC adresa (např. "24:5e:be:7c:42:44")
    is_active: bool = False  # Má aktivní link/carrier?
    has_ip: bool = False  # Má přiřazenou IP adresu?


class NetworkDetector:
    """
    Třída pro detekci síťových rozhraní a jejich stavu.

    Třída = "šablona" pro vytváření objektů
    Objekt = konkrétní instance třídy

    Použití:
        detector = NetworkDetector()  # Vytvoříme instanci
        thunderbolt = detector.find_thunderbolt("Thunderbolt Ethernet Slot 1")
    """

    def __init__(self, logger=None):
        """
        Konstruktor - volá se při vytvoření instance.

        __init__ = speciální metoda (tzv. "dunder" = double underscore)
        self = odkaz na aktuální instanci (v jiných jazycích "this")

        Args:
            logger: Logger instance pro logování (volitelné)
        """
        self.logger = logger

    def _log(self, level: str, message: str):
        """
        Pomocná metoda pro logování.

        Metody začínající _ jsou "private" (konvence, ne vynucení)
        = měly by se používat jen uvnitř třídy

        Args:
            level: Úroveň logu (info, debug, warning, error)
            message: Zpráva k zalogování
        """
        if self.logger:
            # getattr(obj, "method_name") = dynamicky získá metodu z objektu
            # Např. getattr(logger, "info") vrátí logger.info
            log_method = getattr(self.logger, level, None)
            if log_method:
                log_method(message)

    def _run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """
        Spustí systémový příkaz a vrátí výsledek.

        Args:
            cmd: Seznam s příkazem a argumenty
                 Např. ["networksetup", "-listallhardwareports"]

        Returns:
            Tuple (n-tice) s třemi hodnotami:
            - return code (0 = úspěch, jinak = chyba)
            - stdout (standardní výstup)
            - stderr (chybový výstup)
        """
        try:
            # subprocess.run = spustí externí příkaz
            result = subprocess.run(
                cmd,
                capture_output=True,  # Zachytí stdout a stderr
                text=True,  # Vrátí výstup jako string (ne bytes)
                check=False,  # Nehodí výjimku při chybě (kontrolujeme sami)
                timeout=10  # Timeout 10s (ochrana před zaseknutím)
            )

            # .strip() = odstraní bílé znaky (mezery, newline) ze začátku a konce
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            return result.returncode, stdout, stderr

        except subprocess.TimeoutExpired:
            # Výjimka = "exception" = chyba která přeruší normální běh programu
            # try/except = zachytí výjimku a zpracuje ji (program se nesekne)
            self._log("error", f"Příkaz timeout: {' '.join(cmd)}")
            return -1, "", "Timeout"
        except Exception as e:
            # Exception = obecná výjimka (zachytí cokoliv)
            # as e = uloží výjimku do proměnné e
            self._log("error", f"Chyba při spuštění příkazu {cmd}: {e}")
            return -1, "", str(e)

    def list_all_interfaces(self) -> List[NetworkInterface]:
        """
        Získá seznam všech síťových rozhraní z macOS.

        Volá: networksetup -listallhardwareports

        Returns:
            Seznam NetworkInterface objektů
        """
        rc, stdout, stderr = self._run_command(["networksetup", "-listallhardwareports"])

        if rc != 0:
            self._log("warning", f"Nelze získat seznam rozhraní: {stderr}")
            return []

        interfaces = []
        # Parsování výstupu - hledáme bloky:
        # Hardware Port: XXX
        # Device: enX
        # Ethernet Address: XX:XX:XX:XX:XX:XX

        lines = stdout.split("\n")
        current_port = None
        current_device = None
        current_mac = None

        for line in lines:
            line = line.strip()

            # .startswith() = zkontroluje začátek stringu
            if line.startswith("Hardware Port:"):
                # Uložíme předchozí rozhraní (pokud existuje)
                if current_port and current_device:
                    interfaces.append(NetworkInterface(
                        hardware_port=current_port,
                        device=current_device,
                        mac_address=current_mac or "unknown"
                    ))

                # .split(":", 1) = rozdělí string na 2 části u první ":"
                # [1] = vezmeme druhou část (za ":")
                current_port = line.split(":", 1)[1].strip()
                current_device = None
                current_mac = None

            elif line.startswith("Device:"):
                current_device = line.split(":", 1)[1].strip()

            elif line.startswith("Ethernet Address:"):
                current_mac = line.split(":", 1)[1].strip()

        # Přidáme poslední rozhraní
        if current_port and current_device:
            interfaces.append(NetworkInterface(
                hardware_port=current_port,
                device=current_device,
                mac_address=current_mac or "unknown"
            ))

        self._log("debug", f"Nalezeno rozhraní: {len(interfaces)}")
        return interfaces

    def find_thunderbolt(self, port_name: str) -> Optional[NetworkInterface]:
        """
        Najde Thunderbolt rozhraní podle názvu hardware portu.

        Args:
            port_name: Název z configu (např. "Thunderbolt Ethernet Slot 1")

        Returns:
            NetworkInterface nebo None (pokud není nalezeno)

        Optional[X] = typ hint znamená "buď X nebo None"
        """
        interfaces = self.list_all_interfaces()

        # List comprehension = kompaktní způsob filtrace listu
        # [x for x in list if podminka]
        # Je to pythonic způsob místo klasického for cyklu
        matching = [iface for iface in interfaces if iface.hardware_port == port_name]

        if not matching:
            self._log("debug", f"Thunderbolt '{port_name}' nenalezen")
            return None

        # Našli jsme - zjistíme detaily (má link? IP?)
        thunderbolt = matching[0]
        self._check_interface_status(thunderbolt)

        self._log("info", f"Thunderbolt nalezen: {thunderbolt.device} "
                          f"(active={thunderbolt.is_active}, ip={thunderbolt.has_ip})")
        return thunderbolt

    def _check_interface_status(self, interface: NetworkInterface):
        """
        Zjistí detailní stav rozhraní pomocí ifconfig.

        Aktualizuje interface.is_active a interface.has_ip

        Args:
            interface: NetworkInterface objekt (modifikuje ho in-place)
        """
        rc, stdout, _ = self._run_command(["ifconfig", interface.device])

        if rc != 0:
            return

        # Hledáme:
        # - "status: active" = má link/carrier
        # - "inet " = má IPv4 adresu
        interface.is_active = "status: active" in stdout.lower()
        interface.has_ip = "inet " in stdout

    def is_thunderbolt_really_connected(self, port_name: str) -> bool:
        """
        Zjistí, zda je Thunderbolt skutečně funkční (existuje + má link + IP).

        Args:
            port_name: Název hardware portu

        Returns:
            True pokud je Thunderbolt připojen a funkční
        """
        tb = self.find_thunderbolt(port_name)

        if not tb:
            return False

        # Thunderbolt je funkční = existuje + má aktivní link + má IP
        # Pro tvůj případ: i bez linku můžeš chtít vypnout Wi-Fi
        # Takže můžeš upravit na: return tb is not None
        return tb.is_active and tb.has_ip