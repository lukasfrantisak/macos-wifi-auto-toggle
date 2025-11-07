
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jednoduchý launcher pro Wi-Fi Auto Toggle.

Použití:
    python3 run.py          # Spustí aplikaci
    python3 run.py --help   # Zobrazí nápovědu (budoucí)
"""

import sys
from pathlib import Path

# Přidáme src/ do Python path, aby mohly importy fungovat
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Importujeme a spustíme main
from main import main

if __name__ == "__main__":
    main()