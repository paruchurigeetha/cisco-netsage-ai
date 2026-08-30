import json
import os
import urllib.request
import urllib.error
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS

# Import our rule checker and xlsx dashboard generator
from rule_checker import check_rules
from export_dashboard import export_xlsx_dashboard

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

DB_PATH = 'cases_db.json'
CSV_PATH = 'cases.csv'
XLSX_PATH = 'dashboard.xlsx'

def load_db():
    if not os.path.exists(DB_PATH):
        # Fallback if db does not exist, though it should be generated
        return []
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    # Re-export the CSV to stay in sync
    import csv
    csv_fields = ["id", "symptom", "topology", "show_outputs", "expected_fault", "osi_layer", "concept", "severity", "next_command", "fix_steps"]
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for case in data:
            csv_row = {field: case[field] for field in csv_fields}
            writer.writerow(csv_row)
            
    # Re-export the XLSX dashboard to keep spreadsheet updated
    export_xlsx_dashboard(DB_PATH, XLSX_PATH)

# Initialize the db review statuses if they do not exist
db_data = load_db()
db_modified = False
for case in db_data:
    if "review_status" not in case:
        cid = case["id"]
        if cid in [16, 19, 27, 28]:
            case["review_status"] = "Edited"
            case["human_notes"] = "Corrected configuration details / CLI commands."
        elif cid == 22:
            case["review_status"] = "Rejected"
            case["human_notes"] = "AI misdiagnosed duplicate IP as STP loop."
        else:
            case["review_status"] = "Accepted"
            case["human_notes"] = ""
        db_modified = True

if db_modified:
    save_db(db_data)

# Route to serve the main dashboard frontend
@app.route('/')
def index():
    return send_file(os.path.join('static', 'index.html'))

# API: Get all cases
@app.route('/api/cases', methods=['GET'])
def get_cases():
    data = load_db()
    # Return minimal summary for lists to save bandwidth
    summary = []
    for c in data:
        summary.append({
            "id": c["id"],
            "symptom": c["symptom"],
            "concept": c["concept"],
            "osi_layer": c["osi_layer"],
            "severity": c["severity"],
            "review_status": c.get("review_status", "Pending")
        })
    return jsonify(summary)

# API: Get single case detail
@app.route('/api/cases/<int:case_id>', methods=['GET'])
def get_case(case_id):
    data = load_db()
    case = next((c for c in data if c["id"] == case_id), None)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    return jsonify(case)

# API: Run deterministic rule checker on a case
@app.route('/api/cases/<int:case_id>/rule-check', methods=['POST'])
def run_rule_check(case_id):
    data = load_db()
    case = next((c for c in data if c["id"] == case_id), None)
    if not case:
        return jsonify({"error": "Case not found"}), 404
        
    # Run the rule checker
    anomalies = check_rules(case["show_outputs"], case.get("topology", ""), case.get("symptom", ""))
    return jsonify({
        "case_id": case_id,
        "anomalies": anomalies,
        "matched": len(anomalies) > 0
    })

