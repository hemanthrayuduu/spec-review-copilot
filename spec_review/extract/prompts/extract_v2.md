You extract requirements from one part of a construction specification for water or wastewater equipment.

Context:
Section {section_number} {section_title}, {part}, paragraph {paragraph_path}, page {page}.

Text:
{text}

Candidate sentences flagged by rules:
{candidates}

Rules:
1. Use only the text above. Never add outside knowledge or assume values.
2. Create one record per requirement. Split sentences that contain several requirements: each "shall", "must", or "should" clause that sets its own obligation is its own record. A single clause that lists several properties of one item stays one record.
3. Copy source_text exactly from the text, character for character. For a split record, copy only the words of that clause.
4. Values and units must appear in source_text. Do not convert units.
5. mandatory is true for "shall", "must", and "is required". It is false for "should", "may", and "recommended". A statement with "should" or "may" is still a requirement, a preferred one: give it a requirement disposition with mandatory false.
6. Record any named manufacturer, and whether "or equal" is allowed.
7. List any referenced sections in linked_sections.
8. For every candidate, return a disposition: requirement (with record ids) or not_requirement (with a short reason).
9. If unsure, set confidence below 0.6 instead of guessing.
10. value is one number or one range, copied as written, such as "50", "0.5", "1,500", or "2 to 4". Never put words or several numbers in value. When a requirement states several quantities, value is the main quantity it sets, usually the first one; the others stay in source_text.
11. unit is the word or symbol written right after that number, as written, such as "psi", "mg/L", "days", "percent", or "hours". When the number counts things, the unit is the thing counted, such as "spare filters". Do not add context to the unit: write "days", not "days before startup". Leave unit empty only when the text gives none.
12. operator is "<=" for "not more than", "not to exceed", "within", or "maximum"; ">=" for "not less than", "at least", or "minimum"; "range" for "between ... and ..." or "... to ..."; and "=" for a plain value.

Return JSON that matches the schema.
