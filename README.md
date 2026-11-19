# CyberSwarm

An adversarial purple-team lab: an LLM **Red** agent (external, black-box) and an LLM **Blue**
agent (internal, white-box) play repeated rounds in an isolated Docker network. After each round
each side learns through reflection, memory and a cross-agent **debrief**. Suricata gives Blue
"perception" over the traffic.

**Central claim:** agents that exchange debriefs improve faster than agents that only learn from
themselves (measured by the E2 ablation).

> School mini-project (Cybersecurity & Privacy). Everything runs locally on our own machine
> against our own intentionally weak app. The lab has **no internet egress**.

---

## Quick start

### 0. Prerequisites
- Docker Desktop (Windows/Linux/macOS)
- Python 3.12 on the host
- A local model server with tool calling, OpenAI-compatible. Easiest: **Ollama**.

```powershell
ollama pull qwen3:14b
ollama serve          # exposes http://localhost:11434/v1
```

### 1. Install the orchestrator deps
```powershell
cd orchestrator
pip install -r requirements.txt
```

### 2. Bring the lab up by hand once (to grab the Ping + Wireshark screenshots)
```powershell
cd ../lab
docker compose up -d --build
docker exec cs_redbox ping -c 3 10.10.2.10        # ping crosses the gateway
docker exec cs_gateway tcpdump -i any -w /var/log/suricata/capture.pcap    # open in Wireshark
```
The pcap appears in `lab/logs/capture.pcap` (mounted to the host).

### 3. Run an experiment
```powershell
cd ../orchestrator
python main.py --config ../config/experiment.yaml
```
Per-round scores and logs land in `runs/<run_name>/`. Ctrl-C is the kill switch.

### 4. Figures + ablation table
```powershell
cd ../analysis
python plot_curves.py ../runs/baseline ../runs/no_learning
```

---

## The 2-night plan

**Night 1**
- *A:* lab — compose, gateway routing, Flask app (SQLi only), db+flag, traffic-gen, Suricata. Grab Ping + Wireshark screenshots as soon as routing works.
- *B:* Ollama + Qwen, the tools, `guard.py`, agent loop against a running lab with `--no-lab`.

**Night 2**
- Together: referee + scoring, one full round end to end, **record the backup video**.
- Reflection + playbook + debrief (all already scaffolded; flip the flags in `experiment.yaml`).
- Mini-ablation: `baseline` (all learning) vs `no_learning`, ~5 rounds each, one chart.
- Report + slides.

**Cut for time (list as future work):** the ML/RandomForest IDS layer, the Streamlit dashboard,
E3/E4, and 3–5 repeats per config.

---

## The E2 ablation (the headline result)

Run the same lab with different `learning:` flags, giving each run its own `run_name`:

| run_name | reflection | memory | debrief |
|---|---|---|---|
| `none` | false | false | false |
| `reflect` | true | false | false |
| `reflect_mem` | true | true | false |
| `baseline` | true | true | true |

Then `plot_curves.py` overlays the curves and prints the ablation table.

---

## Layout
```
config/experiment.yaml     # rounds, budgets, learning flags, model
lab/                       # docker-compose + gateway/webapp/db/red-box/traffic-gen
orchestrator/
  main.py referee.py guard.py
  agents/   base.py red.py blue.py
  tools/    red_tools.py blue_tools.py
  learning/ reflection.py memory.py debrief.py
  telemetry/ingest.py
analysis/plot_curves.py
runs/                      # per-run outputs (gitignored)
report/                    # figures, screenshots, the PDF
```

## Safety (for the report)
- Lab networks are `internal: true` → no internet egress. LLM calls leave only from the host.
- `guard.py` rejects any target outside `10.10.0.0/16`, regardless of what the model asks, plus
  per-round call budgets and output caps.
- No denial-of-service tooling in Red's toolset.
- The app is ours and intentionally weak; every round starts from clean images.
