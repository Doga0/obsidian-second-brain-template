---
name: sb-experiment
description: "Second Brain — Add an experiment to a research/project hub's Experiment Log or record a result, and compare it against hypotheses and decisions. Use when the user runs /sb-experiment or shares an experiment result."
---
# /sb-experiment

1. Find the hub and read its "Experiment log" table. If there's none, add the table from the `Research Hub` template.
2. **New experiment:** add a row: date · experiment · hypothesis/RQ · the one thing that changes · result (empty). Ask if the hypothesis is unclear. If several variables change at once, warn: change one variable at a time, or you won't know what caused the effect.
3. **Result:** find the row and fill in the result with the numbers the user gave. Never invent numbers. If the raw result is a file (log, csv), suggest moving it into the hub folder and link it from the row. When extracting metrics from a log, say which lines they came from.
4. **Interpretation:** does the result support or refute a hypothesis, open question or decision? Write it under the table as `> [!tip] AI interpretation`. If it contradicts a decision, suggest `/sb-decide`.
5. Run `vault_tool.py log experiment "<hub>: <experiment>"`.
