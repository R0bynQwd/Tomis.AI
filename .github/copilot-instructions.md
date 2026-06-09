# Copilot Instructions for TOMIS.AI

## Build, test, and lint commands

This repository is orchestration-first (scripts + runtime manifests). There is no dedicated unit-test framework or lint pipeline configured in the repo.

### Primary run commands

- **Windows (menu-driven):**
  - `E:\NAI\Start-Deploy.bat`
- **Windows (direct role execution):**
  - `powershell -NoProfile -ExecutionPolicy Bypass -File E:\NAI\Deploy-Cluster.ps1 -Role MASTER`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File E:\NAI\Deploy-Cluster.ps1 -Role NODE`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File E:\NAI\Deploy-Cluster.ps1 -Role EMULATE`
- **Linux/Edge (menu-driven):**
  - `sudo bash E:\NAI\Start-Deploy.sh`

### Validation/smoke commands used in this repo

- **PowerShell syntax check:**
  - `$null = [scriptblock]::Create((Get-Content 'E:\NAI\Deploy-Cluster.ps1' -Raw))`
- **Python syntax check (single file):**
  - `python -m py_compile E:\NAI\TomisDashboard.py`
- **Python syntax check (multiple core files):**
  - `python -m py_compile E:\NAI\TOMIS_Screensaver.py E:\NAI\TomisDashboard.py`
- **Dashboard smoke check:**
  - `Invoke-WebRequest -Uri 'http://<master-physical-ip>:28001/stats' -UseBasicParsing -TimeoutSec 8`
- **Cluster smoke check:**
  - `kubectl get nodes -o wide`
  - `kubectl get pods -A`

## High-level architecture

- The platform is built around a **Unified 3-Script architecture**:
  1. `Start-Deploy.bat` (Windows entrypoint/menu)
  2. `Deploy-Cluster.ps1` (Windows orchestration engine)
  3. `Start-Deploy.sh` (Linux/Edge orchestration engine)

- `Deploy-Cluster.ps1` and `Start-Deploy.sh` are **auto-generative**:
  - they generate/update `TOMIS_Screensaver.py` and `TomisDashboard.py`
  - they maintain runtime state files such as `config.json`, `task_emulation.json`, `node_stats.txt`, and `deployment_log.txt`

- Runtime model:
  - **MASTER** provisions cluster/dashboard and emits `config.json` with connection coordinates
  - **NODE** joins cluster using `config.json` and participates in orchestration
  - **EMULATE** starts local task emulation (`TOMIS_TaskEmulator.py`) so dashboard/task statistics are visible even when K8s is unavailable

- Service exposure:
  - `28001` dashboard
  - `28002+` AI services via NodePort manifests (`tomis-ai-stack.yaml`, optional `extra.sh` stack)

## Key conventions specific to this codebase

- **Physical NIC IPs only for master addressing**: avoid loopback/localhost for node coordination. The Windows deploy logic explicitly resolves non-virtual IPv4 interfaces.
- **Container-centric Windows execution**: orchestration assumes Docker Desktop + k3d/kubectl availability; failures in Docker engine directly impact cluster health and dashboard K8s fields.
- **GUI-aware screensaver behavior**:
  - GUI present => screensaver is launched and controls active-node orchestration semantics
  - headless systems => node should remain active without requiring screensaver UI
- **State and telemetry are file-backed**:
  - `task_emulation.json` and `node_stats.txt` are authoritative for emulated/live task counters
  - dashboard and screensaver both read these files for consistent statistics
- **Script-generated code is canonical in practice**:
  - when changing screensaver/dashboard behavior, mirror updates both in generated target files and in generator sources (`Deploy-Cluster.ps1`, `Start-Deploy.sh`) to prevent regressions on next deploy run.
