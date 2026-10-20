#!/usr/bin/env python3
"""Bauteil-Inventar mit Webcam.

Ablauf:
  1. Bildquelle waehlen: Kamera-Index (USB-Webcam, virtuelle iPhone-Kamera)
     oder Stream-URL (iPhone-App im WLAN). Alternativ ein vorhandenes Bild
     ueber "Bild laden" oeffnen (JPG, PNG, WebP, HEIC ...).
  2. Leertaste (oder "Foto aufnehmen") bzw. "Bild laden": Bild im Speicher
     aufnehmen und - wenn ein API-Key vorhanden ist - vom Modell vorschlagen
     lassen. Fotos werden nicht auf Platte geschrieben.
  3. Vorschlag pruefen/korrigieren, Anzahl und Lagerort eintragen.
  4. Strg+S (oder "Speichern"): Eintrag in inventar.json ablegen und
     Bestand.md + inventar.csv neu erzeugen.

Der API-Key wird nicht gespeichert. Standard ist DeepSeek (DEEPSEEK_API_KEY,
Modell deepseek-flash). Alternativ Anthropic (ANTHROPIC_API_KEY) oder explizit
ueber INVENTAR_ANBIETER=deepseek|anthropic. Ohne Key geht alles manuell.

Aufruf:
  python inventar.py
  python inventar.py --kamera 1
  python inventar.py --quelle "http://192.168.1.50:8080/video"
  python inventar.py --nur-md        # nur Bestand.md/CSV neu schreiben
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import END, IntVar, StringVar, Tk, filedialog, messagebox, ttk
import tkinter as tk

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:
    Image = None
    ImageOps = None
    ImageTk = None

# Optional: HEIC/HEIF (iPhone-Fotos) lesbar machen.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass


BASE = Path(__file__).resolve().parent
DATEN = BASE / "inventar.json"
BESTAND = BASE / "Bestand.md"
CSV_DATEI = BASE / "inventar.csv"

STANDARD_MODELLE = {
    "deepseek": "deepseek-flash",
    "anthropic": "claude-opus-5-5",
}
ANBIETER_NAMEN = {"deepseek": "DeepSeek", "anthropic": "Anthropic"}
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")

KATEGORIEN = [
    "Widerstand", "Kondensator", "Spule", "Diode", "LED", "Transistor",
    "MOSFET", "Relais", "IC", "Sensor", "Modul", "Steckverbinder",
    "Mechanik", "Sonstiges",
]

SYSTEM_PROMPT = (
    "Du inventarisierst elektronische Bauteile. Du bekommst ein Foto von "
    "genau einem Bauteil (oder mehreren gleichen Bauteilen). Antworte "
    "ausschließlich mit einem JSON-Objekt, ohne Markdown, ohne Erklärung."
)

ANWEISUNG = """Bestimme das Bauteil auf dem Foto für ein Bauteil-Inventar.

Antworte NUR mit diesem JSON:
{
  "kategorie": "Widerstand | Kondensator | Spule | Diode | LED | Transistor | MOSFET | Relais | IC | Sensor | Modul | Steckverbinder | Mechanik | Sonstiges",
  "bezeichnung": "kurzer Name, z. B. 'Widerstand 10 kΩ' oder 'NE555 Timer-IC'",
  "wert": "Wert oder Typ, z. B. '10 kΩ', '100 nF', 'NE555'; sonst ''",
  "gehaeuse": "Bauform, z. B. '0207 bedrahtet', '0603', 'TO-220', 'DIP-8'; sonst ''",
  "eigenschaften": ["z. B. '1 %', '0,25 W', '50 V'"],
  "aufdruck": "lesbarer Aufdruck oder Teilenummer; sonst ''",
  "anzahl_auf_foto": 1,
  "konfidenz": 0.0
}

