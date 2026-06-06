# DECISIONS.md — decision & learnings log

A short running note of the real choices you made: what you tried, what failed and why, what
you changed. This is your engineering judgement on the record — it is what separates a builder
from a button-presser, and it is graded (challenge brief section 08).

Append a 1–2 line entry whenever you make a real decision or hit/fix a wall. Add a timestamp.

Format:
`[HH:MM] <decision or problem> → <what you did and why>`

---

## Example (replace with your own)
- `[10:20]` Chose plain-csv parsing over pandas → fewer deps, fast enough for 5k rows, model
  quota saved for the fixer.
- `[11:05]` Title detector over-counted duplicates → realized non-indexable pages were
  included; added an indexable+200 filter (per rulebook).
- `[12:40]` Dashboard wasn't updating live → MCP tool wasn't emitting the SSE event; added
  `_emit("issue", row)` in extract.

---

## My log
- `[12:50]` <Conflict between .claude/settings.json >Decided to not ignore this as it may affect the audit.jsonl file.

- `[1:30]` <Figured out qwen3.5-9b taking a lot of time for solving issues> Decided to give a very detailed on point explaining everything hence reducing it's thinking time.

- `[2:00]` <Add fixing logic in server.py or new file> Decided to make a new file named fix_writer.py for better debugging and code modularity.

- `[2:30]` <The redirect_chain detector flagged the wrong URLs.> 

- `[]` 
