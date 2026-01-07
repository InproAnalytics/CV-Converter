# CV-Converter

## Beschreibung
Ein Tool zur Extraktion von Text aus PDF-Lebensläufen und zur Umwandlung in strukturiertes JSON mithilfe der **ChatGPT API**.  
Das JSON folgt einem vordefinierten Schema und kann zur Befüllung von Standard-CV-Templates verwendet werden.

---

## Projektstruktur

```

CV-Converter/
│
├── .env
├── .gitignore
├── app.py
├── main.py
├── pdf\_processor.py
├── chatgpt\_client.py
├── utils.py
├── requirements.txt
├── README.md
│
├── data\_input/       # Eingabedateien (PDFs)
│   └── CV\_Kunde\_1.pdf
│
└── data\_output/      # Ergebnisse (JSON)
└── result.json

````

---

## ⚙️ Installation und Ausführung

### 1. Virtuelle Umgebung erstellen
```bash
python -m venv .venv
````

### 2. Umgebung aktivieren

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate
```

**Linux/Mac (bash):**

```bash
source .venv/bin/activate
```

ERROR: dependencies were not installed:

In VS Code press: Ctrl + Shift + P
Type and select: Python: Select Interpreter
From the list choose:
.venv — Python 3.12.1 (or similar)


### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. `.env` konfigurieren

Erstelle eine `.env` Datei im Projekt-Root mit folgendem Inhalt:

```
OPENAI_API_KEY=sk-...
```

### 5. Projekt starten

```bash
python main.py
```

Das Ergebnis wird in `data_output/result.json` gespeichert.

---

## 📦 requirements.txt

```txt
openai
pdfplumber
python-dotenv
```

Optionale Pakete:

* `pandas` — für Tabellen/JSON-Verarbeitung
* `typer` — CLI Interface
* `tqdm` — Fortschrittsbalken bei Batch-Verarbeitung

---

## 🔐 Umgang mit Secrets

Die `.env` Datei darf nicht ins Repository gelangen.
Daher in `.gitignore` eintragen:

```
.env
```

---

## 🧠 Komponenten

* **`main.py`** — Orchestrator: PDF → GPT → JSON
* **`pdf_processor.py`** — Extraktion von Text aus PDF
* **`chatgpt_client.py`** — Anfrage an ChatGPT API, Parsing der Antwort
* **`utils.py`** — Speichern von JSON-Dateien
* **`requirements.txt`** — Abhängigkeiten
* **`README.md`** — Dokumentation

---

## 💰 Kosten

* Ein durchschnittliches CV kostet **ca. 0.05–0.08 USD** pro Anfrage.
* Die Kosten hängen von Textlänge und JSON-Größe ab.
* Optimierungsmöglichkeiten:

  * PDF seitenweise oder blockweise verarbeiten
  * Ausgabe-Tokens begrenzen
  * Schema schlanker halten

---

## ✅ Ergebnis

* PDF wird in JSON konvertiert
* JSON wird in `data_output/` gespeichert
* Das Schema entspricht den Standard-CV-Templates

```


