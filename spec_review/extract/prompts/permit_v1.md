You extract numeric effluent limits from part of a discharge permit.

Text:
{text}

Rules:
1. Use only the text above. Never compute, convert, or infer a limit.
2. Create one record per parameter, limit type (monthly_avg, weekly_avg, daily_max, annual_load), and season.
3. Copy source_text exactly from the text, character for character: the line that states the limit.
4. value is the limit as written. If the permit says "Report" or gives no number, put the row in skipped with a reason.
5. unit is the unit as written, such as mg/L or lb/day.

Return JSON that matches the schema.
