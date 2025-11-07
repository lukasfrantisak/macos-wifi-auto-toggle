#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
NOTIFIER - Odesílání macOS notifikací
=============================================================================
Tento modul odesílá notifikace do Notification Center.

Podporuje dva způsoby:
1. terminal-notifier (pokud je nainstalován) - více možností, zvuky
2. osascript + AppleScript (vestavěné v macOS) - fallback bez závislostí

terminal-notifier instalace:
    brew install terminal-notifier
=============================================================================
"""

import subprocess
import shutil
from typing import Optional


class Notifier:
    """
    Třída pro odesílání macOS notifikací.

    Použití:
        notifier = Notifier(app_name="Wi-Fi Toggle")
        notifier.send("Nadpis", "Text zprávy", sound="Submarine")
    """

    def __init__(
            self,
            app_name: str = "Wi-Fi Auto Toggle",
            enabled: bool = True,
            default_sound: Optional[str] = None,
            logger=None
    ):
        """
        Inicializace notifier.

        Args:
            app_name: Název aplikace (zobrazí se v notifikaci)
            enabled: Povolit notifikace? (false = notifikace se neposílají)
            default_sound: Výchozí zvuk (např. "Submarine", "Glass", "Ping")
                          None = bez zvuku
            logger: Logger instance
        """
        self.app_name = app_name
        self.enabled = enabled
        self.default_sound = default_sound
        self.logger = logger

        # Zjistíme, zda je dostupný terminal-notifier
        # shutil.which("command") = najde cestu k příkazu (jako `which` v shellu)
        self.terminal_notifier_path = shutil.which("terminal-notifier")

        if self.terminal_notifier_path:
            self._log("debug", f"Použiji terminal-notifier: {self.terminal_notifier_path}")
        else:
            self._log("debug", "terminal-notifier není nainstalován, použiji AppleScript fallback")

    def _log(self, level: str, message: str):
        """Pomocná metoda pro logování."""
        if self.logger:
            log_method = getattr(self.logger, level, None)
            if log_method:
                log_method(message)

    def _run_command(self, cmd: list) -> tuple:
        """Spustí příkaz a vrátí výsledek."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=5
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            self._log("error", f"Chyba při notifikaci: {e}")
            return -1, "", str(e)

    def send(
            self,
            title: str,
            message: str,
            sound: Optional[str] = None,
            subtitle: Optional[str] = None
    ) -> bool:
        """
        Odešle notifikaci do Notification Center.

        Args:
            title: Nadpis notifikace (tučně)
            message: Text zprávy
            sound: Zvuk notifikace (přepíše default_sound)
                   Možné hodnoty: "Submarine", "Glass", "Ping", "Funk", ...
                   None = bez zvuku
            subtitle: Podtitulek (volitelné, mezi nadpisem a zprávou)

        Returns:
            True pokud se notifikace odeslala, False při chybě
        """
        # Pokud jsou notifikace vypnuté, nic neděláme
        if not self.enabled:
            self._log("debug", "Notifikace vypnuty, přeskakuji")
            return True

        # Určíme, jaký zvuk použít
        sound_to_use = sound if sound is not None else self.default_sound

        # Pokud máme terminal-notifier, použijeme ho
        if self.terminal_notifier_path:
            return self._send_with_terminal_notifier(title, message, sound_to_use, subtitle)
        else:
            # Fallback na AppleScript
            return self._send_with_applescript(title, message, sound_to_use)

    def _send_with_terminal_notifier(
            self,
            title: str,
            message: str,
            sound: Optional[str],
            subtitle: Optional[str]
    ) -> bool:
        """
        Odešle notifikaci pomocí terminal-notifier.

        terminal-notifier je external nástroj s více možnostmi než AppleScript.
        """
        # Sestavíme příkaz
        cmd = [
            self.terminal_notifier_path,
            "-title", title,
            "-message", message,
            "-group", self.app_name,  # Seskupí notifikace od stejné aplikace
        ]

        # Přidáme subtitle (pokud je zadán)
        if subtitle:
            cmd.extend(["-subtitle", subtitle])

        # Přidáme zvuk (pokud je zadán)
        if sound:
            cmd.extend(["-sound", sound])

        # Odešleme
        self._log("debug", f"Odesílám notifikaci: {title}")
        rc, stdout, stderr = self._run_command(cmd)

        if rc != 0:
            self._log("warning", f"Notifikace selhala: {stderr}")
            return False

        return True

    def _send_with_applescript(self, title: str, message: str, sound: Optional[str]) -> bool:
        """
        Odešle notifikaci pomocí AppleScript (fallback).

        AppleScript je vestavěný skriptovací jazyk v macOS.
        Spouští se přes `osascript` příkaz.
        """
        # AppleScript kód pro notifikaci
        # display notification "text" with title "nadpis"
        script = f'display notification "{message}" with title "{title}"'

        # Pokud je zvuk, přidáme sound name
        # (poznámka: AppleScript podporuje jen základní systémové zvuky)
        if sound:
            script += f' sound name "{sound}"'

        self._log("debug", f"Odesílám notifikaci (AppleScript): {title}")

        # Spustíme osascript s inline kódem
        # osascript -e "AppleScript kód"
        rc, stdout, stderr = self._run_command(["osascript", "-e", script])

        if rc != 0:
            self._log("warning", f"AppleScript notifikace selhala: {stderr}")
            return False

        return True

    def notify_wifi_change(self, turned_on: bool):
        """
        Odešle notifikaci o změně stavu Wi-Fi.

        Args:
            turned_on: True = Wi-Fi bylo zapnuto, False = vypnuto
        """
        if turned_on:
            self.send(
                title="Wi-Fi zapnuto",
                message="Kabelové připojení odpojeno → Wi-Fi automaticky zapnuto",
                sound=self.default_sound
            )
        else:
            self.send(
                title="Wi-Fi vypnuto",
                message="Kabelové připojení aktivní → Wi-Fi automaticky vypnuto",
                sound=self.default_sound
            )

    def notify_startup(self, thunderbolt_connected: bool, wifi_on: bool):
        """
        Odešle notifikaci při startu skriptu.

        Args:
            thunderbolt_connected: Je Thunderbolt připojen?
            wifi_on: Je Wi-Fi zapnuto?
        """
        tb_status = "připojen" if thunderbolt_connected else "odpojen"
        wifi_status = "zapnuto" if wifi_on else "vypnuto"

        self.send(
            title="Wi-Fi Auto Toggle spuštěn",
            message=f"Thunderbolt: {tb_status}\nWi-Fi: {wifi_status}",
            subtitle="Monitoring aktivní"
        )

    def notify_error(self, error_message: str):
        """
        Odešle chybovou notifikaci.

        Args:
            error_message: Popis chyby
        """
        self.send(
            title="⚠️ Wi-Fi Toggle - Chyba",
            message=error_message,
            sound="Funk"  # Jiný zvuk pro chyby
        )