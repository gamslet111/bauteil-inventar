---
projekt: bauteil-inventar
typ: anleitung
aktualisiert: 2026-10-20
tags: [projekt, elektronik, inventar, anleitung]
---
# Bauteil-Inventar: Anleitung

Diese Anleitung beschreibt die tägliche Benutzung. Einrichtung und technische Details stehen in [[README]], der Projektstand in [[Stand]].

> **Kurz gesagt:** Kamera oder Bild wählen → Bauteil fotografieren → Vorschlag prüfen → Anzahl und Lagerort eintragen → speichern. Das Programm nimmt **Standbilder** auf, keine Videos. Die Bilder dienen nur der Erkennung und werden **nicht gespeichert**.

## Kurzablauf

1. Kamera verbinden (oder **Bild laden…**).
2. Bauteil ins Bild halten, scharf stellen.
3. **Foto aufnehmen** (Leertaste) bzw. **Bild laden…**.
4. Vorschlag in den Feldern prüfen und korrigieren.
5. **Anzahl** und optional **Lagerort** eintragen.
6. **Speichern** (Strg+S).

## 1. Was das Programm macht

Das Programm erfasst elektronische Bauteile mit einem Foto. Ein Vision-Modell schlägt Kategorie, Bezeichnung, Wert, Gehäuse, Eigenschaften und Aufdruck vor. Du prüfst den Vorschlag, ergänzt **Anzahl** und **Lagerort** und speicherst.

Daraus entstehen automatisch:

- `inventar.json` – der eigentliche Datenbestand
- [[Bestand]] – Übersicht nach Kategorie für Obsidian
- `inventar.csv` – Tabelle für Excel

Das aufgenommene oder geladene Bild wird **nicht gespeichert**: es bleibt nur im Arbeitsspeicher und wird nach der Erkennung verworfen. Im Projekt liegen daher keine Bilddateien.

Die Erkennung ist ein **Vorschlag**, kein Messgerät. Besonders bei kleinen SMD-Bauteilen, Farbcodes und schlecht lesbaren Aufdrucken bitte selbst prüfen.

## 2. Einmalig einrichten

### 2.1 Pakete installieren

```powershell
cd "C:\Users\kilia\Documents\Obsidian Vault\20-Projekte\Bauteil-Inventar"
python -m pip install -r requirements.txt
```

### 2.2 DeepSeek-Key setzen

Der Key wird **nicht** im Projekt und **nicht** im Vault gespeichert. Einmalig für dein Windows-Konto:

```powershell
setx DEEPSEEK_API_KEY "sk-..."
```

