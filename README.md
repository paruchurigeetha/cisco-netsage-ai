# NetSage AI: Cisco Lab Troubleshooter & Verification Dashboard

[![Deploy to Render](https://render.com/images/deploy-to-render.svg)](https://render.com/deploy?repo=https://github.com/paruchurigeetha/cisco-netsage-ai)

**NetSage AI** is an AI-assisted network troubleshooting assistant designed for Cisco-style lab networks (such as Packet Tracer or real enterprise topologies). It helps junior engineers connect symptoms to root causes by combining **deterministic rule-based validation checks (Python)** with **generative semantic reasoning (LLM)**, while enforcing a **Human-in-the-Loop (Safety Rule)** review before implementing configuration fixes.

This project was built as a submission package for the **Cisco Internship**.

---

## Key Features

1. **Vibrant Dark-Theme Dashboard**: A premium, state-of-the-art visual dashboard displaying real-time statistics of cases (total, concepts, OSI layers, severity, and AI vs. Human agreement rates).
2. **Interactive Network Topology Graph**: A live canvas rendering device layouts (Routers, Switches, PCs, Servers) that dynamically flashes in red and indicates link failures for config mismatches.
3. **AI Council Multi-Agent Consensus Debate**: Simulates specialized agent roles (Infrastructure, Security, Services) debating configurations to produce a combined consensus diagnosis.
4. **Interactive Diagnostics Lab**: A live console showing:
   - Cisco CLI `show` command outputs for 30 distinct real-world failure cases.
   - **Deterministic Python Rule Checker**: Runs instant tests on subnetting, native VLAN tags, interface states, access modes, duplicate IPs, OSPF, and HSRP settings.
   - **Gemini AI Diagnosis Integration**: Automatically drafts Root Cause, Confidence, Evidence quotes, Next Commands, and CLI Fix Steps (supports live API keys or built-in offline mock responses).
5. **Interactive Human Oversight (Safety Rule)**: Allows engineers to Accept, Edit (interactively modifying fields), or Reject AI answers, which updates the database and metrics in real-time.
6. **Programmatic Excel Export**: Automatically updates and exports a formatted Excel spreadsheet (`dashboard.xlsx`) complete with embedded charts, metrics tables, and case logs.
7. **Responsible AI Log**: Documents at least 5 complex edge cases where AI hallucinated or made logical omissions, explaining why human oversight prevented network issues.

---

## Repository Deliverables

The files generated for this submission package include:

| File Name | Deliverable Type | Description |
| :--- | :--- | :--- |
| `cases.csv` | **Case Dataset** | The master dataset of 30 networking troubleshooting cases (covering VLAN, Gateway, DHCP, DNS, Routing, ACL, NAT, and Wireless). |
| `cases_db.json` | **Internal Database** | JSON version of the cases dataset, supporting dynamic front-end state, reviews, and editing. |
| `diagnose_prompt.md` | **AI Prompt Library** | Structured system prompt enforcing JSON formatting, OSI classification guidelines, and worked examples. |
| `rule_checker.py` | **Python Checker** | Deteministic script checking duplicate IPs, subnet mismatches, gateway conflicts, shut interfaces, inactive VLANs, etc. |
| `responsible_ai_log.md` | **Responsible AI Log** | A formal report on the 5 cases where AI was corrected by a human reviewer. |
| `dashboard.xlsx` | **Excel Dashboard** | Professional spreadsheet containing summary metrics, charts, and detailed case records. |
| `app.py` | **Flask Web Server** | Exposes the API endpoints for running checks, triggering Gemini, saving reviews, and compiling reports. |
| `export_dashboard.py` | **Dashboard Generator** | Uses `xlsxwriter` to compile the spreadsheet report programmatically. |
| `run.py` | **Startup Script** | Automates directory setup, launches the server, and opens the dashboard in the browser. |

---

## Installation & Setup

### Prerequisites
- Python 3.8 or higher.
- PIP package manager.

### 1. Install Dependencies
All required libraries are standard and lightweight. Install them using the included `requirements.txt`:
```bash
pip install -r requirements.txt
```
*(Note: Flask, flask-cors, and xlsxwriter are required. Chart.js is loaded in the browser via CDN).*

### 2. Run the Application
Start the NetSage AI engine and launch the dashboard in your default browser with a single command:
```bash
python run.py
```
This script will:
- Check for existing dataset files (compiling them if missing).
- Boot the Flask backend on `http://127.0.0.1:5000/`.
- Open your default web browser automatically.

---

## How It Works: Step-by-Step Workflow

### 1. Inspect Symptom & Topology
Choose any of the **30 cases** from the navigator panel in the **Diagnostics Lab** tab. Each case represents a real-world error scenario (e.g. OSPF duplicate IDs, VTP case-sensitivity mismatches, NAT pools missing subnets, or administrative interface shutdowns) and displays the Cisco CLI outputs.

### 2. Execute Python Rule Checker
Click **"Run Python Rule Checker"**. The application runs the deterministic rules in `rule_checker.py` on the CLI text. If it catches a standard mistake (like a subnet mismatch between PC and Router), it immediately raises a failure flag and displays the exact CLI fix.

### 3. Generate AI Diagnosis
Click **"Diagnose with NetSage AI"**. 
- *Offline Mode (Default)*: Loads the pre-compiled, highly accurate AI diagnosis.
- *Online Mode*: Paste a Gemini API Key in the sidebar key panel. The app will make a live call to the Gemini API, feeding the prompt library and CLI outputs to receive a real-time diagnosis.

### 4. Provide Human Verdict (The Safety Rule)
Review the AI's response. Select a verdict:
- **Accept**: If the AI's diagnosis is 100% correct.
- **Edit & Accept**: If the AI is close but missed a detail. The fields (Root Cause, OSI layer, Fix steps) will become editable text inputs, letting you modify them.
- **Reject**: If the AI is completely incorrect (e.g., confusing duplicate IPs for an STP loop).

Submit your review. The local database will be updated, the metrics on the **Dashboard Overview** will recalculate, and `dashboard.xlsx` will automatically rebuild itself.

---

## Responsible AI: Human Oversight Analysis
Of the 30 cases, **5 cases** are configured to demonstrate AI mistakes:
- **Case 16**: AI fails to catch that Cisco standard ACLs use inverted wildcard masks, treating standard subnet masks as valid.
- **Case 19**: AI misses the NAT source list filter omission and diagnoses it as a routing table bug.
- **Case 22**: AI misinterprets duplicate IP warnings and MAC flaps as an STP loop, which would result in shutting down working trunks.
- **Case 27**: AI claims logical subinterfaces must match the VLAN encapsulation tag and suggests deleting them.
- **Case 28**: AI diagnoses HSRP split-brain (Active/Active) as a physical link failure, recommending cable replacement.

The human-in-the-loop workflow catches these faults, corrects the configurations, and records the explanation in the **Responsible AI Log** (visible on the third tab of the app).
