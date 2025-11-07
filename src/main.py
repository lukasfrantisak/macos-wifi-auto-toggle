# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
MAIN - Hlavní řídící logika Wi-Fi Auto Toggle
=============================================================================
Toto je "command block" celého systému - řídící centrum.

Co dělá:
1. Načte konfiguraci z config.yaml
2. Inicializuje všechny komponenty (logger, detector, wifi, notifier)
3. Spustí hlavní smyčku, která:
   - Sleduje stav Thunderbolt karty
   - Zjišťuje stav Wi-Fi
   - Podle logiky zapíná/vypíná Wi-Fi
   - Loguje vše co se děje
   - Posílá notifikace

Analogie v Minecraftu:
    Tohle je ten hlavní "redstone clock" s logikou,
    který řídí všechny ostatní komponenty (observer, piston, hopper...).
=============================================================================
"""

import sys
import time
import signal
from pathlib import Path
from typing import Optional

# Import knihovny pro YAML
# (pokud ještě nemáš nainstalovanou, spusť: pip3 install pyyaml)
import yaml

# Importujeme naše moduly
from logger import setup_logger, get_logger
from network_detector import NetworkDetector
from wifi_controller import WiFiController, WiFiState
from notifier import Notifier


class WiFiAutoToggle:
    """
    Hlavní třída aplikace.

    Tohle je jako "blueprint" celé farmy v Minecraftu.
    Obsahuje všechny komponenty a logiku jak fungují dohromady.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Inicializace aplikace.

        Args:
            config_path: Cesta ke konfiguračnímu souboru
        """
        # Načteme konfiguraci
        self.config = self._load_config(config_path)

        # Nastavíme logger (podle configu)
        self.logger = self._setup_logger()

        # Vytvoříme komponenty
        self.detector = NetworkDetector(logger=self.logger)
        self.wifi = WiFiController(
            service_name=self.config['network']['wifi_service_name'],
            logger=self.logger
        )
        self.notifier = Notifier(
            app_name="Wi-Fi Auto Toggle",
            enabled=self.config['behavior']['enable_notifications'],
            default_sound=self.config['behavior']['notification_sound'],
            logger=self.logger
        )

        # Stavové proměnné - pamatujeme si co se dělo naposledy
        # (aby jsme nespamovali notifikace/logy při každém cyklu)
        self.last_thunderbolt_state = None  # Byl Thunderbolt připojen?
        self.last_wifi_state = None  # Bylo Wi-Fi zapnuto?

        # Flag pro ukončení (nastaví se při Ctrl+C)
        self.running = False

    def _load_config(self, config_path: str) -> dict:
        """
        Načte konfiguraci z YAML souboru.

        YAML = "YAML Ain't Markup Language"
        Je to formát pro konfigurační soubory (jako JSON, ale čitelnější)

        Args:
            config_path: Cesta k config.yaml

        Returns:
            Slovník (dict) s konfigurací
        """
        config_file = Path(config_path)

        # Zkontrolujeme, že soubor existuje
        if not config_file.exists():
            print(f"❌ CHYBA: Konfigurační soubor nenalezen: {config_path}")
            print(f"   Očekávaná cesta: {config_file.absolute()}")
            sys.exit(1)

        # Načteme YAML
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                # yaml.safe_load = bezpečně načte YAML do Python dict
                config = yaml.safe_load(f)
                print(f"✓ Konfigurace načtena z: {config_path}")
                return config
        except yaml.YAMLError as e:
            print(f"❌ CHYBA: Nelze parsovat YAML: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ CHYBA při načítání configu: {e}")
            sys.exit(1)

    def _setup_logger(self):
        """
        Nastaví logger podle konfigurace.

        Returns:
            Logger instance
        """
        log_config = self.config['logging']

        return setup_logger(
            name="wifi-toggle",
            level=log_config['level'],
            targets=log_config['targets'],
            log_file=log_config.get('file_path'),
            max_bytes=log_config.get('max_file_size_mb', 10) * 1024 * 1024,  # MB → bytes
            backup_count=log_config.get('backup_count', 3)
        )

    def _check_thunderbolt_status(self) -> bool:
        """
        Zkontroluje, zda je Thunderbolt karta připojena a funkční.

        Returns:
            True pokud je Thunderbolt připojen (existuje interface)
        """
        port_name = self.config['network']['thunderbolt_port_name']

        # Najdeme Thunderbolt interface
        thunderbolt = self.detector.find_thunderbolt(port_name)

        # Pro tvůj případ: i když nemá link, chceme vědět že existuje
        # (protože doma nemáš SFP+ kabel)
        if thunderbolt:
            self.logger.debug(f"Thunderbolt detekován: {thunderbolt.device} "
                              f"(active={thunderbolt.is_active}, ip={thunderbolt.has_ip})")
            return True
        else:
            self.logger.debug("Thunderbolt není připojen")
            return False

    def _check_wifi_status(self) -> Optional[bool]:
        """
        Zkontroluje stav Wi-Fi.

        Returns:
            True = zapnuto, False = vypnuto, None = nelze určit
        """
        state = self.wifi.get_state()

        if state == WiFiState.ON:
            return True
        elif state == WiFiState.OFF:
            return False
        else:
            return None

    def _enforce_correct_state(self):
        """
        Při startu vynucuje správný stav Wi-Fi podle aktuální situace.

        Tohle se volá jen jednou při spuštění, pokud je v configu:
            behavior.enforce_on_startup: true

        Zajistí, že Wi-Fi je ve správném stavu hned od začátku.
        """
        if not self.config['behavior']['enforce_on_startup']:
            return

        thunderbolt_connected = self._check_thunderbolt_status()
        wifi_on = self._check_wifi_status()

        if wifi_on is None:
            self.logger.warning("Nelze určit stav Wi-Fi při startu")
            return

        # Logika: Thunderbolt připojen → Wi-Fi by mělo být vypnuto
        #         Thunderbolt odpojen → Wi-Fi by mělo být zapnuto

        if thunderbolt_connected and wifi_on:
            # Thunderbolt JE, Wi-Fi JE → musíme vypnout Wi-Fi
            self.logger.info("🔧 Startup: Thunderbolt připojen, vypínám Wi-Fi...")
            if self.wifi.turn_off():
                self.notifier.send(
                    "Wi-Fi vypnuto při startu",
                    "Thunderbolt je připojen → Wi-Fi automaticky vypnuto"
                )

        elif not thunderbolt_connected and not wifi_on:
            # Thunderbolt NENÍ, Wi-Fi NENÍ → musíme zapnout Wi-Fi
            self.logger.info("🔧 Startup: Thunderbolt odpojen, zapínám Wi-Fi...")
            if self.wifi.turn_on():
                self.notifier.send(
                    "Wi-Fi zapnuto při startu",
                    "Thunderbolt není připojen → Wi-Fi automaticky zapnuto"
                )

    def _handle_state_change(self, thunderbolt_connected: bool, wifi_on: bool):
        """
        Zpracuje změnu stavu a provede příslušnou akci.

        Tohle je hlavní "redstone logic" - rozhoduje co udělat.

        Args:
            thunderbolt_connected: Je Thunderbolt připojen?
            wifi_on: Je Wi-Fi zapnuto?
        """
        # Detekujeme změny oproti minulému stavu
        thunderbolt_changed = (self.last_thunderbolt_state != thunderbolt_connected)
        wifi_changed = (self.last_wifi_state != wifi_on)

        # ==============================================================
        # PŘÍPAD 1: Thunderbolt se PŘIPOJIL
        # ==============================================================
        if thunderbolt_changed and thunderbolt_connected:
            self.logger.info("⚡ Thunderbolt PŘIPOJEN")

            # Pokud je Wi-Fi zapnuto, vypneme ho
            if wifi_on:
                self.logger.info("→ Vypínám Wi-Fi (kabel je priorita)")
                if self.wifi.turn_off():
                    self.notifier.notify_wifi_change(turned_on=False)
                    self.last_wifi_state = False

        # ==============================================================
        # PŘÍPAD 2: Thunderbolt se ODPOJIL
        # ==============================================================
        elif thunderbolt_changed and not thunderbolt_connected:
            self.logger.info("⚡ Thunderbolt ODPOJEN")

            # Pokud je Wi-Fi vypnuto, zapneme ho
            if not wifi_on:
                self.logger.info("→ Zapínám Wi-Fi (žádné kabelové připojení)")
                if self.wifi.turn_on():
                    self.notifier.notify_wifi_change(turned_on=True)
                    self.last_wifi_state = True

        # ==============================================================
        # PŘÍPAD 3: Wi-Fi se změnilo samo (uživatel, systém...)
        # ==============================================================
        elif wifi_changed:
            self.logger.info(f"📶 Wi-Fi změněno externě: {'ON' if wifi_on else 'OFF'}")

            # Pokud je Thunderbolt připojen a někdo zapnul Wi-Fi ručně,
            # respektujeme to (nevypneme ho automaticky)
            # Ale zalogujeme to
            if thunderbolt_connected and wifi_on:
                self.logger.warning("⚠️ Thunderbolt připojen, ale Wi-Fi je zapnuto (manuální změna?)")

        # Aktualizujeme stavové proměnné
        self.last_thunderbolt_state = thunderbolt_connected
        self.last_wifi_state = wifi_on

    def run(self):
        """
        Hlavní smyčka aplikace (main loop).

        Tohle je ten "redstone clock" - běží dokola a kontroluje stav.
        """
        self.logger.info("=" * 70)
        self.logger.info("🚀 Wi-Fi Auto Toggle - START")
        self.logger.info("=" * 70)
        self.logger.info(f"Python: {sys.version.split()[0]}")
        self.logger.info(f"Thunderbolt port: {self.config['network']['thunderbolt_port_name']}")
        self.logger.info(f"Wi-Fi service: {self.config['network']['wifi_service_name']}")
        self.logger.info(f"Check interval: {self.config['behavior']['check_interval']}s")
        self.logger.info("=" * 70)

        # Vynucení správného stavu při startu
        self._enforce_correct_state()

        # Načteme počáteční stav
        self.last_thunderbolt_state = self._check_thunderbolt_status()
        self.last_wifi_state = self._check_wifi_status()

        # Startup notifikace
        self.notifier.notify_startup(
            thunderbolt_connected=self.last_thunderbolt_state,
            wifi_on=self.last_wifi_state if self.last_wifi_state is not None else False
        )

        self.logger.info(f"Počáteční stav: Thunderbolt={'PŘIPOJEN' if self.last_thunderbolt_state else 'ODPOJEN'}, "
                         f"Wi-Fi={'ZAPNUTO' if self.last_wifi_state else 'VYPNUTO'}")

        # Nastavíme flag
        self.running = True

        # Hlavní smyčka
        check_interval = self.config['behavior']['check_interval']

        try:
            while self.running:
                # ========================================
                # KROK 1: Zjistit aktuální stav
                # ========================================
                thunderbolt_connected = self._check_thunderbolt_status()
                wifi_on = self._check_wifi_status()

                # Pokud nelze zjistit stav Wi-Fi, přeskočíme tento cyklus
                if wifi_on is None:
                    self.logger.warning("⚠️ Nelze zjistit stav Wi-Fi, čekám...")
                    time.sleep(check_interval)
                    continue

                # ========================================
                # KROK 2: Zpracovat změny
                # ========================================
                self._handle_state_change(thunderbolt_connected, wifi_on)

                # ========================================
                # KROK 3: Čekat do dalšího cyklu
                # ========================================
                # time.sleep = pozastaví program na X sekund
                # (jako delay v repeater clocku)
                time.sleep(check_interval)

        except KeyboardInterrupt:
            # Ctrl+C = uživatel ukončil program
            self.logger.info("\n🛑 Přerušeno uživatelem (Ctrl+C)")
            self.running = False

        except Exception as e:
            # Neočekávaná chyba
            self.logger.error(f"❌ Kritická chyba: {e}", exc_info=True)
            self.notifier.notify_error(f"Kritická chyba: {e}")
            raise

        finally:
            # finally = provede se VŽDY (i když nastane chyba)
            # Použití: cleanup, zavření souborů, apod.
            self.logger.info("=" * 70)
            self.logger.info("👋 Wi-Fi Auto Toggle ukončen")
            self.logger.info("=" * 70)

    def stop(self):
        """
        Ukončí běh aplikace (zastaví main loop).
        """
        self.logger.info("Zastavuji aplikaci...")
        self.running = False


def main():
    """
    Entry point - vstupní bod programu.

    Tato funkce se spustí, když spustíš skript:
        python3 src/main.py
    """
    # Najdeme cestu k config.yaml
    # __file__ = cesta k aktuálnímu souboru (main.py)
    # .parent = nadřazená složka (src/)
    # .parent = ještě o úroveň výš (macos-wifi-auto-toggle/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    config_path = project_root / "config.yaml"

    print("🔧 Wi-Fi Auto Toggle for macOS")
    print(f"📁 Project root: {project_root}")
    print(f"⚙️  Config: {config_path}")
    print()

    # Vytvoříme aplikaci
    app = WiFiAutoToggle(config_path=str(config_path))

    # Nastavíme signal handler pro graceful shutdown
    # (když někdo pošle SIGTERM/SIGINT, ukončíme se čistě)
    def signal_handler(sig, frame):
        """Handler pro Ctrl+C a kill signály."""
        print("\n🛑 Signal přijat, ukončuji...")
        app.stop()

    # signal.signal = nastaví handler pro signály
    # SIGINT = Ctrl+C
    # SIGTERM = kill command (default)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Spustíme aplikaci
    app.run()


# ===========================================================================
# Toto se spustí POUZE když spustíš tento soubor přímo:
#     python3 src/main.py
#
# Nespustí se když ho importuješ jako modul v jiném souboru:
#     from src.main import WiFiAutoToggle
# ===========================================================================
if __name__ == "__main__":
    main()