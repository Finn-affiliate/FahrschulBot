# Washington Driving School – Discord Bot

Ein vollständiger Discord-Bot für eine Roleplay-Fahrschule mit Theorie- und Praktischer Prüfung, PDF-Erstellung und Wochenberichten.

## Setup

### 1. Voraussetzungen

- Python 3.10 oder neuer
- pip

### 2. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3. config.py erstellen

Erstelle eine Datei `config.py` im selben Ordner wie `main.py`:

```python
BOT_TOKEN_FAHRSCHULE = "DEIN_BOT_TOKEN_HIER"
```

### 4. logo.png platzieren

Lege die Datei `logo.png` im selben Ordner wie `main.py` ab.

### 5. Bot starten

```bash
python main.py
```

---

## Dateistruktur

```
FahrschulBot/
├── main.py                  # Einstiegspunkt
├── database.py              # SQLite-Datenbankoperationen
├── pdf_generator.py         # PDF-Zeugnis-Erstellung
├── weekly_reports.py        # Wochenbericht-Logik
├── fragen.json              # 52 Theoriefragen
├── logo.png                 # Schullogo (selbst hinzufügen)
├── config.py                # Token (selbst erstellen, nicht committen!)
├── requirements.txt
├── README.md
└── cogs/
    ├── theorie.py           # Theorie-Freischaltung & Prüfung
    ├── praktisch.py         # Praktische Prüfung
    ├── statistik.py         # Statistik-Befehl
    ├── fragen.py            # Fragen-Verwaltung
    └── wochenbericht.py     # Automatische Wochenberichte
```

---

## Slash Commands

### Für Fahrlehrer

| Befehl | Beschreibung |
|--------|-------------|
| `/passwort erstellen` | Erstellt ein einmaliges Theorie-Passwort für einen Schüler |
| `/prüfung starten` | Startet eine praktische Prüfung |
| `/prüfung beenden` | Beendet eine laufende Prüfung mit Ergebnis |
| `/statistik` | Zeigt die Gesamtstatistik |

### Für Schüler

| Befehl | Beschreibung |
|--------|-------------|
| `/theorie` | Startet die Theorieprüfung mit Passwort |

### Für Admins

| Befehl | Beschreibung |
|--------|-------------|
| `/frage hinzufügen` | Fügt eine neue Theoriefrage hinzu |
| `/frage löschen` | Löscht eine Frage per Nummer |
| `/fragen anzeigen` | Zeigt alle Fragen an |
| `/wochenbericht` | Löst den Wochenbericht sofort aus |
| `/statistik` | Zeigt die Gesamtstatistik |

---

## Ablauf

### Theorieprüfung

1. Fahrlehrer: `/passwort erstellen @Schüler`
2. Schüler erhält Passwort per DM
3. Schüler: `/theorie [passwort]`
4. 20 zufällige Fragen aus 52 → Buttons A/B/C/D
5. Mindestens 18/20 richtig → Bestanden → Rolle "Theorieprüfung" erhalten

### Praktische Prüfung

1. Fahrlehrer: `/prüfung starten @Schüler` → Kategorie wählen → Daten eingeben
2. Fahrlehrer: `/prüfung beenden` → Ergebnis, Name, Unterschrift eingeben
3. Bei Bestehen: PDF per DM an Schüler + Eintrag im Archiv-Kanal
4. Bei Nicht-Bestehen: DM-Benachrichtigung

### Wochenbericht

- Automatisch jeden Sonntag um 23:59 UTC
- Manuell per `/wochenbericht` (nur Admin)
- Kanal `bericht-[fahrlehrername]` wird automatisch erstellt

---

## Discord-Server Konfiguration

| Einstellung | ID |
|-------------|-----|
| Server | 1419390036419411998 |
| Archiv-Kanal | 1473742086171001067 |
| Wochenbericht-Kategorie | 1419390038038544610 |
| Fahrlehrer-Rolle | 1419390036419412005 |
| Admin-Rolle | 1419390036511559709 |
| Theorieprüfung-Rolle | 1467931970158985395 |

---

## Bot-Berechtigungen

Der Bot benötigt folgende Berechtigungen:

- `Send Messages`
- `Embed Links`
- `Attach Files`
- `Manage Roles`
- `Manage Channels`
- `Read Message History`
- `Use Application Commands`
- `Send Messages in Threads`

Privileged Intents (Developer Portal):
- `Server Members Intent`
- `Message Content Intent`
