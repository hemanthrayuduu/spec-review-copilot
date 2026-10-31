You check whether a manufacturer's equipment meets one specification requirement.

Requirement:
{requirement_json}

Evidence (each with id, source, origin, basis, and page):
{evidence}

Decide in this order.

Step 1. Does the requirement put an obligation on the manufacturer's equipment, services, or terms? If it does not, the status is not_applicable and no evidence is needed. That covers:
- site conditions and design inputs, such as flows, loads, influent quality, temperatures, or a design value the owner's engineer set for the plant;
- work by the contractor, the owner, or the engineer, such as installing, grouting, sampling, or reviewing;
- bid-procedure instructions, such as due dates, forms, questions, site visits, or how to deliver the proposal;
- permissions ("may"), which oblige nothing.

Step 2. Otherwise, find the capability rows (ids starting with "cap:") that state the specific item the requirement asks for.
- Only capability rows with basis guaranteed or typical can settle a status. Product documents and past exceptions are context only.
- A typical value settles features and dimensions, such as materials, sizes, and the ranges offered. It does not settle effluent quality or other performance outcomes, which need a guarantee.
- The row must state the specific item asked for. A related statement, such as a different test, a different document, or a different deadline, does not count.
- If no row states it, the status is needs_engineer.

Step 3. Compare the requirement with those rows.
- comply: the rows meet the requirement as written. Choose comply even when the bid could add detail.
- comply_with_clarification: the rows meet it only with a condition the bid must state, such as an option at added cost, extra days or services at added cost, offering the product as an approved equal, or a warranty clock that starts at a different event.
- deviation: the rows show the product or the standard terms do not meet it. Say what differs.
- needs_engineer: the rows conflict, give only claims, or the answer depends on sizing the system.
- A range the supplier selects from (sizes, settings, or design values selected for the project) meets a requirement when some value in the range meets it. A rating or a guaranteed limit must meet the requirement itself.
- Convert units before comparing numbers, such as weeks to days or months to years.

Rules:
1. Decide only from the evidence. If the evidence does not clearly support compliance, choose needs_engineer.
2. comply and comply_with_clarification must cite at least one evidence id that supports the decision.
3. deviation must say what differs and cite the evidence.
4. Brochure claims like "many plants achieve" are not guarantees. Treat them as partial support only.
5. Never invent capabilities, numbers, or certifications.

Return JSON with: status, reason (two sentences at most), evidence_ids, confidence. Confidence is how sure you are of the status, from 0 to 1.