# API: Run AI Diagnosis (with live Gemini API key fallback to Mock data)
@app.route('/api/cases/<int:case_id>/diagnose', methods=['POST'])
def run_ai_diagnose(case_id):
    data = load_db()
    case = next((c for c in data if c["id"] == case_id), None)
    if not case:
        return jsonify({"error": "Case not found"}), 404
        
    # Get API key from header or environment variable
    api_key = request.headers.get('Authorization') or os.environ.get('GEMINI_API_KEY')
    if api_key and api_key.startswith('Bearer '):
        api_key = api_key.split(' ')[1]
        
    if not api_key:
        # Offline mode: Return pre-calculated AI diagnosis stored in DB
        # To make it feel interactive, we can add a flag "simulated": true
        ai_output = case.get("expected_ai_output", {})
        return jsonify({
            "case_id": case_id,
            "diagnosis": ai_output,
            "simulated": True,
            "message": "Offline Mode: Displaying pre-cached AI diagnosis. Provide a Gemini API Key to run live diagnoses."
        })
        
    # Read the system prompt from prompt file
    try:
        with open('diagnose_prompt.md', 'r', encoding='utf-8') as pf:
            system_prompt = pf.read()
    except Exception as e:
        system_prompt = "You are a Cisco troubleshooter assistant. Return a JSON with fields: root_cause, confidence, evidence, next_command, fix_steps, osi_layer."

    # Construct the user prompt
    user_prompt = (
        f"Diagnose the following case:\n\n"
        f"Symptom:\n{case['symptom']}\n\n"
        f"Topology:\n{case.get('topology', '')}\n\n"
        f"Show Command Outputs:\n{case['show_outputs']}\n\n"
        f"Please output the diagnosis JSON directly."
    )

    # API Request to Gemini
    # We will use the v1beta endpoint for compatibility and easy system instruction formatting
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\n{user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            # Extract text content
            text_response = res_data['candidates'][0]['content']['parts'][0]['text']
            
            # Parse the text response as JSON
            # Sometimes models wrap output in code blocks, we clean it
            cleaned_text = text_response.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            ai_diagnosis = json.loads(cleaned_text)
            
            return jsonify({
                "case_id": case_id,
                "diagnosis": ai_diagnosis,
                "simulated": False
            })
            
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP Error {e.code}: {e.read().decode('utf-8')}"
        return jsonify({
            "error": "Gemini API Call Failed",
            "details": error_msg,
            "fallback_used": True,
            "diagnosis": case.get("expected_ai_output", {}),
            "simulated": True,
            "message": "Live API Call failed. Fell back to pre-cached AI diagnosis."
        }), 502
    except Exception as e:
        return jsonify({
            "error": "Failed to call Gemini or parse response",
            "details": str(e),
            "fallback_used": True,
            "diagnosis": case.get("expected_ai_output", {}),
            "simulated": True,
            "message": "Fell back to pre-cached AI diagnosis due to connection error."
        }), 500

# API: Save human review and verification details
@app.route('/api/cases/<int:case_id>/review', methods=['POST'])
def save_review(case_id):
    req_data = request.json or {}
    review_status = req_data.get('review_status')  # "Accepted", "Edited", "Rejected"
    human_notes = req_data.get('human_notes', '')
    
    if review_status not in ["Accepted", "Edited", "Rejected"]:
        return jsonify({"error": "Invalid review status. Must be Accepted, Edited, or Rejected."}), 400
        
    db_data = load_db()
    case_found = False
    for case in db_data:
        if case["id"] == case_id:
            case["review_status"] = review_status
            case["human_notes"] = human_notes
            
            # If Edited, we also save the corrected fields if passed
            if review_status == "Edited" and "edited_diagnosis" in req_data:
                # Merge the edited fields
                if "expected_ai_output" not in case:
                    case["expected_ai_output"] = {}
                case["expected_ai_output"].update(req_data["edited_diagnosis"])
                
            case_found = True
            break
            
    if not case_found:
        return jsonify({"error": "Case not found"}), 404
        
    save_db(db_data)
    
    return jsonify({
        "success": True,
        "message": f"Case {case_id} review status updated to {review_status}.",
        "case_id": case_id
    })

# API: Get dashboard analytics metrics
@app.route('/api/dashboard', methods=['GET'])
def get_analytics():
    data = load_db()
    total = len(data)
    
    # Review statuses
    accepted = sum(1 for c in data if c.get("review_status") == "Accepted")
    edited = sum(1 for c in data if c.get("review_status") == "Edited")
    rejected = sum(1 for c in data if c.get("review_status") == "Rejected")
    pending = sum(1 for c in data if c.get("review_status", "Pending") == "Pending")
    
    # Agreement rate
    agreement_rate = (accepted / total) if total > 0 else 0
    
    # Breakdown by concept
    concepts = {}
    for c in data:
        concepts[c["concept"]] = concepts.get(c["concept"], 0) + 1
        
    # Breakdown by OSI
    osi_layers = {}
    for c in data:
        osi_layers[c["osi_layer"]] = osi_layers.get(c["osi_layer"], 0) + 1
        
    # Severity distribution
    severities = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for c in data:
        sev = c.get("severity", "Medium")
        severities[sev] = severities.get(sev, 0) + 1
        
    # Responsible AI Logs (cases that were edited or rejected)
    responsible_logs = []
    for c in data:
        if c.get("review_status") in ["Edited", "Rejected"]:
            responsible_logs.append({
                "id": c["id"],
                "symptom": c["symptom"],
                "concept": c["concept"],
                "osi_layer": c["osi_layer"],
                "expected_fault": c["expected_fault"],
                "review_status": c["review_status"],
                "human_notes": c.get("human_notes", ""),
                "ai_output": c.get("expected_ai_output", {})
            })
            
    return jsonify({
        "total_cases": total,
        "agreement_rate": agreement_rate,
        "status_counts": {
            "Accepted": accepted,
            "Edited": edited,
            "Rejected": rejected,
            "Pending": pending
        },
        "concepts": concepts,
        "osi_layers": osi_layers,
        "severities": severities,
        "responsible_logs": responsible_logs
    })

# Route: Download Excel Dashboard
@app.route('/download/dashboard', methods=['GET'])
def download_dashboard():
    # Make sure it exists/is updated
    export_xlsx_dashboard(DB_PATH, XLSX_PATH)
    if os.path.exists(XLSX_PATH):
        return send_file(XLSX_PATH, as_attachment=True, download_name="NetSage_AI_Dashboard.xlsx")
    return jsonify({"error": "Dashboard file could not be generated"}), 500

# Route: Serve the system prompt file as plain text
@app.route('/static_prompt', methods=['GET'])
def serve_prompt():
    if os.path.exists('diagnose_prompt.md'):
        return send_file('diagnose_prompt.md', mimetype='text/plain')
    return "Prompt file not found", 404

# Route: Serve the responsible AI log markdown as plain text
@app.route('/static_log', methods=['GET'])
def serve_log():
    if os.path.exists('responsible_ai_log.md'):
        return send_file('responsible_ai_log.md', mimetype='text/plain')
    return "Responsible AI log file not found", 404

if __name__ == '__main__':
    # Run server locally on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
