# Bauteil-Inventar

Programm für den Bauteilbestand. Es nimmt ein Bild auf – von einer Kamera, einem Netzwerk-Stream oder einer vorhandenen Bilddatei –, schlägt mit einem Vision-Modell Bauteilart, Wert, Gehäuse und Eigenschaften vor, du korrigierst und trägst **Anzahl** und Lagerort ein. Gespeichert wird in `inventar.json`; daraus entstehen automatisch [[Bestand]] (Markdown für Obsidian) und `inventar.csv` (für Excel).

Standardmäßig läuft die Erkennung über **DeepSeek** (`deepseek-flash`). Claude von Anthropic geht weiterhin als Alternative.

**Bedienung im Alltag:** siehe [[Anleitung]] (Kurzablauf, Kameras, Bilddateien, Feldregeln, Problemlösungen). Dieses README beschreibt Einrichtung und Technik.

## Einmal einrichten

```powershell
cd "C:\Users\kilia\Documents\Obsidian Vault\20-Projekte\Bauteil-Inventar"
python -m pip install -r requirements.txt
```

`pillow-heif` ist in `requirements.txt` enthalten, damit iPhone-Fotos im HEIC-Format direkt gelesen werden. Ohne das Paket gehen JPG, PNG, WebP, BMP und TIFF; HEIC meldet dann einen Hinweis.

Für die automatische Erkennung braucht das Programm einen DeepSeek-API-Key. Er wird **nicht** im Projekt gespeichert, sondern nur aus der Umgebung gelesen. Einmalig für dein Windows-Konto:

```powershell
setx DEEPSEEK_API_KEY "sk-..."
```

Danach ein **neues** Terminal öffnen (auf `setx` folgende Fenster haben die Variable) und starten:

```powershell
python inventar.py
```

Nur für die aktuelle PowerShell-Sitzung:

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
python inventar.py
```

`starten.bat` doppelklicken funktioniert ebenfalls und liest dieselbe Variable, falls sie gesetzt ist.

Ohne Key startet das Programm trotzdem; dann füllst du die Felder selbst aus. Fotos werden nicht gespeichert.

## Anthropic statt DeepSeek

```powershell
python -m pip install anthropic
$env:INVENTAR_ANBIETER = "anthropic"
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python inventar.py
```

Ohne `INVENTAR_ANBIETER` gilt: `DEEPSEEK_API_KEY` hat Vorrang, sonst `ANTHROPIC_API_KEY`.

## Bedienung

| Taste / Knopf | Wirkung |
|---|---|
| Leertaste | Foto von der Kamera aufnehmen und erkennen lassen |
| Strg+O | vorhandene Bilddatei laden |
| Strg+S | Eintrag speichern |
| Felder leeren | Formular zurücksetzen |

1. Bauteil vor die Kamera halten (Aufdruck möglichst scharf und lesbar) oder ein vorhandenes Foto laden.
2. **Foto aufnehmen** bzw. **Bild laden…** – der Vorschlag landet in den Feldern.
3. Kategorie, Bezeichnung, Wert, Gehäuse und Eigenschaften prüfen.
4. **Anzahl** eintragen, optional **Lagerort**. Eigenschaften mit **Semikolon** trennen, z. B. `1 %; 0,25 W` (wegen des Dezimalkommas).
5. **Speichern**. Gibt es das Bauteil schon (gleiche Bezeichnung + Wert + Gehäuse), fragt das Programm, ob die Anzahl dazugezählt werden soll.

Ein geladenes Standbild pausiert die Live-Vorschau, damit es nicht sofort überschrieben wird. **Felder leeren**, **Speichern** oder **Verbinden** schaltet die Kamera wieder live.

## Bildquellen

Im Feld **Kamera** steht entweder ein Index oder eine Stream-URL. Danach **Verbinden** drücken.

| Quelle | Eingabe | Hinweis |
|---|---|---|
| Eingebaute Kamera | `0` | Standard |
| USB-Webcam | `1`, `2`, … | Kabel-Webcam wird meist als nächster Index erkannt; ausprobieren |
| iPhone als virtuelle Kamera | Index ausprobieren | braucht unter Windows 10 eine App wie Camo, Iriun, EpocCam oder DroidCam; deren virtuelle Kamera erscheint als Index |
| iPhone im WLAN | `http://<iPhone-IP>:<Port>/video` | App auf dem iPhone muss einen MJPEG-/RTSP-Stream anbieten; PC und iPhone im selben WLAN; die URL steht in der App |
| Bilddatei | **Bild laden…** (Strg+O) | JPG, PNG, WebP, BMP, TIFF und HEIC (iPhone) |

Bei einer Netzwerk-Kamera kann der Verbindungsaufbau einige Sekunden dauern; die Oberfläche bleibt währenddessen bedienbar. Bei Problemen die Windows-Firewall für das Programm freigeben und prüfen, ob iPhone und PC im selben Netz sind.

## Dateien

| Datei | Inhalt |
|---|---|
| `inventar.py` | Programm |
| `inventar.json` | Datenbestand (eine Liste von Einträgen) |
| `Bestand.md` | automatisch erzeugte Übersicht für Obsidian |
| `inventar.csv` | automatisch erzeugte Tabelle für Excel (`;` als Trenner) |

Fotos werden **nicht gespeichert**. Das aufgenommene Bild bleibt nur im Arbeitsspeicher, wird für die Erkennung als JPEG kodiert und danach verworfen. Ein vorhandener Ordner `Fotos/` aus älteren Versionen bleibt unangetastet, wird aber nicht mehr beschrieben.

`Bestand.md` und `inventar.csv` nicht von Hand ändern – beim nächsten Speichern werden sie neu geschrieben.

## Kamera und Modell

```powershell
python inventar.py --kamera 1          # zweite Kamera
python inventar.py --quelle "http://192.168.1.50:8080/video"
python inventar.py --nur-md            # nur Bestand.md/CSV neu erzeugen
$env:INVENTAR_MODELL = "deepseek-flash"      # anderes Modell
$env:INVENTAR_ANBIETER = "deepseek"          # Anbieter erzwingen
```

`--quelle` nimmt einen Index oder eine URL und hat Vorrang vor `--kamera`.

Standard ist `deepseek-flash`. Die Erkennung ist ein **Vorschlag**, kein Messgerät: Werte und Aufdrucke bitte prüfen, besonders bei kleinen SMD-Bauteilen und Farbcodes.

## Grenzen

- Das Programm erkennt Bauteile nur optisch. Verdeckte Werte, Rückseiten und sehr kleine Aufdrucke bleiben offen.
- Ein Barcode-/QR-Scanner für LCSC-Tüten ist noch nicht eingebaut (Idee für später).
- Lokale Kameras werden mit OpenCV über DirectShow geöffnet. Wenn `0` schwarz bleibt, `1` oder `2` probieren.
- Netzwerk-Streams brauchen eine von der iPhone-App bereitgestellte URL (MJPEG oder RTSP). Die App muss im Hintergrund laufen; bei gesperrtem iPhone pausiert der Stream oft.
- Große Handyfotos werden vor der Erkennung auf maximal 2000 px Kantenlänge verkleinert.
