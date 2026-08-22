import requests
import time

time.sleep(2)

# Test stats endpoint
try:
    r = requests.get('http://localhost:8000/api/stats')
    print('Stats:', r.json())
except Exception as e:
    print('Error:', e)

# Test documents list
try:
    r = requests.get('http://localhost:8000/api/documents')
    docs = r.json()
    print('Documents:', len(docs))
    for d in docs[:3]:
        print(' ', d['filename'], '-', d['status'])
except Exception as e:
    print('Error:', e)

# Test facts for first document
try:
    r = requests.get('http://localhost:8000/api/documents')
    docs = r.json()
    if docs:
        doc_id = docs[0]['document_id']
        r = requests.get(f'http://localhost:8000/api/documents/{doc_id}/facts')
        facts = r.json()
        print('Facts for', docs[0]['filename'], ':', len(facts))
        for f in facts[:5]:
            print(' ', f['entity'], '|', f['attribute'], '=', f['value'], f['unit'])
except Exception as e:
    print('Error:', e)

# Test relationships
try:
    r = requests.get('http://localhost:8000/api/relationships?relationship_type=corroborates')
    rels = r.json()
    print('Corroborations:', len(rels))
    for rel in rels[:3]:
        print(' ', rel['relationship_type'], ':', rel['explanation'][:80], '...')
except Exception as e:
    print('Error:', e)

# Test contradictions
try:
    r = requests.get('http://localhost:8000/api/relationships?relationship_type=contradicts')
    rels = r.json()
    print('Contradictions:', len(rels))
    for rel in rels[:3]:
        print(' ', rel['relationship_type'], ':', rel['explanation'][:80], '...')
except Exception as e:
    print('Error:', e)

# Test reconciliations
try:
    r = requests.get('http://localhost:8000/api/relationships?relationship_type=reconciles')
    rels = r.json()
    print('Reconciliations:', len(rels))
    for rel in rels[:3]:
        print(' ', rel['relationship_type'], ':', rel['explanation'][:80], '...')
except Exception as e:
    print('Error:', e)