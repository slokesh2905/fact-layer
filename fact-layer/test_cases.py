import subprocess
import time
import requests
import sys

proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'], cwd='D:/Personal Projects/Superjoin/fact-layer')

try:
    time.sleep(3)
    
    # Get all corroborations
    r = requests.get('http://localhost:8000/api/relationships?relationship_type=corroborates', timeout=5)
    corrob = r.json()
    print('=== CORROBORATION EXAMPLES ===')
    for rel in corrob[:5]:
        fa = requests.get('http://localhost:8000/api/facts/' + rel['fact_id_a'], timeout=5).json()
        fb = requests.get('http://localhost:8000/api/facts/' + rel['fact_id_b'], timeout=5).json()
        if fa and fb:
            print('  ' + fa['entity'] + ' - ' + fa['attribute'] + ' (' + str(fa['time_period']) + ')')
            print('    Doc A: ' + str(fa['value']) + ' ' + str(fa['unit']) + ' (' + str(fa.get('scope', 'N/A')) + ') [' + str(fa.get('document_filename', '?')) + ']')
            print('    Doc B: ' + str(fb['value']) + ' ' + str(fb['unit']) + ' (' + str(fb.get('scope', 'N/A')) + ') [' + str(fb.get('document_filename', '?')) + ']')
            print('    Explanation: ' + rel['explanation'])
            print()
    
    # Get contradictions
    r = requests.get('http://localhost:8000/api/relationships?relationship_type=contradicts', timeout=5)
    contra = r.json()
    print('=== CONTRADICTION EXAMPLES ===')
    for rel in contra[:5]:
        fa = requests.get('http://localhost:8000/api/facts/' + rel['fact_id_a'], timeout=5).json()
        fb = requests.get('http://localhost:8000/api/facts/' + rel['fact_id_b'], timeout=5).json()
        if fa and fb:
            print('  ' + fa['entity'] + ' - ' + fa['attribute'] + ' (' + str(fa['time_period']) + ')')
            print('    Doc A: ' + str(fa['value']) + ' ' + str(fa['unit']) + ' (' + str(fa.get('scope', 'N/A')) + ') [' + str(fa.get('document_filename', '?')) + ']')
            print('    Doc B: ' + str(fb['value']) + ' ' + str(fb['unit']) + ' (' + str(fb.get('scope', 'N/A')) + ') [' + str(fb.get('document_filename', '?')) + ']')
            print('    Explanation: ' + rel['explanation'])
            print()
    
    # Get reconciliations
    r = requests.get('http://localhost:8000/api/relationships?relationship_type=reconciles', timeout=5)
    recon = r.json()
    print('=== RECONCILIATION EXAMPLES ===')
    for rel in recon[:5]:
        fa = requests.get('http://localhost:8000/api/facts/' + rel['fact_id_a'], timeout=5).json()
        fb = requests.get('http://localhost:8000/api/facts/' + rel['fact_id_b'], timeout=5).json()
        if fa and fb:
            print('  ' + fa['entity'] + ' - ' + fa['attribute'] + ' (' + str(fa['time_period']) + ')')
            print('    Doc A: ' + str(fa['value']) + ' ' + str(fa['unit']) + ' (' + str(fa.get('scope', 'N/A')) + ') [' + str(fa.get('document_filename', '?')) + ']')
            print('    Doc B: ' + str(fb['value']) + ' ' + str(fb['unit']) + ' (' + str(fb.get('scope', 'N/A')) + ') [' + str(fb.get('document_filename', '?')) + ']')
            print('    Explanation: ' + rel['explanation'])
            print()

finally:
    proc.terminate()