Danach ein **neues** PowerShell-Fenster öffnen. Nur für die aktuelle Sitzung:

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
```

### 2.3 Starten

```powershell
python inventar.py
```

Oder `starten.bat` doppelklicken. Die Batch-Datei liest dieselbe Umgebungsvariable.

**Ohne Key** startet das Programm trotzdem. Dann werden keine Vorschläge gemacht; du füllst alle Felder selbst aus. Ein Foto wird nicht dauerhaft gespeichert.

### 2.4 Anthropic statt DeepSeek (optional)

```powershell
python -m pip install anthropic
$env:INVENTAR_ANBIETER = "anthropic"
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python inventar.py
```

Ohne `INVENTAR_ANBIETER` gilt: `DEEPSEEK_API_KEY` hat Vorrang, sonst `ANTHROPIC_API_KEY`.

## 3. Die Oberfläche

| Bereich | Bedeutung |
|---|---|
| Großes Bild links | Live-Vorschau der Kamera oder das geladene Standbild |
| **Kamera** | Kamera-Index (`0`, `1`, `2` …) oder Stream-URL |
| **Verbinden** | Kamera mit der eingegebenen Quelle öffnen |
| **Foto aufnehmen** | Aktuelles Kamerabild aufnehmen und erkennen lassen (nur im Arbeitsspeicher) |
| **Bild laden…** | Vorhandene Bilddatei öffnen |
| **Felder leeren** | Formular zurücksetzen; Live-Vorschau läuft wieder |
| **Speichern** | Eintrag in den Bestand übernehmen |
| Formular rechts | Vorschlag prüfen und ergänzen |
| Statuszeile unten | Meldungen, Kamera-Status, Konfidenz |

## 4. Ein Bauteil aufnehmen (Standardablauf)

1. **Kamera verbinden.** Standard ist `0`. Bei einer USB-Webcam `1`, `2`, `3` … probieren und **Verbinden** drücken.
2. **Bauteil ins Bild halten.** Aufdruck zur Kamera drehen, Abstand so wählen, dass das Bauteil das Bild gut ausfüllt.
3. **Foto aufnehmen** (Leertaste, wenn die Vorschau den Fokus hat) oder den Knopf drücken.
4. **Warten.** Das Bild wird für die Erkennung vorbereitet; die Statuszeile zeigt „Erkenne Bauteil …“. Danach steht dort die Konfidenz, z. B. „Vorschlag übernommen (Konfidenz 82 %)“.
5. **Vorschlag prüfen.** Kategorie, Bezeichnung, Wert, Gehäuse, Eigenschaften und Aufdruck korrigieren.
6. **Anzahl eintragen** (mindestens 1) und optional den **Lagerort**, z. B. `Kasten B2, Fach 3`.
7. **Speichern** (Strg+S).

### Bereits vorhandenes Bauteil

Das Programm vergleicht **Bezeichnung + Wert + Gehäuse** (Groß-/Kleinschreibung egal). Gibt es den Eintrag schon, fragt es:

> „… ist schon im Bestand (12 Stück). 3 Stück dazuzählen?“

- **Ja:** Anzahl wird addiert, der Lagerort aktualisiert, das Änderungsdatum gesetzt.
- **Nein:** Es wird ein neuer Eintrag angelegt.

Nach dem Speichern werden die Felder geleert und die Live-Vorschau läuft wieder.

## 5. Gute Fotos

- **Licht:** gleichmäßig und diffus; keine harten Schatten oder Blitzreflexe auf glänzenden Bauteilen.
- **Hintergrund:** einfarbig und ruhig, am besten weiß oder grau. Kein unruhiger Tisch.
- **Fokus:** auf den Aufdruck scharf stellen. Bei kleinen ICs oder SMD-Widerständen lieber ein Handyfoto mit Makro verwenden und über **Bild laden…** einlesen.
- **Bildausschnitt:** ein Bauteil pro Foto. Mehrere gleiche Bauteile nur, wenn sie vollständig und klar sichtbar sind.
- **Aufdruck:** frontal und lesbar; Beschriftung nicht verdecken.
- **Ruhig halten:** kurz warten, bis die Vorschau scharf ist, dann auslösen.

## 6. Bilddatei statt Kamera

Über **Bild laden…** (Strg+O) kannst du vorhandene Fotos verwenden:

- JPG, PNG, WebP, BMP, TIFF
- **HEIC/HEIF** von iPhone (über `pillow-heif`)

Das Programm dreht Hochformatfotos anhand der EXIF-Daten richtig und verkleinert sehr große Handyfotos auf maximal 2000 px Kantenlänge. Das Bild bleibt nur im Arbeitsspeicher und wird **nicht gespeichert** – es dient ausschließlich der Erkennung.

Ein geladenes Standbild **pausiert die Live-Vorschau**, damit es nicht sofort überschrieben wird. **Felder leeren**, **Speichern** oder **Verbinden** schaltet die Kamera wieder live.

### iPhone-Fotos auf den PC bringen

- Per USB-Kabel: iPhone entsperren, Vertrauen bestätigen, Fotos über den Windows-Explorer kopieren.
- Oder über iCloud/OneDrive auf den PC synchronisieren.
- Dann im Programm **Bild laden…** verwenden.

Unter **Windows 10** wird das iPhone nicht ohne Zusatz-App als normale USB-Kamera erkannt. Dafür braucht es eine virtuelle-Kamera-App (z. B. Camo, Iriun, EpocCam) oder den DroidCam-Weg unten.

## 7. Externe Kameras

### 7.1 USB-Webcam

1. Webcam anstecken.
2. Im Feld **Kamera** `1`, `2`, `3` … probieren.
3. **Verbinden** drücken.

Die eingebaute Kamera ist meist `0`, die USB-Webcam oft `1`. Wenn der Index nicht stimmt, erscheint „Keine Kamera …“; einfach den nächsten versuchen.

### 7.2 DroidCam (iPhone oder Android)

DroidCam gibt es für iPhone und Android. Es gibt zwei Wege:

#### A) Direkt als Netzwerk-Kamera (ohne PC-Client)

1. DroidCam-App auf dem Handy installieren und öffnen.
2. Handy und PC ins **gleiche WLAN** bringen.
3. In der DroidCam-App die angezeigte Adresse ablesen, meist `192.168.x.x:4747`.
4. Im Feld **Kamera** eintragen:

   ```text
   http://192.168.x.x:4747/video
   ```

5. **Verbinden** drücken.

Wenn kein Bild kommt, diese Varianten probieren:

```text
http://192.168.x.x:4747/mjpegfeed
http://192.168.x.x:4747/mjpegfeed?1280x720
```

#### B) DroidCam als virtuelle Windows-Kamera

1. **DroidCam Client für Windows** von [dev47apps.com](https://www.dev47apps.com/droidcam/windows/) installieren.
2. DroidCam-App am Handy starten.
3. Im PC-Client per WLAN verbinden (IP und Port eintragen) oder USB verwenden.
4. Erst wenn im DroidCam-Client das Bild läuft, im Bauteil-Inventar verbinden.
5. Im Feld **Kamera** die Indizes `1`, `2`, `3`, `4` probieren. DroidCam erscheint meist als „DroidCam Source“. Der Index lässt sich auch direkt eintippen, z. B. `5`.

#### DroidCam-Hinweise

- DroidCam bedient oft nur **einen Client** gleichzeitig. Wenn der PC-Client läuft, funktioniert die direkte URL möglicherweise nicht – umgekehrt genauso.
- Handy entsperrt lassen und DroidCam im Vordergrund halten.
- Die kostenlose Version liefert 640×480. Für kleine Aufdrucke ist das knapp; HD gibt es in der Pro-Version.
- USB am iPhone kann iTunes/Apple-Gerätetreiber brauchen und ist unter Windows 10 launischer als WLAN.
- Windows-Firewall für Python freigeben, wenn der Netzwerk-Stream nicht ankommt.
- Kein Gastnetz mit Client-Isolation verwenden.

### 7.3 iPhone ohne DroidCam

- **Virtuelle Kamera-App** (Camo, Iriun, EpocCam, DroidCam) installieren, am PC starten und deren Kamera-Index im Feld **Kamera** eintragen.
- Oder Fotos mit dem iPhone machen und über **Bild laden…** einlesen. Für Makroaufnahmen kleiner Bauteile ist das oft die schärfste Lösung.

### 7.4 Andere Netzwerk-Kameras

Das Feld **Kamera** akzeptiert auch andere MJPEG- oder RTSP-URLs, z. B. von einer IP-Kamera:

```text
http://192.168.1.50:8080/video
rtsp://192.168.1.50:554/stream
```

## 8. Die Felder

| Feld | Bedeutung | Beispiel |
|---|---|---|
| Kategorie | Auswahlliste; Unbekanntes → `Sonstiges` | `Widerstand` |
| Bezeichnung | Kurzer Name, **Pflichtfeld** | `Widerstand 10 kΩ` |
| Wert / Typ | elektrischer Wert oder Typ | `10 kΩ`, `100 nF`, `NE555` |
| Gehäuse | Bauform | `0207 bedrahtet`, `0603`, `TO-220`, `DIP-8` |
| Eigenschaften | weitere Merkmale, **mit Semikolon getrennt** | `1 %; 0,25 W; 50 V` |
| Aufdruck | lesbarer Aufdruck oder Teilenummer | `10K`, `NE555P` |
| Anzahl | Stückzahl, mindestens 1 | `25` |
| Lagerort | wo das Bauteil liegt | `Kasten B2, Fach 3` |

**Wichtig bei Eigenschaften:** Semikolon verwenden, **kein Komma**. Das Dezimalkomma in `0,25 W` bleibt sonst nicht erhalten. Richtig ist:

```text
1 %; 0,25 W
```

Falsch wäre:

```text
1 %, 0,25 W
```

## 9. Speichern und Dateien

| Datei | Inhalt | Bearbeiten? |
|---|---|---|
| `inventar.json` | Datenbestand, Quelle für alles andere | nur über das Programm |
| [[Bestand]] | Übersicht nach Kategorie | nein, wird neu erzeugt |
| `inventar.csv` | Tabelle für Excel, Trenner `;` | nein, wird neu erzeugt |
| `Fotos/` | nur aus älteren Versionen; wird nicht mehr beschrieben | nicht löschen, solange alte Einträge darauf verweisen |

Neue Fotos werden **nicht** abgelegt. Nur der Ordner `Fotos/` aus früheren Versionen bleibt bestehen; die dortigen Bilder werden in [[Bestand]] weiterhin verlinkt.

`Bestand.md` und `inventar.csv` werden bei jedem Speichern neu geschrieben. Wenn `inventar.csv` gerade in Excel geöffnet ist, kann das Speichern fehlschlagen – Excel vorher schließen.

**Sicherung:** Kopiere `inventar.json` regelmäßig an einen anderen Ort – darin steht der komplette Bestand. Wenn alte Einträge auf `Fotos/` verweisen, den Ordner mitkopieren.

## 10. Tastenkürzel

| Taste | Wirkung |
|---|---|
| Leertaste | Foto aufnehmen (wenn die Videovorschau den Fokus hat) |
| Strg+O | Bilddatei laden |
| Strg+S | Eintrag speichern |
| Eingabetaste im Kamera-Feld | Verbinden |

Damit die Leertaste funktioniert, einmal auf die Videovorschau klicken. Alternativ den Knopf **Foto aufnehmen** verwenden.

## 11. Kommandozeile und Umgebungsvariablen

```powershell
python inventar.py                     # Kamera 0
python inventar.py --kamera 1          # Kamera 1 (z. B. USB-Webcam)
python inventar.py --quelle "http://192.168.1.50:4747/video"
python inventar.py --nur-md            # nur Bestand.md/CSV neu erzeugen
```

`--quelle` nimmt einen Index oder eine URL und hat Vorrang vor `--kamera`.

| Variable | Wirkung |
|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek-Key (Standard-Anbieter) |
| `ANTHROPIC_API_KEY` | Anthropic-Key (Alternative) |
| `INVENTAR_ANBIETER` | `deepseek` oder `anthropic` erzwingen |
| `INVENTAR_MODELL` | anderes Modell, z. B. `deepseek-flash` |

## 12. Probleme und Lösungen

| Meldung / Problem | Lösung |
|---|---|
| „Keine Kamera unter ‚0‘“ | Anderen Index probieren (`1`, `2`, `3` …), andere Kamera-App schließen, bei DroidCam zuerst den Client verbinden |
| „Die Kamera liefert noch kein Bild“ | Ein bis zwei Sekunden warten und erneut aufnehmen; **Verbinden** erneut drücken |
| „Bild aufgenommen. Kein API-Key“ | `DEEPSEEK_API_KEY` setzen und ein **neues** Terminal öffnen; ohne Key Felder manuell ausfüllen |
| „HTTP 401“ oder „Authentication Fails“ | Key falsch, abgelaufen oder mit Leerzeichen kopiert; neu setzen |
| „DeepSeek nicht erreichbar“ | Internetverbindung, Firewall oder Proxy prüfen |
| „Erkennung fehlgeschlagen“ | Modell/Anbieter prüfen; Felder lassen sich immer manuell ausfüllen |
| HEIC wird nicht gelesen | `python -m pip install pillow-heif`; alternativ Foto als JPG exportieren |
| „Speichern fehlgeschlagen“ | `inventar.csv` in Excel geschlossen? Schreibrechte im Projektordner prüfen |
| Kamera getrennt | **Verbinden** erneut drücken oder Bild laden |
| DroidCam-Stream kommt nicht | `/video` und `/mjpegfeed` probieren, PC-Client schließen, gleiches WLAN, Firewall, Handy entsperrt |
| USB-Webcam bleibt schwarz | Anderen Index probieren, andere Kamera-App schließen, Kabel prüfen |
| Bild ist verdreht | Das Programm korrigiert EXIF normalerweise; sonst Foto als JPG exportieren |
| Alles blockiert beim Verbinden | Netzwerk-Streams können einige Sekunden brauchen; die Oberfläche bleibt bedienbar |

## 13. Grenzen

- Nur optische Erkennung: verdeckte Werte, Rückseiten und sehr kleine Aufdrucke bleiben offen.
- Das Modell kann falsch raten. Werte und Polarität immer prüfen.
- Kein Messgerät: Widerstand, Kapazität und Spannung werden nicht gemessen.
- Keine Videoaufnahme: es werden einzelne Standbilder aufgenommen, aber nicht gespeichert.
- DroidCam (kostenlos) liefert 640×480; für feine Beschriftungen ist ein Makrofoto besser.
- Netzwerk-Kameras hängen von WLAN, App und Akkustand des Handys ab.

## Siehe auch

- [[README]] · [[Stand]] · [[Bestand]] · [[00-Projekte]]
- [[Kondensatoren-Auswahl]] · [[MOSFET-Auswahl]] · [[EasyEDA-LCSC-JLCPCB]]
