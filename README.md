# 💻 macOS Wi-Fi Auto Toggle

> 🧠 **Autor:** Lukáš Františák  
> 🎯 **Cíl:** Automatizovat přepínání mezi **Wi-Fi** a **10G Thunderbolt síťovou kartou QNAP** na MacBooku  
> a využít tento reálný problém jako osobní DevOps projekt pro učení automatizace, monitoringu a tvorby infrastruktury.

---

## 💡 Proč tento projekt vznikl

V práci používám **MacBook připojený k NASu** přes **externí 10G QNAP Thunderbolt síťovou kartu**.  
Přestože mám v macOS nastavenou prioritu rozhraní, systém stále často využívá **Wi-Fi** namísto rychlejšího kabelového připojení.

To vede ke snížení propustnosti a vyšším latencím při práci s NASem.  
Cílem je tedy vytvořit **chytrý Python skript**, který bude automaticky sledovat síťové rozhraní a přepínat Wi-Fi podle potřeby.

Současně chci tento projekt rozvíjet jako **studijní platformu pro DevOps** – naučit se na něm:
- práci s Gitem a GitHubem  
- logování a observabilitu (Prometheus + Grafana)  
- nasazování pomocí Docker Compose  
- CI/CD workflow s GitHub Actions  

---

## 🧰 Co skript aktuálně umí

✅ Sleduje všechna síťová rozhraní a rozpozná Thunderbolt kartu (`en10`)  
✅ Pokud je Thunderbolt připojen → **Wi-Fi se vypne**  
✅ Pokud se Thunderbolt odpojí → **Wi-Fi se automaticky zapne**  
✅ Posílá **macOS notifikace** při změnách  
✅ **Loguje vše** do konzole i souboru (s rotací)  
✅ Plně **konfigurovatelný** přes `config.yaml`  
✅ Modulární architektura (každá komponenta je samostatný modul)

---

## 📁 Struktura projektu

```bash
macos-wifi-auto-toggle/
├── config.yaml                 # Konfigurace (nastav si zde vše)
├── requirements.txt            # Python závislosti
├── run.py                      # Spouštěč (python3 run.py)
├── README.md
├── src/                        # Zdrojové kódy
│   ├── __init__.py
│   ├── main.py                 # Hlavní logika
│   ├── logger.py               # Logování
│   ├── network_detector.py     # Detekce Thunderbolt
│   ├── wifi_controller.py      # Ovládání Wi-Fi
│   └── notifier.py             # macOS notifikace
└── logs/                       # Logy (vytvoří se automaticky)
```

---

## 🚀 Instalace a spuštění

### 1️⃣ Naklonuj nebo stáhni projekt

```bash
cd ~/Dev
git clone <url-tvého-repo> macos-wifi-auto-toggle
cd macos-wifi-auto-toggle
```

### 2️⃣ Nainstaluj závislosti

```bash
pip3 install -r requirements.txt
```

### 3️⃣ (Volitelné) Nainstaluj terminal-notifier

Pro hezčí notifikace:
```bash
brew install terminal-notifier
```
*(Pokud ho nemáš, použije se fallback přes AppleScript — funguje také.)*

### 4️⃣ Uprav konfiguraci

Otevři `config.yaml` a zkontroluj/uprav:
- `network.thunderbolt_port_name` — název tvé Thunderbolt karty  
- `behavior.check_interval` — jak často kontrolovat (sekundy)  
- `logging.level` — DEBUG pro detailní výstup, INFO pro normální  

### 5️⃣ Spusť

```bash
python3 run.py
```

**Ukončení:** Ctrl + C

---

## ⚙️ Konfigurace (`config.yaml`)

```yaml
network:
  thunderbolt_port_name: "Thunderbolt Ethernet Slot 1"  # Tvá karta
  wifi_service_name: "Wi-Fi"

behavior:
  check_interval: 10             # Kontrolovat každých 10 s
  enforce_on_startup: true       # Vynucovat správný stav při startu
  enable_notifications: true     # Povolit notifikace
  notification_sound: "Submarine"

logging:
  level: "INFO"                  # DEBUG | INFO | WARNING | ERROR
  targets: ["console", "file"]
  file_path: "logs/wifi-toggle.log"
  max_file_size_mb: 10
  backup_count: 3
```

---

## 🔄 Logika skriptu

| Stav Thunderbolt | Akce |
|------------------|------|
| **Připojen**     | Wi-Fi se **vypne** |
| **Odpojen**      | Wi-Fi se **zapne** |
| **Změna**        | Pošle **notifikaci** |

---

## 🏗️ Architektura projektu

| Modul | Úloha |
|-------|-------|
| `logger.py` | Logování do konzole a souboru s rotací |
| `network_detector.py` | Detekce síťových rozhraní |
| `wifi_controller.py` | Zapínání/vypínání Wi-Fi |
| `notifier.py` | macOS notifikace |
| `main.py` | Hlavní smyčka a rozhodovací logika |

---

## 🧭 Plány do budoucna

### 🔹 Krátkodobé
- ✅ YAML konfigurace  
- ✅ Modulární architektura  
- ✅ Log rotace  
- ✅ macOS notifikace  
- ⬜ Automatické spuštění přes LaunchAgent  
- ⬜ Debug/dry-run režim  
- ⬜ Detekce SSID kancelářské sítě ("away mode")  

### 🔹 Střednědobé
- ⬜ Prometheus endpoint  
- ⬜ Docker Compose stack (Prometheus + Grafana)  
- ⬜ Grafana dashboard  

### 🔹 Dlouhodobé
- ⬜ CI/CD s GitHub Actions  
- ⬜ Homebrew tap pro instalaci  
- ⬜ CLI nástroj (`tbwifi status`, `tbwifi toggle`)  
- ⬜ Integrace s Grafana Loki  
- ⬜ Distribuce mezi kolegy  

---

## 🐛 Troubleshooting

**⚠️ Skript hlásí “Nelze zjistit stav Wi-Fi”**
- Zkontroluj, že máš službu pojmenovanou přesně `Wi-Fi`
- Nebo změň `wifi_service_name` v `config.yaml`

**⚠️ Thunderbolt karta se nedetekuje**
```bash
networksetup -listallhardwareports
```
Zkopíruj přesný název karty do `thunderbolt_port_name`.

**⚠️ Notifikace nefungují**
```bash
brew install terminal-notifier
```
Pokud není nainstalováno, použije se AppleScript fallback.

**⚠️ Chci více detailů v logu**
- V `config.yaml` nastav:  
  ```yaml
  logging:
    level: "DEBUG"
  ```

---

## 🧠 Co jsem se na projektu naučil

- Práci s YAML konfigurací v Pythonu  
- Modulární architekturu (separation of concerns)  
- Logování s rotací souborů  
- Práci s `subprocess` a macOS CLI  
- Type hints a dataclasses  
- Použití Enum pro definici stavů  
- Signal handling (graceful shutdown)

---

## 📜 Licence

MIT – volně použitelné a upravitelné.

---

## 🤝 Přispívání

Projekt slouží primárně jako **osobní learning sandbox**,  
ale návrhy a pull requesty jsou vítány!

---

> _Projekt aktivně vyvíjen — slouží jako osobní DevOps sandbox pro praktické učení automatizace a monitoringu._
