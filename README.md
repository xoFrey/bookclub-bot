# 📚 Buchclub Discord Bot – Anleitung

## Dateien
```
buchclub-bot/
├── bot.py
├── database.py
├── cogs/
│   ├── panel.py
│   └── bewertung.py
├── requirements.txt
└── .env.example
```

---

## 1. Discord Bot erstellen
1. Gehe zu https://discord.com/developers/applications
2. „New Application" → Name vergeben
3. Links auf „Bot" → „Add Bot"
4. Token kopieren (brauchst du gleich)
5. Unter „Privileged Gateway Intents": **Message Content Intent** aktivieren
6. Bot einladen: OAuth2 → URL Generator
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Administrator`
   - Link öffnen und Bot zum Server hinzufügen

---

## 2. Render – PostgreSQL Datenbank
1. Render Dashboard → „New" → „PostgreSQL"
2. Name vergeben, Region wählen (Frankfurt empfohlen)
3. Erstellen → „External Database URL" kopieren

---

## 3. Render – Web Service (Bot)
1. GitHub Repo erstellen und alle Dateien hochladen
2. Render Dashboard → „New" → „Web Service"
3. GitHub Repo verbinden
4. Einstellungen:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
   - **Environment:** Python 3
5. Environment Variables hinzufügen:
   - `DISCORD_TOKEN` = dein Bot-Token
   - `DATABASE_URL` = deine Render PostgreSQL URL (External)
   - `PORT` = `8080`
6. Deploy starten

---

## 4. UptimeRobot (damit der Bot nicht schläft)
1. https://uptimerobot.com → Account erstellen
2. „Add New Monitor"
   - Monitor Type: HTTP(s)
   - URL: deine Render URL (z.B. `https://buchclub-bot.onrender.com`)
   - Interval: 5 Minuten
3. Speichern – fertig!

---

## 5. Bot benutzen
- Im Discord-Server: `/panel` eingeben (nur Admins)
- Das Panel erscheint mit 3 Buttons:
  - **📚 Buch Eintragen** – Genre wählen, dann Formular ausfüllen
  - **📊 Statistiken** – Genre-Häufigkeit, Bücherzahl, Gesamtseiten
  - **📖 Bücherliste** – Alle Bücher sortiert nach Startdatum

---

## Bewertungssystem
- Jeden Tag um **16:00 Uhr (Berlin)** prüft der Bot ob ein Buch heute endet
- Wenn ja: Bewertungs-Embed erscheint mit Dropdown (⭐ 1.0 – ⭐⭐⭐⭐⭐ 5.0, halbe Sterne möglich)
- Nach **24 Stunden**: Ergebnis-Embed mit Durchschnitt wird gepostet
- Bewertungskanal = erster Textkanal, in den der Bot schreiben kann

---

## Tipp: Bewertungskanal festlegen
Wenn du einen bestimmten Kanal für Bewertungen willst, öffne `cogs/bewertung.py`
und ersetze in `bewertung_starten()` die Kanalsuche durch:
```python
kanal = guild.get_channel(DEINE_KANAL_ID)
```
