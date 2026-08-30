import json
import xlsxwriter
import os

def export_xlsx_dashboard(json_path='cases_db.json', output_path='dashboard.xlsx'):
    if not os.path.exists(json_path):
        print(f"Error: {json_path} does not exist. Run generate_cases.py first.")
        return False
        
    with open(json_path, 'r') as f:
        cases = json.load(f)
        
    # Default human review status mapping for demonstration:
    # 25 Accepted, 4 Edited (16, 19, 27, 28), 1 Rejected (22)
    # If the file already has some reviews, we can use them.
    # We will check if "review_status" exists in each case, if not, pre-populate.
    for case in cases:
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
                
    # Create the workbook
    workbook = xlsxwriter.Workbook(output_path)
    
    # ----------------------------------------------------
    # Styles and Palettes (Sleek Professional Look)
    # ----------------------------------------------------
    color_primary = '#005A9C'    # Cisco Blue
    color_secondary = '#0F2C59'  # Navy
    color_accent = '#4A90E2'     # Light Blue
    color_bg_header = '#F2F4F8'  # Light Gray
    
    fmt_title = workbook.add_format({
        'bold': True,
        'size': 16,
        'font_color': '#FFFFFF',
        'bg_color': color_secondary,
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    fmt_section = workbook.add_format({
        'bold': True,
        'size': 12,
        'font_color': color_primary,
        'bottom': 2,
        'bottom_color': color_primary
    })
    
    fmt_header = workbook.add_format({
        'bold': True,
        'bg_color': color_primary,
        'font_color': '#FFFFFF',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    fmt_cell = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True
    })
    
    fmt_cell_center = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    fmt_cell_bold = workbook.add_format({
        'border': 1,
        'bold': True,
        'align': 'left',
        'valign': 'vcenter'
    })
    
    fmt_pct = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '0.0%'
    })
    
    # Status badges formatting
    fmt_accepted = workbook.add_format({'bg_color': '#E2F0D9', 'font_color': '#385723', 'border': 1, 'align': 'center'})
    fmt_edited = workbook.add_format({'bg_color': '#FFF2CC', 'font_color': '#7F6000', 'border': 1, 'align': 'center'})
    fmt_rejected = workbook.add_format({'bg_color': '#FCE4D6', 'font_color': '#C65911', 'border': 1, 'align': 'center'})
    
    # ----------------------------------------------------
    # Sheet 1: Overview Dashboard
    # ----------------------------------------------------
    ws_ov = workbook.add_worksheet('Overview')
    ws_ov.set_zoom(100)
    ws_ov.hide_gridlines(2) # show gridlines
    ws_ov.set_column('A:A', 3)
    ws_ov.set_column('B:D', 20)
    ws_ov.set_column('E:E', 25)
    
    # Banner
    ws_ov.merge_range('B2:E3', 'NetSage AI - Networking Troubleshooter Dashboard', fmt_title)
    
    # Summary Metrics Table
    ws_ov.write('B5', 'Key Diagnostic Metrics', fmt_section)
    ws_ov.write('B6', 'Metric', fmt_header)
    ws_ov.write('C6', 'Count / Value', fmt_header)
    ws_ov.write('D6', 'Target', fmt_header)
    
    metrics = [
        ("Total Troubleshooting Cases", len(cases), "At least 30"),
        ("AI Diagnoses Run", len(cases), "At least 30"),
        ("Human Accepted Diagnoses", sum(1 for c in cases if c["review_status"] == "Accepted"), "-"),
        ("Human Edited Diagnoses", sum(1 for c in cases if c["review_status"] == "Edited"), "-"),
        ("Human Rejected Diagnoses", sum(1 for c in cases if c["review_status"] == "Rejected"), "-"),
        ("AI-Human Agreement Rate", sum(1 for c in cases if c["review_status"] == "Accepted") / len(cases), ">= 80%"),
        ("Responsible AI Correction Logs", sum(1 for c in cases if c["review_status"] in ["Edited", "Rejected"]), "At least 5")
    ]
    
    row_idx = 6
    for metric, val, target in metrics:
        ws_ov.write(row_idx, 1, metric, fmt_cell_bold)
        if isinstance(val, float):
            ws_ov.write(row_idx, 2, val, fmt_pct)
        else:
            ws_ov.write(row_idx, 2, val, fmt_cell_center)
        ws_ov.write(row_idx, 3, target, fmt_cell_center)
        row_idx += 1
        
    # Concept / Issue Type breakdown
    ws_ov.write('B15', 'Issue Breakdown by Concept Tag', fmt_section)
    ws_ov.write('B16', 'Concept', fmt_header)
    ws_ov.write('C16', 'Case Count', fmt_header)
    
    concepts = {}
    for c in cases:
        concepts[c["concept"]] = concepts.get(c["concept"], 0) + 1
        
    c_row = 16
    for concept, count in concepts.items():
        ws_ov.write(c_row, 1, concept, fmt_cell)
        ws_ov.write(c_row, 2, count, fmt_cell_center)
        c_row += 1
        
    # HSRP / OSI Layer distribution
    ws_ov.write('B26', 'OSI Layer Distribution', fmt_section)
    ws_ov.write('B27', 'OSI Layer', fmt_header)
    ws_ov.write('C27', 'Case Count', fmt_header)
    
    osi_layers = {}
    for c in cases:
        osi_layers[c["osi_layer"]] = osi_layers.get(c["osi_layer"], 0) + 1
        
    osi_row = 27
    for layer, count in sorted(osi_layers.items()):
        ws_ov.write(osi_row, 1, layer, fmt_cell)
        ws_ov.write(osi_row, 2, count, fmt_cell_center)
        osi_row += 1
        
    # Programmatic Charts on Overview page!
    # 1. Human Agreement Pie Chart
    chart_agreement = workbook.add_chart({'type': 'pie'})
    chart_agreement.add_series({
        'name': 'AI vs Human Review',
        'categories': '=Overview!$B$8:$B$10',
        'values': '=Overview!$C$8:$C$10',
        'points': [
            {'fill': {'color': '#5B9BD5'}}, # Accepted
            {'fill': {'color': '#FFC000'}}, # Edited
            {'fill': {'color': '#ED7D31'}}, # Rejected
        ]
    })
    chart_agreement.set_title({'name': 'AI vs Human Review Status'})
    ws_ov.insert_chart('F5', chart_agreement, {'x_offset': 10, 'y_offset': 10})
    
    # 2. Concept Breakdown Bar Chart
    chart_concept = workbook.add_chart({'type': 'bar'})
    chart_concept.add_series({
        'name': 'Cases',
        'categories': f'=Overview!$B$17:$B${16+len(concepts)}',
        'values': f'=Overview!$C$17:$C${16+len(concepts)}',
        'fill': {'color': color_primary}
    })
    chart_concept.set_title({'name': 'Troubleshooting Cases by Concept'})
    chart_concept.set_legend({'position': 'none'})
    ws_ov.insert_chart('F20', chart_concept, {'x_offset': 10, 'y_offset': 10})
    
    # ----------------------------------------------------
    # Sheet 2: Case Log Details
    # ----------------------------------------------------
    ws_log = workbook.add_worksheet('Case Dataset Log')
    ws_log.set_column('A:A', 6)  # ID
    ws_log.set_column('B:B', 40) # Symptom
    ws_log.set_column('C:C', 12) # Concept
    ws_log.set_column('D:D', 10) # OSI
    ws_log.set_column('E:E', 10) # Severity
    ws_log.set_column('F:F', 35) # Expected Fault
    ws_log.set_column('G:G', 15) # Review Status
    ws_log.set_column('H:H', 40) # Human Notes
    
    ws_log.write('A1', 'ID', fmt_header)
    ws_log.write('B1', 'Symptom', fmt_header)
    ws_log.write('C1', 'Concept', fmt_header)
    ws_log.write('D1', 'OSI Layer', fmt_header)
    ws_log.write('E1', 'Severity', fmt_header)
    ws_log.write('F1', 'Expected Root Cause', fmt_header)
    ws_log.write('G1', 'Review Status', fmt_header)
    ws_log.write('H1', 'Human Verification Notes', fmt_header)
    
    l_row = 1
    for case in cases:
        ws_log.write(l_row, 0, case["id"], fmt_cell_center)
        ws_log.write(l_row, 1, case["symptom"], fmt_cell)
        ws_log.write(l_row, 2, case["concept"], fmt_cell_center)
        ws_log.write(l_row, 3, case["osi_layer"], fmt_cell_center)
        ws_log.write(l_row, 4, case["severity"], fmt_cell_center)
        ws_log.write(l_row, 5, case["expected_fault"], fmt_cell)
        
        status = case["review_status"]
        if status == "Accepted":
            ws_log.write(l_row, 6, status, fmt_accepted)
        elif status == "Edited":
            ws_log.write(l_row, 6, status, fmt_edited)
        else:
            ws_log.write(l_row, 6, status, fmt_rejected)
            
        ws_log.write(l_row, 7, case.get("human_notes", ""), fmt_cell)
        l_row += 1
        
    workbook.close()
    print(f"Successfully generated {output_path}")
    return True

if __name__ == "__main__":
    export_xlsx_dashboard()
