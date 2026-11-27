# Example output

Everything in this folder is **synthetic**. "Example Studio", its games ("Starfall Drift", "Tiny Harbor"), labels, counts, dates, fingerprints and the "Why this is special" paragraphs are invented to show the output format. They describe no real company or dataset.

`dream.txt` is the synthetic draft that `scripts/add_dream.py` validated and inserted as the "Why this is special" section at the end of `report.md`.

`status.json` holds the synthetic owner answers recorded with `measure_data.py status` (connectors and studio categories), and `dream.json` the saved pitch, so `measure_data.py report --out examples` re-renders `measure.json` and `report.md` exactly. The ticket keys behind the hashed resolved-key sets in `sources/jira--starfall-jira.json` are invented (`SFD-1` to `SFD-14820`).
