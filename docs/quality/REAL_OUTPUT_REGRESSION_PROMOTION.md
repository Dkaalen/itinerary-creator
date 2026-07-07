# Real Output Regression Promotion

Use this when a random real-Excel QA run exposes a real client-facing output bug.

Workflow:

1. Keep the seed and fixture id from the failing report.
2. Describe the expected product behavior.
3. Promote the case into `tests/fixtures/real_output_regressions/`.
4. Add or adjust a focused regression test when a root-cause fix is made.

Example:

```bash
python scripts/promote_real_output_regression.py \
  --seed 7007 \
  --fixture "Standard-Itinerary-Iceland.xlsx::8D RW" \
  --issue-code typoed_activity_type_seen \
  --name activity-upgrade-typo-classification \
  --expected-behavior "Typoed Activity Upgrade rows must remain optional add-ons and must not become route destinations."
```

The JSON record captures:

* seed
* fixture id
* score issues
* trip title/subtitle/route
* short day excerpts
* expected behavior

Do not promote every warning. Promote cases that prove a bug class.
