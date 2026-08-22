from app.extraction.validator import validate_extraction_output, filter_and_score_facts

# Use the exact chunk content from the test
chunk_text = """(in  million, unless otherwise stated)
As at As at As at As at As at
Particulars December March March 31,
December 31, 2020 March 31, 2021
31, 2021 31, 2020 2019
Total equity 59,798.47 29,148.37 28,367.97 31,704.06 33,882.83
Liabilities
Non-current liabilities
Financial Liabilities
i) Borrowings 1,005.28 1,329.84 1,316.09 998.02 356.20
ii) Lease liabilities 6,912.95 6,563.72 6,538.44 3,870.65 2,425.22
iii) Trade payables
a. total outstanding dues
of micro enterprises and
small enterprises - - -
b. total outstanding dues
of creditors other than micro
enterprises and small
enterprises - - - 1.10 24.75
Provisions 406.55 214.58 219.16 166.12 108.90
Deferred tax liabilities (net) 734.97 - - - -
Total non- current
liabilities 9,059.75 8,108.14 8,073.69 5,035.89 2,915.07
Current liabilities"""

raw = '{"facts": [{"entity": "Delhivery Limited", "attribute": "Total Equity", "value": "59798.47", "unit": "INR million", "time_period": "December 31, 2020", "scope": "Consolidated", "qualifier": "Balance Sheet: Total equity 59,798.47 29,148.37 28,367.97 31,704.06 33,882.83", "fact_type": "numeric", "confidence": 0.85, "evidence_span": {"start": 244, "end": 306}}]}'

result, errors = validate_extraction_output(raw)
print('Validation result:', result)
print('Errors:', errors)

if result:
    valid = filter_and_score_facts(result.facts, chunk_text, min_confidence=0.5)
    print('Filtered facts:', len(valid))
    for f in valid:
        print(' ', f.entity, '|', f.attribute, '=', f.value, f.unit)
    # Debug the evidence span
    for f in result.facts:
        start = f.evidence_span["start"]
        end = f.evidence_span["end"]
        print(f'Chunk length: {len(chunk_text)}')
        print(f'Evidence span: [{start}:{end}]')
        print(f'Evidence text: {chunk_text[start:end]!r}')
        # Check if numeric value found
        import re
        evidence_text = chunk_text[start:end]
        fact_num = 59798.47
        evidence_nums = re.findall(r"[\d,]+\.?\d*", evidence_text)
        print(f'Evidence nums: {evidence_nums}')
        for num_str in evidence_nums:
            try:
                if abs(float(num_str.replace(",", "")) - fact_num) < 0.01:
                    print(f'  Found match: {num_str}')
            except ValueError:
                pass