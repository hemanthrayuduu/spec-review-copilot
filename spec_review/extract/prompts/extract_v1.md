You extract requirements from one part of a construction specification for water or wastewater equipment.

Context:
Section {section_number} {section_title}, {part}, paragraph {paragraph_path}, page {page}.

Text:
{text}

Candidate sentences flagged by rules:
{candidates}

Rules:
1. Use only the text above. Never add outside knowledge or assume values.
2. Create one record per requirement. Split sentences that contain several requirements.
3. Copy source_text exactly from the text, character for character.
4. Values and units must appear in source_text. Do not convert units.
5. mandatory is true for "shall", "must", and "is required". It is false for "should", "may", and "recommended".
6. Record any named manufacturer, and whether "or equal" is allowed.
7. List any referenced sections in linked_sections.
8. For every candidate, return a disposition: requirement (with record ids) or not_requirement (with a short reason).
9. If unsure, set confidence below 0.6 instead of guessing.

Return JSON that matches the schema.
