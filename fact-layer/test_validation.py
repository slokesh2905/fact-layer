from app.extraction.validator import validate_extraction_output, filter_and_score_facts

raw = '{"facts": [{"entity": "Delhivery Limited", "attribute": "Total Equity", "value": "59798.47", "unit": "INR million", "time_period": "December 31, 2020", "scope": "Consolidated", "qualifier": "Balance Sheet: Total equity 59,798.47 29,148.37 28,367.97 31,704.06 33,882.83", "fact_type": "numeric", "confidence": 0.85, "evidence_span": {"start": 244, "end": 306}}]}'

chunk_text = """(in  million, unless otherwise stated)
As at As at As at As at As at
Particulars December March March 31,
December 31, 2020 March 31, 2021
31, 2021 31, 2020 2019
Total equity 59,798.47 29,148.37 28,367.97 31,704.06 33,882.83
Liabilities
Non-current liabilities"""

result, errors = validate_extraction_output(raw)
print('Validation result:', result)
print('Errors:', errors)

if result:
    valid = filter_and_score_facts(result.facts, chunk_text, min_confidence=0.5)
    print('Filtered facts:', len(valid))
    for f in valid:
        print(' ', f.entity, '|', f.attribute, '=', f.value, f.unit)