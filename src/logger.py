#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
LOGGER - Modul pro logování událostí
=============================================================================
Tento modul vytváří a konfiguruje logger, který:
- Loguje do konzole (terminál)
- Loguje do souboru (s rotací - když soubor naroste, vytvoří nový)
- Podporuje různé úrovně logování (DEBUG, INFO, WARNING, ERROR)

Logger používá standardní Python knihovnu 'logging', která je součástí Pythonu.
=============================================================================
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List


def setup_logger(
        name: str,  # Název loggeru (typicky název aplikace)
        level: str = "INFO",  # Úroveň logování: DEBUG, INFO, WARNING, ERROR
        targets: List[str] = None,  # Kam logovat: ["console", "file"]
        log_file: str = None,  # Cesta k log souboru
        max_bytes: int = 10485760,  # Maximální velikost souboru (10 MB default)
        backup_count: int = 3  # Kolik starých log souborů ponechat
) -> logging.Logger:
    """
    Vytvoří a nakonfiguruje logger podle zadaných parametrů.

    Args:
        name: Název loggeru (zobrazí se v log záznamech)
        level: Úroveň logování - co se bude logovat
               DEBUG = všechno (hodně detailů, použij při vývoji)
               INFO = normální provoz (události, změny stavu)
               WARNING = varování (něco nefunguje ideálně, ale běží to)
               ERROR = chyby (něco selhalo)
        targets: Seznam kam logovat - ["console"] nebo ["file"] nebo oboje
        log_file: Cesta k souboru pro logy (pokud je "file" v targets)
        max_bytes: Když log soubor dosáhne této velikosti, vytvoří se nový
        backup_count: Kolik starých logů ponechat (wifi.log.1, wifi.log.2, ...)

    Returns:
        Nakonfigurovaný logger připravený k použití
    """

    # Pokud targets není zadán, použijeme výchozí konzoli
    if targets is None:
        targets = ["console"]

    # Vytvoříme logger s daným jménem
    logger = logging.getLogger(name)

    # Nastavíme úroveň logování (převedeme text na konstantu)
    # Např. "INFO" → logging.INFO
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Odstraníme staré handlery (pokud logger už existoval)
    # Handler = "výstup" kam se logy posílají (konzole, soubor, síť...)
    logger.handlers.clear()

    # Formát log zprávy - jak bude vypadat každý řádek
    # %(asctime)s = timestamp (čas)
    # %(name)s = název loggeru
    # %(levelname)s = úroveň (INFO, ERROR, ...)
    # %(message)s = samotná zpráva
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"  # Formát času: 2025-01-15 14:30:45
    )

    # Přidáme konzolový výstup (pokud je požadován)
    if "console" in targets:
        # StreamHandler = handler pro výstup do "proudu" (stream)
        # sys.stdout = standardní výstup (terminál)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Přidáme souborový výstup (pokud je požadován)
    if "file" in targets and log_file:
        # Vytvoříme cestu k souboru pomocí pathlib
        log_path = Path(log_file)

        # Vytvoříme složku pro logy, pokud neexistuje
        # parents=True = vytvoří i nadřazené složky
        # exist_ok=True = nepokládá chybu, pokud složka už existuje
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # RotatingFileHandler = handler který:
        # - zapisuje do souboru
        # - když soubor přeroste, přejmenuje ho na .1 a vytvoří nový
        # - udržuje jen N starých souborů (backup_count)
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,  # Maximální velikost v bytech
            backupCount=backup_count,  # Kolik starých souborů ponechat
            encoding="utf-8"  # Kódování (pro české znaky)
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Zabráníme propagaci do parent loggeru
    # (jinak by se zprávy logovaly 2x)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Získá existující logger podle jména.

    Použití:
        logger = get_logger("wifi-toggle")
        logger.info("Nějaká zpráva")

    Args:
        name: Název loggeru

    Returns:
        Logger instance
    """
    return logging.getLogger(name)