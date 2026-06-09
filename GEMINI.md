# 🏛️ PROIECT TOMIS.AI - Context Instrucțional Core (V2 - Iunie 2026)

## 📋 Prezentare Generală
TOMIS.AI este un ecosistem de calcul distribuit hibrid (Windows/Linux/Edge) bazat pe K3s și Docker, specializat în procesare AI multi-modală de înaltă fidelitate. Arhitectura este axată pe portabilitate supremă, funcționare offline și management autonom al resurselor.

## 🏗️ Arhitectură "Unified 3-Script"
Întreg sistemul este gestionat prin exact 3 scripturi inteligente, auto-generative:
1.  **`Start-Deploy.bat`**: Interfața universală de lansare (Windows).
2.  **`Deploy-Cluster.ps1`**: Motorul de execuție și configurare (Windows/WSL2).
3.  **`Start-Deploy.sh`**: Scriptul universal pentru Unix (Linux/Edge/Pi5/Jetson).

## 🧠 Capabilități AI Avansate
- **Whisper ASR (Port 28002):** Transcriere cu **Consensus Engine** (verificare pe 2+ noduri) și detecție limbă în 3 puncte (Start/Mid/End).
- **Universal OCR (Port 28003):** Toate limbile suportate, detecție automată sau parametrizată.
- **Vision Engine (Port 28004):** Clasificare obiecte (YOLOv8) și recunoaștere facială (DeepFace). Include timestamping video și procesare stream în timp real.
- **TTS Natural (Port 28005):** Sinteză vocală naturală (XTTS-v2) pentru RO și EN.
- **LPR Engine (Port 28006):** Recunoaștere plăcuțe auto.
- **Voice Fingerprint (Port 28007):** Identificare vorbitor (Speaker Verification).
- **Offline Routing (Port 28008):** Rutare auto globală/regională via GraphHopper și hărți OpenStreetMap (.pbf).
- **Network Forensics (Port 28009):** Analiză automată fișiere `.pcap` (Zeek/Tshark).
- **LLM Engine (Port 28010):** Ollama cu modele Gemma 2 (9B/27B) și Llama 3.
- **Romanian Stack (Ports 28011-28014):** NER, NLP, RAG (ChromaDB) și Private GPT optimizate exclusiv pentru limba română.

## ⚓ Armonizarea Porturilor (Consecutive)
- **28001**: Master Dashboard (Bootstrap 5 UI).
- **28002 - 28015**: Servicii AI Microservices (vezi mai sus).

## 📺 Identitate Vizuală și Stealth
- **Screensaver V22.1 HD:** Animație "Neural Explosion" (OLED Safe, sub #444).
- **Orchestrare Activă:** Execută `uncordon` la pornire și `cordon` la ieșire (mouse/tastă).
- **Anti-Standby:** Forțează sistemul să rămână activ (`WAKE: ACTIVE`) pe durata procesării.
- **Dashboard Discret:** Statistici persistente (Now/Session/Lifetime) cu drift orizontal.

## 🛠️ Convenții de Operare
- **Container-Centric:** Pe Windows, procesarea rulează EXCLUSIV în Docker. Fără instalări locale de modele sau Python masiv.
- **Offline Ready:** Opțiunea `GENERATE KIT` creează structuri `Tomis.AI.Master` și `Tomis.AI.Nod` gata de stick USB.
- **Modularitate:** `extra.sh` permite extinderea Master-ului fără a modifica nucleul.
- **Git Sync:** Orice modificare este sincronizată automat pe GitHub.

---
*Acest fișier servește drept context permanent pentru agentul AI Gemini în gestionarea și extinderea ecosistemului TOMIS.AI.*
