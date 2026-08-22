import subprocess
import time
import requests
import sys

# Start the API server
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'], cwd='D:/Personal Projects/Superjoin/fact-layer')

try:
    # Wait for server to start
    time.sleep(3)
    
    # Test stats endpoint
    try:
        r = requests.get('http://localhost:8000/api/stats', timeout=5)
        print('Stats:', r.json())
    except Exception as e:
        print('Stats Error:', e)

    # Test documents list
    try:
        r = requests.get('http://localhost:8000/api/documents', timeout=5)
        docs = r.json()
        print('Documents:', len(docs))
        for d in docs[:3]:
            print(' ', d['filename'], '-', d['status'])
    except Exception as e:
        print('Documents Error:', e)

    # Test facts for first document
    try:
        r = requests.get('http://localhost:8000/api/documents', timeout=5)
        docs = r.json()
        if docs:
            doc_id = docs[0]['document_id']
            r = requests.get(f'http://localhost:8000/api/documents/{doc_id}/facts', timeout=5)
            facts = r.json()
            print('Facts for', docs[0]['filename'], ':', len(facts))
            for f in facts[:5]:
                print(' ', f['entity'], '|', f['attribute'], '=', f['value'], f['unit'])
    except Exception as e:
        print('Facts Error:', e)

    # Test relationships
    for rel_type in ['corroborates', 'contradicts', 'reconciles']:
        try:
            r = requests.get(f'http://localhost:8000/api/relationships?relationship_type={rel_type}', timeout=5)
            rels = r.json()
            print(f'{rel_type.capitalize()}: {len(rels)}')
            for rel in rels[:3]:
                print(' ', rel['relationship_type'], ':', rel['explanation'][:80], '...')
        except Exception as e:
            print(f'{rel_type} Error:', e)

finally:
    proc.terminate()