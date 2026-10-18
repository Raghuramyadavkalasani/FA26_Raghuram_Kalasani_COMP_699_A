# Step 2 - Week 1

Review draft: confirm the proposed research question against your approved plan.

1. Read docs/step_2/week_1/research_foundation.pdf.
2. Open Terminal in this folder. Use Python 3.12 for the recorded environment.
3. Run:

```sh
python3 src/research/prepare_inputs.py --count 200 --equipment 10 --seed 699 --output docs/step_2/week_1/evidence
python3 -m unittest discover -s src/research -p 'test_*.py' -v
```

No additional packages are needed. If python3 selects a different version, use your Python 3.12 interpreter path. The script is also compatible with Python 3.9 for input preparation; it does not run Django. Outputs are replaced on rerun; use --output with another directory to retain the supplied assistant-run evidence.

Expected recorded summary: 200 requests, 10 items, 1,962 same-item pairs, 414 overlapping input pairs. These are not double bookings or comparative experiment results. Six tests should pass.

Upload the docs and src folders from this package at your GitHub repository root, preserving paths. They add docs/step_2/week_1 and src/research; do not replace or delete previous project folders. This package contains no local application database or account data.

Suggested commit message: Add Week 1 synthetic reservation inputs and research foundation

The code, report and recorded run were prepared with AI assistance. The student repeated execution successfully; see docs/step_2/week_1/student_run/. Review the report and understand the code before submitting. Only Week 1 is prepared. Week 2 and Week 3 experiments remain planned; the final combined Canvas PDF is not yet due to be assembled from unperformed work.