Regeln:
- Lies den Aufdruck, wenn er lesbar ist. Erfinde nichts.
- Farbreihen von Widerständen nur angeben, wenn sie klar erkennbar sind.
- Unsichere Felder leer lassen und die Konfidenz senken (0 bis 1).
- Anzahl im Foto zählen, aber nur wenn alle Bauteile gleich sind."""


# ---------------------------------------------------------------- Daten

def lade_daten(gui: bool = True) -> list[dict]:
    if not DATEN.exists():
        return []
    try:
        with DATEN.open("r", encoding="utf-8") as f:
            daten = json.load(f)
        if isinstance(daten, list):
            return [d for d in daten if isinstance(d, dict)]
        raise ValueError("inventar.json enthält keine Liste.")
    except Exception as fehler:
        sicherung = DATEN.with_name(
            f"inventar.kaputt-{datetime.now():%Y%m%d-%H%M%S}.json"
        )
        try:
            DATEN.replace(sicherung)
        except OSError:
            pass
        meldung = (
            f"inventar.json konnte nicht gelesen werden: {fehler}\n"
            f"Die Datei wurde als {sicherung.name} gesichert. "
            "Es wird mit einem leeren Bestand begonnen."
        )
        if gui:
            messagebox.showwarning("inventar.json", meldung)
        else:
            print(meldung)
        return []


def speichere_daten(eintraege: list[dict]) -> None:
    tmp = DATEN.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(eintraege, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATEN)


def _zelle(wert) -> str:
    return str(wert or "").replace("|", "\\|").replace("\n", " ").strip()


def _eigenschaften_text(eintrag: dict) -> str:
    werte = eintrag.get("eigenschaften") or []
    if isinstance(werte, str):
        werte = [werte]
    return ", ".join(str(w).strip() for w in werte if str(w).strip())


def _foto_link(eintrag: dict) -> str:
    fotos = eintrag.get("fotos") or []
    if isinstance(fotos, str):
        fotos = [fotos]
    if not fotos:
        return "—"
    name = Path(fotos[0]).name
    link = f"[[{name}|Foto]]"
    if len(fotos) > 1:
        link += f" +{len(fotos) - 1}"
    return link


def _arten(n: int) -> str:
    return "Art" if n == 1 else "Arten"


def _sortierschluessel(eintrag: dict):
    kategorie = str(eintrag.get("kategorie") or "Sonstiges")
    rang = KATEGORIEN.index(kategorie) if kategorie in KATEGORIEN else len(KATEGORIEN)
    return (rang, kategorie.lower(), str(eintrag.get("bezeichnung", "")).lower())


def schreibe_bestand(eintraege: list[dict]) -> None:
    jetzt = datetime.now().strftime("%d.%m.%Y, %H:%M")
    gesamt_stueck = sum(int(e.get("anzahl") or 0) for e in eintraege)

    zeilen = [
        "# Bauteil-Bestand",
        "",
        "> Automatisch erzeugt von `inventar.py`. Nicht von Hand ändern – "
        "Änderungen macht das Skript.",
        f"> Stand: {jetzt} · **{len(eintraege)} "
        f"{'Bauteilart' if len(eintraege) == 1 else 'Bauteilarten'}** · "
        f"**{gesamt_stueck} Stück**",
        "",
    ]

    if not eintraege:
        zeilen += ["Noch keine Bauteile erfasst.", ""]
    else:
        gruppen: dict[str, list[dict]] = {}
        for eintrag in sorted(eintraege, key=_sortierschluessel):
            gruppen.setdefault(str(eintrag.get("kategorie") or "Sonstiges"), []).append(eintrag)

        for kategorie in sorted(gruppen, key=lambda k: _sortierschluessel({"kategorie": k})):
            gruppe = gruppen[kategorie]
            stueck = sum(int(e.get("anzahl") or 0) for e in gruppe)
            zeilen += [
                f"## {kategorie} ({len(gruppe)} {_arten(len(gruppe))}, {stueck} Stück)",
                "",
                "| Bauteil | Wert | Gehäuse | Eigenschaften | Aufdruck | Anzahl | Lagerort | Foto |",
                "|---|---|---|---|---|---:|---|---|",
            ]
            for e in gruppe:
                zeilen.append(
                    "| {bez} | {wert} | {geh} | {eig} | {auf} | {anz} | {lager} | {foto} |".format(
                        bez=_zelle(e.get("bezeichnung")),
                        wert=_zelle(e.get("wert")),
                        geh=_zelle(e.get("gehaeuse")),
                        eig=_zelle(_eigenschaften_text(e)),
                        auf=_zelle(e.get("aufdruck")),
                        anz=int(e.get("anzahl") or 0),
                        lager=_zelle(e.get("lagerort")),
                        foto=_foto_link(e),
                    )
                )
            zeilen.append("")

    BESTAND.write_text("\n".join(zeilen), encoding="utf-8")


def schreibe_csv(eintraege: list[dict]) -> None:
    with CSV_DATEI.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Kategorie", "Bezeichnung", "Wert", "Gehaeuse", "Eigenschaften",
            "Aufdruck", "Anzahl", "Lagerort", "Fotos", "Erkannt von", "Aktualisiert",
        ])
        for e in sorted(eintraege, key=_sortierschluessel):
            fotos = e.get("fotos") or []
            if isinstance(fotos, str):
                fotos = [fotos]
            writer.writerow([
                e.get("kategorie", ""), e.get("bezeichnung", ""), e.get("wert", ""),
                e.get("gehaeuse", ""), _eigenschaften_text(e), e.get("aufdruck", ""),
                e.get("anzahl", 0), e.get("lagerort", ""),
                " | ".join(str(f) for f in fotos),
                e.get("erkannt_von", ""), e.get("aktualisiert", ""),
            ])


# ---------------------------------------------------------------- Erkennung

def _json_aus_text(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    treffer = re.search(r"\{.*\}", text, re.S)
    if not treffer:
        raise ValueError("Die Antwort enthielt kein JSON-Objekt.")
    daten = json.loads(treffer.group(0))
    if not isinstance(daten, dict):
        raise ValueError("Die Antwort war kein JSON-Objekt.")
    return daten


def anbieter() -> str:
    """Welcher Anbieter benutzt wird: INVENTAR_ANBIETER schlaegt Keys."""
    gewaehlt = os.environ.get("INVENTAR_ANBIETER", "").strip().lower()
    if gewaehlt in STANDARD_MODELLE:
        return gewaehlt
    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return "deepseek"
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "anthropic"
    return ""


def modell_name() -> str:
    return (os.environ.get("INVENTAR_MODELL", "").strip()
            or STANDARD_MODELLE.get(anbieter(), "unbekannt"))


def _erkenne_deepseek(bilddaten: bytes, modell: str) -> dict:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Kein DEEPSEEK_API_KEY gesetzt. In der PowerShell:\n"
            '$env:DEEPSEEK_API_KEY = "sk-..."'
        )

    bild = base64.standard_b64encode(bilddaten).decode("ascii")
    koerper = {
        "model": modell,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": ANWEISUNG},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{bild}",
                }},
            ]},
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
    }
    anfrage = urllib.request.Request(
        f"{DEEPSEEK_BASE}/chat/completions",
        data=json.dumps(koerper, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(anfrage, timeout=180) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as fehler:
        details = fehler.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(
            f"DeepSeek antwortet mit HTTP {fehler.code}: {details}"
        ) from None
    except urllib.error.URLError as fehler:
        raise RuntimeError(f"DeepSeek nicht erreichbar: {fehler.reason}") from None

    try:
        wahl = daten["choices"][0]
    except (KeyError, IndexError, TypeError):
        raise ValueError(f"Unerwartete Antwort von DeepSeek: {str(daten)[:300]}") from None
    if wahl.get("finish_reason") == "length":
        raise RuntimeError("Die Antwort war zu lang und wurde abgeschnitten.")

    nachricht = wahl.get("message") or {}
    text = nachricht.get("content") or ""
    if isinstance(text, list):
        text = "".join(
            teil.get("text", "") for teil in text if isinstance(teil, dict)
        )
    if not str(text).strip():
        raise ValueError("Die Antwort war leer.")
    return normalisiere_ergebnis(_json_aus_text(str(text)))


def _erkenne_anthropic(bilddaten: bytes, modell: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    bild = base64.standard_b64encode(bilddaten).decode("ascii")
    antwort = client.messages.create(
        model=modell,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": bild,
                    },
                },
                {"type": "text", "text": ANWEISUNG},
            ],
        }],
    )

    if antwort.stop_reason == "refusal":
        grund = getattr(antwort.stop_details, "explanation", None) or "keine Angabe"
        raise RuntimeError(f"Das Modell hat die Erkennung abgelehnt ({grund}).")
    if antwort.stop_reason == "max_tokens":
        raise RuntimeError("Die Antwort war zu lang und wurde abgeschnitten.")

    text = "".join(b.text for b in antwort.content if b.type == "text")
    if not text:
        raise ValueError("Die Antwort war leer.")
    return normalisiere_ergebnis(_json_aus_text(text))


def erkenne_bauteil(bilddaten: bytes) -> dict:
    gewaehlt = anbieter()
    if gewaehlt == "deepseek":
        return _erkenne_deepseek(bilddaten, modell_name())
    if gewaehlt == "anthropic":
        return _erkenne_anthropic(bilddaten, modell_name())
    raise RuntimeError(
        "Kein API-Key gefunden. Setze vor dem Start DEEPSEEK_API_KEY "
        '(oder ANTHROPIC_API_KEY):\n$env:DEEPSEEK_API_KEY = "sk-..."'
    )


def normalisiere_ergebnis(daten: dict) -> dict:
    def text(name: str) -> str:
        wert = daten.get(name, "")
        return "" if wert is None else str(wert).strip()

    kategorie = text("kategorie")
    if kategorie not in KATEGORIEN:
        kategorie = "Sonstiges"

    eigenschaften = daten.get("eigenschaften") or []
    if isinstance(eigenschaften, str):
        # Semikolon, nicht Komma: deutsche Dezimalkommas wie „0,25 W“ bleiben heil.
        eigenschaften = [t.strip() for t in eigenschaften.split(";") if t.strip()]
    elif isinstance(eigenschaften, list):
        eigenschaften = [str(t).strip() for t in eigenschaften if str(t).strip()]
    else:
        eigenschaften = []

    try:
        konfidenz = max(0.0, min(1.0, float(daten.get("konfidenz", 0))))
    except (TypeError, ValueError):
        konfidenz = 0.0

    try:
        anzahl_foto = max(1, int(daten.get("anzahl_auf_foto", 1)))
    except (TypeError, ValueError):
        anzahl_foto = 1

    return {
        "kategorie": kategorie,
        "bezeichnung": text("bezeichnung"),
        "wert": text("wert"),
        "gehaeuse": text("gehaeuse"),
        "eigenschaften": eigenschaften,
        "aufdruck": text("aufdruck"),
        "anzahl_auf_foto": anzahl_foto,
        "konfidenz": konfidenz,
    }


# ---------------------------------------------------------------- Oberfläche

class InventarApp:
    def __init__(self, root: Tk, quelle: str):
        self.root = root
        self.root.title("Bauteil-Inventar")
        self.root.geometry("1060x740")
        self.root.minsize(940, 700)

        self.kamera = None
        self.kamera_token = 0
        self.aktuelles_bild = None
        self.neues_bild = None
        self.bild_lock = threading.Lock()
        self.meldungen: queue.Queue = queue.Queue()
        self.vorschau_job = None
        self.vorschau_aktiv = True
        self.anzeige = None
        self.letztes_bilddaten: bytes | None = None
        self.erkennt_gerade = False
        self.erkannt_von_ki = False
        self.erkannt_von_modell = ""
        self.konfidenz: float | None = None
        self.laeuft = True
        self.eintraege = lade_daten()
        self.start_quelle = str(quelle).strip() or "0"

        self._baue_ui()
        self._setze_startstatus()
        self._vorschau()
        self.verbinde_quelle(leise=True)
        self._aktualisiere_zaehler()

        self.root.protocol("WM_DELETE_WINDOW", self._schliessen)
        self.root.bind("<Control-s>", lambda _e: self.speichern())
        self.root.bind("<Control-S>", lambda _e: self.speichern())
        self.root.bind("<Control-o>", lambda _e: self.bild_laden())
        self.root.bind("<Control-O>", lambda _e: self.bild_laden())

    # ------------------------------------------------------------ Aufbau

    def _baue_ui(self) -> None:
        aussen = ttk.Frame(self.root, padding=10)
        aussen.pack(fill="both", expand=True)

        links = ttk.Frame(aussen)
        links.pack(side="left", fill="y")

        self.video = tk.Label(links, bg="#111111", fg="#888888",
                              width=640, height=480,
                              text="Kamera startet …", compound="center")
        self.video.pack()
        self.video.configure(takefocus=True)
        self.video.bind("<Button-1>", lambda _e: self.video.focus_set())
        self.video.bind("<space>", lambda _e: self.aufnehmen())

        quelle = ttk.Frame(links)
        quelle.pack(fill="x", pady=(8, 0))
        ttk.Label(quelle, text="Kamera:").pack(side="left")
        self.var_quelle = StringVar(value=self.start_quelle)
        self.cmb_quelle = ttk.Combobox(
            quelle, textvariable=self.var_quelle,
            values=["0", "1", "2", "3", "4"], width=28,
        )
        self.cmb_quelle.pack(side="left", fill="x", expand=True, padx=6)
        self.cmb_quelle.bind("<Return>", lambda _e: self.verbinde_quelle())
        self.btn_verbinden = ttk.Button(quelle, text="Verbinden",
                                        command=self.verbinde_quelle)
        self.btn_verbinden.pack(side="left")
        ttk.Label(
            links,
            text="Index (0–4) oder Stream-URL, z. B. http://192.168.1.50:8080/video",
            foreground="#666666",
        ).pack(anchor="w", pady=(2, 0))

        knoepfe = ttk.Frame(links)
        knoepfe.pack(fill="x", pady=(8, 0))

        self.btn_aufnehmen = ttk.Button(knoepfe, text="Foto aufnehmen (Leertaste)",
                                        command=self.aufnehmen)
        self.btn_aufnehmen.pack(side="left")
        self.btn_bild = ttk.Button(knoepfe, text="Bild laden… (Strg+O)",
                                   command=self.bild_laden)
        self.btn_bild.pack(side="left", padx=6)

        knoepfe2 = ttk.Frame(links)
        knoepfe2.pack(fill="x", pady=(6, 0))
        ttk.Button(knoepfe2, text="Felder leeren",
                   command=self.zuruecksetzen).pack(side="left")
        ttk.Button(knoepfe2, text="Speichern (Strg+S)",
                   command=self.speichern).pack(side="left", padx=6)

        rechts = ttk.LabelFrame(aussen, text="Bauteil", padding=12)
        rechts.pack(side="left", fill="both", expand=True, padx=(16, 0))

        self.var_kategorie = StringVar(value="Sonstiges")
        self.var_bezeichnung = StringVar()
        self.var_wert = StringVar()
        self.var_gehaeuse = StringVar()
        self.var_eigenschaften = StringVar()
        self.var_aufdruck = StringVar()
        self.var_anzahl = IntVar(value=1)
        self.var_lagerort = StringVar()

        zeilen = [
            ("Kategorie", "combobox", self.var_kategorie),
            ("Bezeichnung", "entry", self.var_bezeichnung),
            ("Wert / Typ", "entry", self.var_wert),
            ("Gehäuse", "entry", self.var_gehaeuse),
            ("Eigenschaften", "entry", self.var_eigenschaften),
            ("Aufdruck", "entry", self.var_aufdruck),
            ("Anzahl", "spinbox", self.var_anzahl),
            ("Lagerort", "entry", self.var_lagerort),
        ]

        self.felder: dict[str, tk.Widget] = {}
        for i, (label, art, variable) in enumerate(zeilen):
            ttk.Label(rechts, text=label).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if art == "combobox":
                widget = ttk.Combobox(rechts, textvariable=variable, values=KATEGORIEN)
            elif art == "spinbox":
                widget = ttk.Spinbox(rechts, from_=1, to=99999, textvariable=variable)
            else:
                widget = ttk.Entry(rechts, textvariable=variable)
            widget.grid(row=i, column=1, sticky="ew", pady=4)
            self.felder[label] = widget

        rechts.columnconfigure(1, weight=1)

        ttk.Label(
            rechts,
            text="Eigenschaften mit Semikolon trennen, z. B. „1 %; 0,25 W“.",
            foreground="#666666",
        ).grid(row=len(zeilen), column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.var_status = StringVar(value="Bereit.")
        status = ttk.Label(self.root, textvariable=self.var_status, padding=(12, 4))
        status.pack(fill="x", side="bottom")

    def _setze_startstatus(self) -> None:
        if anbieter():
            self.var_status.set(
                f"Bereit. Erkennung: {ANBIETER_NAMEN.get(anbieter(), anbieter())} "
                f"({modell_name()})."
            )
        else:
            self.var_status.set(
                "Bereit. Kein API-Key – Felder selbst ausfüllen."
            )

    # ------------------------------------------------------------ Kamera

    def verbinde_quelle(self, leise: bool = False) -> None:
        if cv2 is None:
            self.var_status.set("opencv-python fehlt – nur manuelle Eingabe möglich.")
            self.video.configure(text="opencv-python installieren:\n"
                                      "python -m pip install opencv-python")
            return

        text = self.var_quelle.get().strip()
        if not text:
            if not leise:
                messagebox.showwarning(
                    "Kamera", "Bitte Kamera-Index oder Stream-URL eingeben."
                )
            return

        self.kamera_token += 1
        token = self.kamera_token
        self._kamera_freigeben()
        self.vorschau_aktiv = True
        self.var_status.set(f"Verbinde mit {text} …")
        self.btn_verbinden.configure(state="disabled")
        threading.Thread(
            target=self._kamera_lesen, args=(text, token), daemon=True
        ).start()

    def _kamera_freigeben(self) -> None:
        kamera = self.kamera
        self.kamera = None
        self.aktuelles_bild = None
        with self.bild_lock:
            self.neues_bild = None
        if kamera is not None:
            try:
                kamera.release()
            except Exception:
                pass

    def _oeffne_kamera(self, text: str):
        if text.isdigit():
            index = int(text)
            try:
                kamera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            except Exception:
                kamera = cv2.VideoCapture(index)
            if not kamera.isOpened():
                kamera.release()
                kamera = cv2.VideoCapture(index)
            if not kamera.isOpened():
                kamera.release()
                raise RuntimeError(f"Kamera {index} nicht gefunden.")
            kamera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return kamera

        # Netzwerk-Stream (MJPEG/HTTP oder RTSP), z. B. von einer iPhone-App.
        parameter = []
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            parameter += [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000]
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            parameter += [cv2.CAP_PROP_READ_TIMEOUT_MSEC, 8000]
        try:
            kamera = cv2.VideoCapture(text, cv2.CAP_FFMPEG, parameter)
        except TypeError:
            kamera = cv2.VideoCapture(text, cv2.CAP_FFMPEG)
        if not kamera.isOpened():
            kamera.release()
            kamera = cv2.VideoCapture(text)
        if not kamera.isOpened():
            kamera.release()
            raise RuntimeError(f"Stream nicht erreichbar: {text}")
        return kamera

    def _kamera_lesen(self, text: str, token: int) -> None:
        """Oeffnet die Quelle und liest Bilder im Hintergrund.

        Lesen im Hauptthread wuerde die Oberflaeche blockieren, sobald eine
        WLAN-Kamera stockt. Der Hauptthread zeigt nur das jeweils neueste Bild.
        """
        kamera = None
        try:
            kamera = self._oeffne_kamera(text)
            if token != self.kamera_token:
                return
            self.kamera = kamera
            self.meldungen.put(("kamera_verbunden", text, token))

            fehler = 0
            while token == self.kamera_token:
                try:
                    ok, bild = kamera.read()
                except Exception:
                    ok, bild = False, None
                if not ok:
                    fehler += 1
                    if fehler >= 30:
                        self.meldungen.put(("kamera_ausgefallen", text, token))
                        return
                    time.sleep(0.1)
                    continue
                fehler = 0
                with self.bild_lock:
                    self.neues_bild = bild
                time.sleep(0.02)
        except Exception as problem:
            if token == self.kamera_token:
                self.meldungen.put(("kamera_fehler", text, str(problem), token))
        finally:
            if kamera is not None:
                try:
                    kamera.release()
                except Exception:
                    pass
            if self.kamera is kamera:
                self.kamera = None
            self.meldungen.put(("kamera_ende", token))

    def _kamera_verbunden(self, text: str, token: int) -> None:
        if token != self.kamera_token:
            return
        self.btn_verbinden.configure(state="normal")
        if self.vorschau_aktiv:
            self.var_status.set(f"Kamera verbunden: {text}.")

    def _kamera_fehler(self, text: str, meldung: str, token: int) -> None:
        if token != self.kamera_token:
            return
        self.btn_verbinden.configure(state="normal")
        # Ein geladenes Standbild nicht durch eine Kamera-Fehlermeldung ersetzen.
        if not self.vorschau_aktiv:
            return
        self.aktuelles_bild = None
        self.var_status.set(
            f"Keine Kamera unter „{text}“ – Bild laden oder manuell eintragen."
        )
        self.video.configure(
            image="",
            text=f"Keine Kamera:\n{text}\n\n{meldung}",
        )

    def _kamera_ausgefallen(self, text: str, token: int) -> None:
        if token != self.kamera_token:
            return
        self.btn_verbinden.configure(state="normal")
        if not self.vorschau_aktiv:
            return
        self.aktuelles_bild = None
        self.var_status.set(
            "Kamera getrennt – „Verbinden“ erneut versuchen oder Bild laden."
        )
        self.video.configure(image="", text="Kamera getrennt.")

    def _kamera_thread_ende(self, token: int) -> None:
        if token == self.kamera_token:
            self.btn_verbinden.configure(state="normal")

    def _verarbeite_meldungen(self) -> None:
        """Worker-Threads melden ueber eine Queue; Tk laeuft nur im Hauptthread."""
        while True:
            try:
                meldung = self.meldungen.get_nowait()
            except queue.Empty:
                return
            art = meldung[0]
            if art == "kamera_verbunden":
                self._kamera_verbunden(meldung[1], meldung[2])
            elif art == "kamera_fehler":
                self._kamera_fehler(meldung[1], meldung[2], meldung[3])
            elif art == "kamera_ausgefallen":
                self._kamera_ausgefallen(meldung[1], meldung[2])
            elif art == "kamera_ende":
                self._kamera_thread_ende(meldung[1])
            elif art == "erkennung_ok":
                self._uebernehme_erkenntnis(meldung[1])
            elif art == "erkennung_fehler":
                self._erkennung_fehlgeschlagen(meldung[1])

    def _vorschau(self) -> None:
        if not self.laeuft:
            return
        self._verarbeite_meldungen()
        if self.vorschau_aktiv and not self.erkennt_gerade:
            with self.bild_lock:
                bild = self.neues_bild
                self.neues_bild = None
            if bild is not None:
                self.aktuelles_bild = bild
                self._zeige_bild(bild)
        self.vorschau_job = self.root.after(30, self._vorschau)

    def _zeige_bild(self, bild) -> None:
        if Image is None or ImageTk is None:
            return
        if cv2 is not None and bild.ndim == 2:
            bild = cv2.cvtColor(bild, cv2.COLOR_GRAY2BGR)
        elif cv2 is not None and bild.ndim == 3 and bild.shape[2] == 4:
            bild = cv2.cvtColor(bild, cv2.COLOR_BGRA2BGR)
        rgb = bild[:, :, ::-1]
        foto = Image.fromarray(rgb)
        foto.thumbnail((640, 480), Image.LANCZOS)
        leinwand = Image.new("RGB", (640, 480), (17, 17, 17))
        leinwand.paste(foto, ((640 - foto.width) // 2, (480 - foto.height) // 2))
        self.anzeige = ImageTk.PhotoImage(leinwand)
        self.video.configure(image=self.anzeige, text="")

    # ------------------------------------------------------------ Aktionen

    def aufnehmen(self) -> None:
        if self.erkennt_gerade:
            return
        bild = self._hole_neuestes_bild()
        if bild is None:
            messagebox.showwarning(
                "Kein Bild",
                "Die Kamera liefert noch kein Bild.\n\n"
                "Alternativ „Bild laden…“ (Strg+O) verwenden.",
            )
            return
        self.vorschau_aktiv = True
        self._verarbeite_bild(bild)

    def bild_laden(self) -> None:
        if self.erkennt_gerade:
            return
        if Image is None:
            messagebox.showerror(
                "Bild laden",
                "Dafür fehlt Pillow:\npython -m pip install Pillow",
            )
            return
        if cv2 is None:
            messagebox.showerror(
                "Bild laden",
                "Dafür fehlt opencv-python:\n"
                "python -m pip install opencv-python",
            )
            return

        pfad = filedialog.askopenfilename(
            parent=self.root,
            title="Bild auswählen",
            filetypes=[
                ("Bilder", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff "
                           "*.heic *.heif"),
                ("Alle Dateien", "*.*"),
            ],
        )
        if not pfad:
            return

        try:
            import numpy as np
            with Image.open(pfad) as datei:
                # Hochformat von Handyfotos richtig drehen (EXIF), bevor
                # convert() die Metadaten verwirft.
                rgb = ImageOps.exif_transpose(datei) if ImageOps else datei
                rgb = rgb.convert("RGB")
                # Sehr große Handyfotos verkleinern: schnellerer Upload,
                # weniger Speicher; Details bleiben für die Erkennung erhalten.
                if max(rgb.size) > 2000:
                    rgb.thumbnail((2000, 2000), Image.LANCZOS)
                bild = np.asarray(rgb)[:, :, ::-1].copy()
        except Exception as fehler:
            hinweis = ""
            if Path(pfad).suffix.lower() in {".heic", ".heif"}:
                hinweis = (
                    "\n\nHEIC/HEIF (iPhone) braucht das Paket pillow-heif:\n"
                    "python -m pip install pillow-heif"
                )
            messagebox.showerror(
                "Bild laden",
                f"Bild konnte nicht gelesen werden:\n{fehler}{hinweis}",
            )
            return

        # Standbild anzeigen, nicht sofort vom Kamerastream überschreiben.
        self.vorschau_aktiv = False
        self._verarbeite_bild(bild)

    def _hole_neuestes_bild(self):
        with self.bild_lock:
            bild = self.neues_bild
            self.neues_bild = None
        if bild is not None:
            self.aktuelles_bild = bild
        return self.aktuelles_bild

    def _verarbeite_bild(self, bild) -> None:
        try:
            self.letztes_bilddaten = self._kodiere_foto(bild)
        except Exception as fehler:
            messagebox.showerror(
                "Bild", f"Bild konnte nicht verarbeitet werden:\n{fehler}"
            )
            return

        self.erkannt_von_ki = False
        self.erkannt_von_modell = ""
        self.konfidenz = None
        self._zeige_bild(bild)
        self._starte_erkennung(self.letztes_bilddaten)

    def _starte_erkennung(self, bilddaten: bytes) -> None:
        if not anbieter():
            self.erkennt_gerade = False
            self.var_status.set(
                "Bild aufgenommen. Kein API-Key – Felder selbst ausfüllen."
            )
            return

        self.erkennt_gerade = True
        self.btn_aufnehmen.configure(state="disabled")
        self.btn_bild.configure(state="disabled")
        self.var_status.set("Erkenne Bauteil …")
        threading.Thread(
            target=self._erkenne_thread, args=(bilddaten,), daemon=True
        ).start()

    def _kodiere_foto(self, bild) -> bytes:
        """JPEG im Speicher erzeugen. Fotos werden bewusst nicht gespeichert."""
        if cv2 is None:
            raise RuntimeError("opencv-python fehlt.")
        ok, puffer = cv2.imencode(".jpg", bild, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise RuntimeError("JPEG konnte nicht erzeugt werden.")
        return puffer.tobytes()

    def _erkenne_thread(self, bilddaten: bytes) -> None:
        try:
            ergebnis = erkenne_bauteil(bilddaten)
        except Exception as fehler:
            self.meldungen.put(("erkennung_fehler", str(fehler)))
            return
        self.meldungen.put(("erkennung_ok", ergebnis))

    def _erkennung_fehlgeschlagen(self, meldung: str) -> None:
        self.erkennt_gerade = False
        self.btn_aufnehmen.configure(state="normal")
        self.btn_bild.configure(state="normal")
        self.var_status.set("Erkennung nicht möglich – Felder bitte selbst ausfüllen.")
        if "No module named 'anthropic'" in meldung:
            messagebox.showinfo(
                "anthropic fehlt",
                "Für die automatische Erkennung fehlt das Paket anthropic:\n\n"
                "python -m pip install anthropic\n\n"
                "Ohne Paket kannst du alle Felder manuell ausfüllen.",
            )
        elif ("authentication" in meldung.lower() or "api key" in meldung.lower()
              or "401" in meldung or "kein deepseek_api_key" in meldung.lower()):
            if anbieter() == "deepseek":
                name, beispiel = "DEEPSEEK_API_KEY", "sk-..."
            else:
                name, beispiel = "ANTHROPIC_API_KEY", "sk-ant-..."
            messagebox.showinfo(
                "API-Key",
                f"Kein gültiger API-Key gefunden ({name}).\n\n"
                "Setze ihn in der PowerShell, bevor du das Programm startest:\n\n"
                f'$env:{name} = "{beispiel}"\n\n'
                "Die Erkennung ist nur ein Vorschlag; du kannst alles manuell eintragen.",
            )
        else:
            messagebox.showinfo("Erkennung", f"Erkennung fehlgeschlagen:\n{meldung}")

    def _uebernehme_erkenntnis(self, daten: dict) -> None:
        self.erkennt_gerade = False
        self.erkannt_von_ki = True
        self.erkannt_von_modell = modell_name()
        self.konfidenz = daten.get("konfidenz")
        self.btn_aufnehmen.configure(state="normal")
        self.btn_bild.configure(state="normal")

        self.var_kategorie.set(daten.get("kategorie", "Sonstiges"))
        self.var_bezeichnung.set(daten.get("bezeichnung", ""))
        self.var_wert.set(daten.get("wert", ""))
        self.var_gehaeuse.set(daten.get("gehaeuse", ""))
        self.var_eigenschaften.set("; ".join(daten.get("eigenschaften") or []))
        self.var_aufdruck.set(daten.get("aufdruck", ""))

        stueck = daten.get("anzahl_auf_foto", 1)
        konfidenz = int(round((daten.get("konfidenz") or 0) * 100))
        self.var_status.set(
            f"Vorschlag übernommen (Konfidenz {konfidenz} %"
            + (f", {stueck} Stück im Bild" if stueck > 1 else "")
            + "). Bitte prüfen, Anzahl eintragen, dann speichern."
        )
        self.felder["Bezeichnung"].focus_set()

    def speichern(self) -> None:
        bezeichnung = self.var_bezeichnung.get().strip()
        if not bezeichnung:
            messagebox.showwarning("Bezeichnung", "Bitte eine Bezeichnung eingeben.")
            self.felder["Bezeichnung"].focus_set()
            return

        try:
            anzahl = int(self.var_anzahl.get())
        except (tk.TclError, ValueError):
            anzahl = 0
        if anzahl < 1:
            messagebox.showwarning("Anzahl", "Die Anzahl muss mindestens 1 sein.")
            return

        eigenschaften = [t.strip() for t in self.var_eigenschaften.get().split(";")
                         if t.strip()]
        jetzt = datetime.now().isoformat(timespec="seconds")

        kategorie = self.var_kategorie.get().strip() or "Sonstiges"
        wert = self.var_wert.get().strip()
        gehaeuse = self.var_gehaeuse.get().strip()
        schluessel = (bezeichnung.casefold(), wert.casefold(), gehaeuse.casefold())

        vorhanden = next(
            (e for e in self.eintraege
             if (str(e.get("bezeichnung", "")).casefold(),
                 str(e.get("wert", "")).casefold(),
                 str(e.get("gehaeuse", "")).casefold()) == schluessel),
            None,
        )

        if vorhanden is not None:
            frage = (
                f"„{bezeichnung}“ ist schon im Bestand "
                f"({vorhanden.get('anzahl', 0)} Stück).\n\n"
                f"{anzahl} Stück dazuzählen?"
            )
            if messagebox.askyesno("Bereits vorhanden", frage):
                vorhanden["anzahl"] = int(vorhanden.get("anzahl") or 0) + anzahl
                vorhanden["aktualisiert"] = jetzt
                if self.var_lagerort.get().strip():
                    vorhanden["lagerort"] = self.var_lagerort.get().strip()
                if eigenschaften and not vorhanden.get("eigenschaften"):
                    vorhanden["eigenschaften"] = eigenschaften
                self._nach_dem_speichern()
                return

        eintrag = {
            "id": uuid.uuid4().hex[:8],
            "kategorie": kategorie,
            "bezeichnung": bezeichnung,
            "wert": wert,
            "gehaeuse": gehaeuse,
            "eigenschaften": eigenschaften,
            "aufdruck": self.var_aufdruck.get().strip(),
            "anzahl": anzahl,
            "lagerort": self.var_lagerort.get().strip(),
            "fotos": [],
            "erkannt_von": (self.erkannt_von_modell or modell_name())
            if self.erkannt_von_ki else "manuell",
            "konfidenz": self.konfidenz if self.erkannt_von_ki else None,
            "angelegt": jetzt,
            "aktualisiert": jetzt,
        }
        self.eintraege.append(eintrag)
        self._nach_dem_speichern()

    def _nach_dem_speichern(self) -> None:
        try:
            speichere_daten(self.eintraege)
            schreibe_bestand(self.eintraege)
            schreibe_csv(self.eintraege)
        except Exception as fehler:
            messagebox.showerror("Speichern", f"Speichern fehlgeschlagen:\n{fehler}")
            return
        self._aktualisiere_zaehler()
        self.var_status.set("Gespeichert. Bestand.md und inventar.csv aktualisiert.")
        self.zuruecksetzen(leise=True)

    def zuruecksetzen(self, leise: bool = False) -> None:
        self.var_kategorie.set("Sonstiges")
        self.var_bezeichnung.set("")
        self.var_wert.set("")
        self.var_gehaeuse.set("")
        self.var_eigenschaften.set("")
        self.var_aufdruck.set("")
        self.var_anzahl.set(1)
        self.var_lagerort.set("")
        self.letztes_bilddaten = None
        self.erkannt_von_ki = False
        self.erkannt_von_modell = ""
        self.konfidenz = None
        self.vorschau_aktiv = True
        if not leise:
            self.var_status.set("Felder geleert.")

    def _aktualisiere_zaehler(self) -> None:
        stueck = sum(int(e.get("anzahl") or 0) for e in self.eintraege)
        self.root.title(
            f"Bauteil-Inventar – {len(self.eintraege)} "
            f"{_arten(len(self.eintraege))}, {stueck} Stück"
        )

    def _schliessen(self) -> None:
        self.laeuft = False
        if self.vorschau_job is not None:
            try:
                self.root.after_cancel(self.vorschau_job)
            except Exception:
                pass
            self.vorschau_job = None
        self.kamera_token += 1
        self._kamera_freigeben()
        self.root.destroy()


# ---------------------------------------------------------------- Start

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bauteil-Inventar mit Kamera, Stream oder Bilddatei"
    )
    parser.add_argument("--kamera", type=int, default=None,
                        help="Kamera-Index (0 = meist eingebaute Kamera, 1 = USB …)")
    parser.add_argument("--quelle", default=None,
                        help="Kamera-Index oder Stream-URL; hat Vorrang vor --kamera")
    parser.add_argument("--nur-md", action="store_true",
                        help="nur Bestand.md und inventar.csv neu erzeugen")
    args = parser.parse_args()

    if args.nur_md:
        eintraege = lade_daten(gui=False)
        schreibe_bestand(eintraege)
        schreibe_csv(eintraege)
        stueck = sum(int(e.get("anzahl") or 0) for e in eintraege)
        print(f"Bestand.md und inventar.csv neu geschrieben: "
              f"{len(eintraege)} Arten, {stueck} Stück.")
        return

    if cv2 is None:
        print("Hinweis: opencv-python fehlt. Es geht nur die manuelle Eingabe.")
        print("Installieren: python -m pip install opencv-python")
    if Image is None:
        print("Hinweis: Pillow fehlt. Die Kameravorschau bleibt leer.")
        print("Installieren: python -m pip install Pillow")

    if args.quelle is not None:
        quelle = args.quelle
    elif args.kamera is not None:
        quelle = str(args.kamera)
    else:
        quelle = "0"

    root = Tk()
    InventarApp(root, quelle)
    root.mainloop()


if __name__ == "__main__":
    main()
