# Změny v projektu

Všechny významné změny tohoto projektu jsou zaznamenány v tomto souboru.  
Formát vychází z [Keep a Changelog](https://keepachangelog.com/) a projekt dodržuje zásady [sémantického verzování](https://semver.org/).

## [0.1.1] – 8. listopadu 2025

Odhadovaný typ vydání: **Patch** (opravy chyb a drobná vylepšení).

### Změněno
- Zesílena detekce kabelového připojení pro vyšší spolehlivost: vyžaduje aktivní linku a ne-link-lokální IPv4, ignoruje pseudo-rozhraní Thunderbolt a používá seznam povolených pro adaptér QNAP. ([0095834](https://github.com/lukasfrantisak/macos-wifi-auto-toggle/commit/0095834))
- Aktualizován README – nové cesty a rozšířené plány do budoucna. ([e940e74](https://github.com/lukasfrantisak/macos-wifi-auto-toggle/commit/e940e74))

### Opraveno
- Obecný úklid: odstraněn `.DS_Store` z repozitáře. ([e8638a9](https://github.com/lukasfrantisak/macos-wifi-auto-toggle/commit/e8638a9))

## [0.1.0] – 7. listopadu 2025

První veřejné vydání.

### Přidáno
- Funkční **macOS Wi-Fi Auto Toggle**:
  - Detekce síťového rozhraní Thunderbolt (např. `en10`).
  - Vypne Wi-Fi při připojení Thunderboltu, zapne při odpojení.
  - macOS notifikace při změně stavu.
  - Komplexní logování do konzole a rotujícího souboru.
  - Konfigurace přes `config.yaml`.
  - Modulární architektura s oddělenými komponentami pro detekci, ovládání Wi-Fi, notifikace a logování. ([2151a63](https://github.com/lukasfrantisak/macos-wifi-auto-toggle/commit/2151a63))

### Poznámky
- Interní zálohovací commit před refaktoringem byl vynechán, protože není určen pro uživatele. ([81c24a1](https://github.com/lukasfrantisak/macos-wifi-auto-toggle/commit/81c24a1))

---

[0.1.1]: https://github.com/lukasfrantisak/macos-wifi-auto-toggle/compare/0.1.0...0.1.1  
[0.1.0]: https://github.com/lukasfrantisak/macos-wifi-auto-toggle/tree/0.1.0
