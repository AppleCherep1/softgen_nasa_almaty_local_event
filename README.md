# Crew Health AutoCheck

**Team SoftGen — NASA Space Apps Challenge 2026, Almaty, Kazakhstan**

Challenge: **Create Health Monitoring Software for Astronauts on Space Missions**.

An autonomous onboard software prototype combining crew health checks, simulated physiological and environmental monitoring, offline voice interaction, emergency guidance, and chronological reporting in one interface. Onboard support and ground medical awareness are complementary: reports are generated as events occur so specialists can review readings and actions after the communication delay.

## Try the prototype

Download this repository and open `crew-heart-check.html` in a modern desktop browser for the self-contained interface and simulation. No model download is needed to explore the nine scenarios. Camera and microphone functionality depend on browser permissions and a secure context; use the local server below for voice AI.

## What is implemented

- Heart, vision and attention checks with local history.
- Two-person spacecraft simulation with nine scenarios: pulse change, possible collapse, possible bleeding, unsafe atmosphere, sensor failure, exercise, sleep, fatigue and vision change.
- Explainable rule-based alerts using simulated signals, context and signal availability.
- Simulated crewmate notifications, assistance workflow and Earth communication queue/delay.
- Incident reports with readings, reasons, responses, actions and timestamps.
- Experimental camera-based pulse estimation (rPPG), not a clinical measurement.
- Optional offline voice pipeline: **Vosk → Qwen via Ollama → validated facts → procedural rules**. The language model extracts reported facts; it does not generate medical decisions.
- English and Russian interface and an in-app list of 49 references.

## Scope and limitations

This is an educational hackathon prototype, not a clinical system or flight-qualified product. Sensor feeds, camera detections, crew movement, notifications and Earth replies in the simulation are synthetic. There is **no operational connection to NASA, ISS equipment, ground control or real crew wearables**. The local server journal stays local; Earth transmission is represented in the simulation, not implemented as a real mission link. Reported timing and benchmark files describe particular test conditions, not validated clinical performance.

## Local voice AI setup

Requires Python 3.11+, a modern browser and Ollama installed locally. Internet is needed initially to download dependencies and models; local operation is possible after installation.

```sh
python -m pip install -r requirements.txt
ollama pull qwen3:4b
```

Ensure Ollama is running at `http://127.0.0.1:11434` (`ollama serve` if needed).

Download Vosk models from https://alphacephei.com/vosk/models and extract them as:

```text
models/vosk-model-small-ru-0.22/
models/vosk-model-small-en-us-0.15/
```

The Russian folder name `vosk-model-small-ru` is also supported. On Windows, `download_vosk.ps1` downloads and extracts both models. Weights and their ZIP archives are intentionally excluded from this repository.

```sh
python server.py
```

Open **http://127.0.0.1:8765/** and allow microphone access. Inspect **http://127.0.0.1:8765/health** for readiness. Initial model loading can take time. The server binds to loopback only; do not expose it as a production medical service. It creates `crew_journal.sqlite3` locally.

Optional model selection on PowerShell:

```powershell
$env:CREW_MODEL = 'qwen3:1.7b'
python server.py
```

The main frontend applies recognized facts automatically with an undo option. `/confirm` is an API operation and does not necessarily represent a separate human confirmation. The backend `/demo` page is an older development interface. `README_RU.md` is preserved development documentation and includes historical behavior and measurements; this README describes the submission's current scope.

## Repository guide

- `crew-heart-check.html`: main self-contained interface and simulation.
- `server.py`, `core.py`, `stt.py`, `guards.py`: local server, extraction, recognition and validation.
- `mission.py`, `scenario.py`, `inventory.json`, `sources.json`: backend development scenario configuration.
- `test_*.py`, `test_ui_contract.js`: supplied development tests; some may target older interfaces.
- `eval_*.jsonl`, `evaluation_*.json`, `benchmark_*.json`: development test cases and recorded results, not clinical validation.
- `README_RU.md`: detailed historical development notes in Russian.

Run supplied Python tests with `python -m unittest discover -v`. Voice/model evaluations require the separately installed models. Read test results in context; no successful end-to-end hardware validation is claimed.

## Scientific and technical basis

- [NASA Autonomous Medical Operations](https://www.nasa.gov/directorates/stmd/game-changing-development-program/autonomous-medical-operations-amo/)
- [CSA Bio-Monitor](https://www.asc-csa.gc.ca/eng/sciences/bio-monitor.asp)
- [NASA Environmental Data App](https://visualization.osdr.nasa.gov/eda/)
- [NASA CIPHER](https://www.nasa.gov/reference/cipher/)
- The main application contains the complete collected reference list. Sources motivate the concept; they do not validate this prototype or imply endorsement.

## Team and tools

Team SoftGen: Raibekov Zhansultan and Baizhanuly Bauyrzhan.

Python, HTML, JavaScript, Three.js, Vosk and Qwen/Ollama. Claude and ChatGPT assisted development and content preparation. Third-party software and models retain their respective licenses; no NASA endorsement is implied.

## Next steps

Integrate real sensors through device-specific adapters, evaluate voice robustness and false alerts, and review workflows with medical specialists before considering operational use.
