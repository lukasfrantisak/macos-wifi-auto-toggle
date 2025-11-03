# macOS Thunderbolt Wi-Fi Toggle (DevOps Mini Projekt)

> 🧠 Autor: **Lukáš Františák**  
> 🎯 Cíl: Automatizovat přepínání mezi **Wi-Fi** a **10G Thunderbolt síťovou kartou QNAP** na MacBooku
> a postupně se na tom naučit DevOps přístup – automatizaci, monitoring a práci s Dockerem.

---

## 💡 Proč tento projekt vznikl

Na MacBooku používám externí **10G síťovou kartu QNAP připojenou přes Thunderbolt**, kterou využívám pro vysokorychlostní připojení k NASu.  
macOS ale i při zapojení karty často používá připojení přes **Wi-Fi**, což snižuje propustnost a stabilitu spojení.

Cílem projektu je, aby se:
- při připojení Thunderbolt karty **Wi-Fi automaticky vypnula**,
- a při jejím odpojení **Wi-Fi zase zapnula zpět**.

Zároveň chci, aby skript rozpoznal, že se nacházím v kanceláři (např. podle SSID `Marketing 5.0GHz`)  
a mimo kancelář zbytečně neběžel – šetřil výkon i energii.

---

## 🧰 Co skript aktuálně umí

- Sleduje všechna síťová rozhraní (`en*`) a pozná, kdy je aktivní drát (Thunderbolt/Ethernet).  
- Při aktivním drátu **vypne Wi-Fi**, po odpojení **Wi-Fi znovu zapne**.  
- Pozná, jestli jsem v kanceláři (SSID `Marketing 5.0GHz`).  
- Mimo kancelář přejde do „spánkového“ režimu (idle).  
- Umí běžet i jako **LaunchDaemon** – automaticky po startu systému.  
- Zapisuje logy do konzole s informacemi o stavech připojení.

---

## ⚙️ Stav projektu

Projekt je v **rané fázi vývoje**.  
V tuto chvíli funguje základní logika přepínání Wi-Fi ↔ Thunderbolt.  
Další části jako **Prometheus / Grafana**, **notifikace** nebo **CI/CD** zatím nejsou implementovány –  
jsou v plánu jako další krok v rámci mého učení DevOps nástrojů.

---

## 🚀 Jak skript spustit

1️⃣ Vytvoř složku pro skript:
```bash
mkdir -p ~/Documents/Scripts
```

2️⃣ Ulož soubor `monitor_thunderbolt_wifi.py` do této složky.

3️⃣ Spusť ho ručně v terminálu:
```bash
sudo /usr/bin/python3 ~/Documents/Scripts/monitor_thunderbolt_wifi.py
```

Skript vypíše informace o aktuálních rozhraních a začne hlídat stav připojení.

4️⃣ (Volitelné) Spuštění automaticky po startu systému  
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

## 📋 Plány do budoucna

- Přidat `/metrics` endpoint (Prometheus format)
- Vytvořit Docker Compose stack s Prometheem a Grafanou
- Přidat systémové notifikace (macOS Notification Center)
- Logování do souboru + rotace
- Unit testy a GitHub CI linting
- Možnost distribuce skriptu mezi kolegy

---

## 🧠 Co si na tom chci vyzkoušet

- Základy DevOps přístupu (observability, logging, monitoring)  
- Integraci Prometheus / Grafana  
- Práci s `launchd` (macOS služby)  
- Docker Compose workflow  
- Automatizaci jednoduchých systémových úloh pomocí Pythonu

---

## 🧭 Licence

MIT – volně použitelné a upravitelné.

---

> _Projekt v rané fázi – funguje základní automatické přepínání Wi-Fi ↔ Thunderbolt,  
> postupně na tom stavím znalosti z DevOps._
