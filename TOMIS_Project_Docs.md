# 🏛️ PROIECT TOMIS.AI - Cluster AI Hibrid, Portabil și Autonom
**Documentație Tehnică Consolidată pentru NotebookLM (Iunie 2026)**

---

## 1. Conceptul "Unified 3-Script" Arhitecture
Sistemul TOMIS.AI a fost condensat într-o arhitectură minimalistă formată din exact 3 scripturi inteligente care gestionează întreg ciclul de viață al clusterului AI, indiferent de sistemul de operare (Windows, Linux, Unix, Edge):

1.  **`Start-Deploy.bat`**: Punctul de intrare universal pentru Windows.
2.  **`Deploy-Cluster.ps1`**: Motorul de execuție și configurare pentru platformele Microsoft.
3.  **`Start-Deploy.sh`**: Scriptul universal pentru Unix (Ubuntu, Debian, Pi5, Jetson Nano).

Aceste scripturi sunt **auto-generative**: ele conțin codul sursă pentru componentele secundare (cum este Screensaver-ul Python) și îl pot extrage automat pe disc la nevoie.

---

## 2. Roluri și Automatizare Plug-and-Play
Sistemul funcționează pe baza a două roluri principale, detectate sau selectate de utilizator:

### 👑 Rolul de MASTER (Inima Clusterului)
*   **Instalare:** Configurează K3s Server și un server NFS pentru partajarea modelelor AI (Varianta B).
*   **Inteligență:** Extrage automat IP-ul local și Token-ul de securitate.
*   **Export:** Generează automat fișierul `config.json` care conține coordonatele necesare nodurilor pentru conectare.
*   **Învățare:** Include pipeline-ul de fine-tuning duminical pentru modelele Whisper/Dialect.

### 👷 Rolul de NOD (Puterea de Calcul)
*   **Adaptivitate:** Detectează automat dacă sistemul are GPU NVIDIA (instalează CUDA/Drivers) sau doar CPU.
*   **Conectivitate:** Caută fișierul `config.json` generat de Master. Dacă îl găsește, se conectează la cluster cu **zero intervenție manuală**.
*   **Orchestrare:** Implementează Screensaver-ul TOMIS ca trigger tehnic pentru procesare.

---

## 3. TOMIS Neural Visualizer (Stealth V15.2 HD)
Screensaver-ul nu este doar un element estetic, ci o componentă critică de management al resurselor:
- **Tehnologie:** Python + Pygame-CE (High-Definition Rendering).
- **Vizual:** Constelație de stele în culori "Deep Stealth" care explodează în RGB la activitate AI.
- **Logica Cordon/Uncordon:**
    *   **Activ:** Nodul devine vizibil în cluster (`uncordon`) doar când animația rulează.
    *   **Inactiv:** La orice mișcare de mouse sau tastă, nodul este blocat (`cordon`), eliberând resursele pentru utilizator.
- **Dashboard:** Afișează în timp real starea Master-ului, containerele Docker active și numărul de sarcini (Curente, Sesiune, Lifetime).

---

## 4. Portabilitate și Utilizare Offline
Sistemul poate genera structuri de directoare gata de pus pe stick USB:
- **`Tomis.AI.Master`**: Kit-ul complet pentru instalarea unui creier de rețea.
- **`Tomis.AI.Nod`**: Kit-ul pre-configurat (conține deja IP-ul Master-ului) pentru instalarea rapidă a puterii de calcul pe orice alt PC, fără a necesita internet.

---

## 5. Resurse și Referințe
- **Resurse minime:** 4GB RAM, CPU Quad-Core.
- **Resurse recomandate:** 16GB RAM, NVIDIA RTX 3060+ (pentru Whisper Large V3).
- **Link-uri sursă:**
    *   [K3s Documentation](https://docs.k3s.io/)
    *   [NVIDIA WSL2 Guide](https://docs.nvidia.com/cuda/wsl-user-guide/)
    *   [Pygame Community](https://pyga.me/)

---
*Creat de AI Collaborator pentru ecosistemul de calcul distribuit TOMIS.AI.*
