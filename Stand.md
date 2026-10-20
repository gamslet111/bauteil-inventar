---
projekt: bauteil-inventar
aktualisiert: 2026-10-20
quelle: claude-code
tags: [projekt, elektronik, inventar]
---
# Bauteil-Inventar: Stand

**Stand: 20.10.2026.** Das Programm `inventar.py` nimmt ein Bild auf – von einer lokalen Kamera, einem Netzwerk-Stream oder einer Bilddatei – und lässt es von einem Vision-Modell vorschlagen (Bauteilart, Wert, Gehäuse, Eigenschaften, Aufdruck). Du korrigierst die Felder, trägst **Anzahl** und Lagerort ein. Gespeichert wird in `inventar.json`; daraus werden [[Bestand]] und `inventar.csv` erzeugt. Erkennung läuft über **DeepSeek** (`deepseek-flash`, `DEEPSEEK_API_KEY`), Anthropic ist als Alternative eingebaut.

## Was es kann
- Kamera-Quelle frei wählbar: Index `0`–`4` (eingebaute Kamera, USB-Webcam, virtuelle iPhone-Kamera) oder Stream-URL (MJPEG/RTSP, z. B. iPhone-App im WLAN)
- Bilddatei laden über **Bild laden…** / Strg+O: JPG, PNG, WebP, BMP, TIFF und HEIC (iPhone, über `pillow-heif`)
- Live-Vorschau (OpenCV, DirectShow unter Windows); Lesen im Hintergrund-Thread, damit ein stockender Stream die Oberfläche nicht blockiert
- Standbild pausiert die Vorschau, bis der Eintrag gespeichert, die Felder geleert oder neu verbunden wird
- Foto per Leertaste; das Bild bleibt im Arbeitsspeicher und wird **nicht gespeichert**; große Handyfotos werden vor der Erkennung auf 2000 px verkleinert
- Erkennung mit `deepseek-flash` (Modell über `INVENTAR_MODELL` änderbar)
- Anbieter automatisch nach vorhandenem Key: DeepSeek vor Anthropic; erzwungen über `INVENTAR_ANBIETER`
- Vorschlag ist editierbar; ohne API-Key reine Handeingabe
- Anzahl als Zahlenfeld, Eigenschaften als Semikolonliste (wegen Dezimalkomma)
- Gleiche Bezeichnung + Wert + Gehäuse → Anzahl auf Wunsch addieren
- Automatisch: `Bestand.md` (nach Kategorie gruppiert) und `inventar.csv` (Excel, `;`)

## Entscheidungen
| Datum | Entscheidung | Grund |
|---|---|---|
| 20.10.2026 | JSON als Datenquelle, Markdown und CSV generiert | JSON ist robust fürs Programm, Markdown ist im Vault lesbar, CSV für Excel |
| 20.10.2026 | Vision-Modell statt lokalem Modell | liest Aufdrucke und erkennt Bauformen ohne Training; kein lokales Modell nötig |
| 20.10.2026 | Anzahl immer von Hand | die Anzahl im Foto ist oft nicht eindeutig; der Nutzer entscheidet |
| 20.10.2026 | Kein API-Key im Vault | Vault-Regel: keine Passwörter/Keys; Key nur über `DEEPSEEK_API_KEY` bzw. `ANTHROPIC_API_KEY` |
| 20.10.2026 | DeepSeek als Standard | vorhandener Key ist von DeepSeek; `deepseek-flash` nimmt Bilder per OpenAI-kompatibler API an |
| 20.10.2026 | DeepSeek per `urllib`, kein OpenAI-SDK | eine einzelne POST-Anfrage; spart eine Abhängigkeit und funktioniert ohne Zusatzpaket |
| 20.10.2026 | Bilddatei laden statt nur Kamera | Bauteile lassen sich auch nachträglich vom Handy oder aus einem Ordner erfassen |
| 20.10.2026 | Fotos nur im Arbeitsspeicher, keine Bilddateien | das Bild dient der Erkennung; der Bestand bleibt ohne Bilddateien klein und einfach zu sichern |
| 20.10.2026 | Netzwerk-URL als Kamera-Quelle | iPhone-Apps liefern MJPEG/RTSP; OpenCV/FFmpeg liest das ohne Zusatzsoftware |
| 20.10.2026 | Kamera-Lesen im Hintergrund-Thread, Meldungen über `queue` | ein hängender WLAN-Stream blockiert die Tk-Oberfläche nicht; Tk wird nur im Hauptthread aufgerufen |
| 20.10.2026 | HEIC fest in `requirements.txt` (`pillow-heif`) | iPhone-Fotos sollen ohne Zusatzschritt lesbar sein; Wheel für Python 3.13/Windows vorhanden |

## Offen
- [ ] Erste echte Fotos mit DeepSeek testen (Erkennungsqualität, Beleuchtung, Abstand)
- [ ] USB-Webcam und iPhone-Stream mit der echten Hardware testen
- [ ] Prüfen, ob Aufdrucke kleiner ICs lesbar genug sind
- [ ] Optional: QR-/Barcode-Scanner für LCSC-Tüten
- [ ] Optional: Suche/Filter in `Bestand.md` (z. B. Dataview) oder eine kleine Web-Ansicht
- [ ] Lagerorte festlegen (Kästen, Fächer) und einheitlich benennen
- [ ] Entscheiden, ob der alte Ordner `Fotos/` und die Bildverweise in [[Bestand]] bleiben oder entfernt werden

## Dateien
`inventar.py` · `requirements.txt` · `README.md` · [[Anleitung]] · `inventar.json` · `Bestand.md` · `inventar.csv` · `Fotos/` (nur alte Einträge, wird nicht mehr beschrieben)

## Siehe auch
- [[Anleitung]] · [[README]] · [[00-Projekte]] · [[Kondensatoren-Auswahl]] · [[MOSFET-Auswahl]] · [[EasyEDA-LCSC-JLCPCB]]
