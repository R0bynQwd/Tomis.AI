# 🏛️ PROIECT TOMIS.AI - Context Instrucțional Core

## 📋 Prezentare Generală
TOMIS.AI este un ecosistem de calcul distribuit hibrid (Windows/Linux/Edge) bazat pe K3s și Docker, specializat în procesare AI multi-modală (Whisper ASR, OCR, Vision, NLP). Arhitectura este axată pe portabilitate supremă, funcționare offline și management adaptiv al resurselor.

## 🏗️ Arhitectură și Tehnologii
- **Orchestrare:** K3s (Lightweight Kubernetes).
- **Execuție:** Docker Desktop (Windows) / Containerd (Linux).
- **Frontend Master:** Dashboard Flask pe portul `28001`.
- **Interfață Noduri:** Screensaver Python (Pygame-CE) cu logica de Cordon/Uncordon.
- **Sincronizare:** `config.json` pentru IP și Token Master.
- **Modele AI:** Whisper (Consensus Engine), OCR (All-languages), YOLOv8 (Vision), SpeechBrain.

## 🚀 Comenzi de Operare (Cele 3 Scripturi)

### 1. Windows (Lansare și Noduri)
- **`Start-Deploy.bat`**: Punctul de intrare universal. Meniu interactiv pentru:
  - `[1]` Instalare Master Windows (Experimental).
  - `[2]` Instalare Nod (Conectare automată via `config.json`).
  - `[3]` Generare kit-uri portabile (`Tomis.AI.Master` / `Tomis.AI.Nod`).
  - `[4]` Actualizare modele AI locale.

### 2. Linux / Unix / Edge
- **`sudo bash Start-Deploy.sh`**: Scriptul universal pentru Master sau Nod Linux.
  - Automatizează instalarea K3s, NFS Server și Dashboard-ul Master.
  - Detectează arhitectura (ARM64 pentru Pi5/Jetson, x86_64 pentru servere).

### 3. Modul de Extensie (Master)
- **`extra.sh`**: Script modular chemat de `Start-Deploy.sh`. Permite adăugarea de noi module (Security, RAG, custom models) fără a altera nucleul.

## 🛠️ Convenții de Dezvoltare
- **Offline First:** Toate scripturile trebuie să verifice `Test-Internet` și să utilizeze `Kit_AI_Offline` dacă conexiunea lipsește.
- **Container-Centric:** Pe Windows, nu se instalează module AI locale. Totul rulează în Docker.
- **Stealth Aesthetic:** Interfețele grafice (Screensaver, Dashboard) respectă tema "Deep Black" și branding-ul grecesc **ΤΟΜΙΣ.ΑΙ**.
- **Logging:** Orice acțiune majoră trebuie logată în `deployment_log.txt`.

## 📡 Managementul Sarcinilor
Sarcinile sunt transmise către Master via API (port 28001):
- **OCR:** `POST /api/ocr` (Detectare automată limbă).
- **Whisper:** `POST /api/asr` (Verificare prin consens pe 2+ noduri).
- **Vision:** `POST /api/vision` (Clasificare obiecte).

---
*Acest fișier servește drept context permanent pentru agentul AI Gemini în gestionarea proiectului TOMIS.AI.*
