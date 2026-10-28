Run `uv run specreview eval dev`.

Then read runs/latest/scorecard.json and the previous scorecard if one exists. Report:

1. Section filter recall
2. Requirement recall and precision
3. Mandatory requirement recall
4. Deadline and required form recall
5. Citation accuracy
6. Silent coverage drops
7. Status accuracy (Lakeview)
8. Tokens, latency, and cost per package

Show what changed since the last run. List the five worst misses with document, page, and paragraph path, and the stage that most likely caused each one.

Propose fixes, one change at a time. Never edit anything under data/golden/test/, and never run the test set unless I ask.
