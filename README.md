# macOS Wi-Fi Auto Toggle

> 🧠 Autor: **Lukáš Františák**  
> 🎯 Cíl: Automatizovat přepínání mezi **Wi-Fi** a **10G Thunderbolt síťovou kartou QNAP** na MacBooku  
> a využít tento reálný problém jako osobní DevOps projekt pro učení automatizace, monitoringu a tvorby infrastruktury.

---

## 💡 Proč tento projekt vznikl

V práci používám **MacBook připojený k NASu** přes **externí 10G QNAP Thunderbolt síťovou kartu**.  
Přestože mám v macOS nastavenou prioritu rozhraní, systém stále často využívá **Wi-Fi** namísto rychlejšího kabelového připojení.

To vede ke snížení propustnosti a vyšším latencím při práci s NASem.  
Cílem je tedy vytvořit **chytrý Python skript**, který bude automaticky sledovat síťové rozhraní a přepínat Wi-Fi podle potřeby.

Současně chci tento projekt rozvíjet jako **studijní platformu** pro DevOps – naučit se na něm:
- práci s Gitem a GitHubem,  
- logování a observabilitu (Prometheus + Grafana),  
- nasazování pomocí Docker Compose,  
- a CI/CD workflow s GitHub Actions.

---

## 🧰 Co skript aktuálně umí

✅ Sleduje všechna síťová rozhraní (`en*`) a rozpozná, kdy je aktivní „drát“ (Thunderbolt/Ethernet).  
✅ Pokud je drát aktivní → **Wi-Fi se vypne**.  
✅ Pokud se drát odpojí → **Wi-Fi se automaticky zapne**.  
✅ Umí rozpoznat, zda jsem v kanceláři podle SSID (`Marketing 5.0GHz`).  
✅ Mimo kancelář přejde do „spánkového režimu“ (šetří výkon).  
✅ Lze ho spustit automaticky po startu systému pomocí **LaunchDaemona** nebo **LaunchAgenta**.  

---

## ⚙️ Aktuální stav projektu

Projekt je v **rané, ale funkční fázi**.  
Základní logika přepínání Wi-Fi ↔ Thunderbolt funguje spolehlivě.  
Kód je napsán v Pythonu s důrazem na čitelnost, komentáře a možnost dalšího rozšiřování.

V této fázi se projekt používá **na lokálním MacBooku** bez externích závislostí.  
Následující vývoj se zaměří na přidání observability, logování a monitoringu.

---

## 🚀 Jak skript spustit

1️⃣ Vytvoř složku pro projekt (pokud ji ještě nemáš):
```bash
mkdir -p ~/Dev/macos-wifi-auto-toggle
```

2️⃣ Ulož do ní soubory:
- `monitor_thunderbolt_wifi.py`
- `README.md`

3️⃣ Spusť skript ručně v terminálu:
```bash
sudo /usr/bin/python3 ~/Dev/macos-wifi-auto-toggle/monitor_thunderbolt_wifi.py
```

4️⃣ (Volitelné) Spuštění po startu systému:  
Vytvoř LaunchDaemon nebo LaunchAgent podle instrukcí v kódu (soubor `.plist`).

---

## 🔄 Jak funguje logika

| Stav | Akce |
|------|------|
| Thunderbolt aktivní | Wi-Fi se vypne |
| Thunderbolt odpojen | Wi-Fi se zapne |
| Jsem v kanceláři (SSID `Marketing 5.0GHz`) | Skript zůstává aktivní |
| Jsem mimo kancelář | Skript přejde do režimu spánku (60 s) |

---

## 🧭 Plány do budoucna

### 🔹 Krátkodobé cíle
- Přidat **notifikace** do Notification Center při přepnutí sítě.  
- Doplnit **rotující logování** (`logging` + `RotatingFileHandler`).  
- Umožnit zapnutí debug režimu pomocí argumentu (`--debug`).  
- Přidat konfiguraci přes `.env` nebo `config.yml`.  

### 🔹 Střednědobé cíle
- Přidat **/metrics endpoint** (Prometheus format).  
- Vytvořit **Docker Compose stack** s Prometheem a Grafanou.  
- Zaznamenávat stav a změny do **Prometheus metrik** (`tbwifi_*`).  
- Vytvořit **dashboard v Grafaně** pro vizualizaci přepínání, uptime a chyb.  

### 🔹 Dlouhodobé cíle
- Přidat **GitHub Actions workflow** pro lintování a testy.  
- Nasazení do balíčku (`.pkg` nebo Homebrew tap).  
- Verzi pro **distribuci v kanceláři mezi kolegy** – auto-updaty, centrální monitoring.  
- Integrace s **Grafana Loki** pro logování.  
- Vytvoření **CLI nástroje** (`tbwifi` příkaz).  
- Možnost zasílat stav do **Slacku nebo e-mailu** při chybě.  

---

## 🧠 Co si chci na tomto projektu vyzkoušet

- Prakticky pochopit DevOps cyklus: **build → monitor → iterate**.  
- Psaní spolehlivých skriptů s idempotentním chováním.  
- Práci s `launchd` a službami na macOS.  
- Integraci Pythonu s nástroji pro observabilitu (Prometheus, Grafana).  
- Vytvoření přehledného `docker-compose` stacku.  
- Základy CI/CD a verzování pomocí GitHub Actions.  

---

## 📜 Licence

MIT – volně použitelné a upravitelné.

---

> _Projekt v rané fázi – základní automatické přepínání funguje.  
> Slouží jako můj osobní sandbox pro zkoušení DevOps principů na reálném příkladu._
