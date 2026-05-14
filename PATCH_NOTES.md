# Patch Notes

Fixed scripts for the recovery demo:

- `00_05_e/main.py`: always creates a fresh known-good baseline before unsafe output; adds run and operation IDs.
- `00_05_e/state_utils.py`: uses unique microsecond + UUID snapshot/quarantine filenames; selects latest snapshot by mtime.
- `00_05_e/scanner.py`: detects sensitive content and attributes the writer from logs.
- `00_05_e/rollback.py`: includes scanner findings and attribution in the recovery action log.
- `00_05_e/validate.py`: validates restored output against `AgentOutput` schema and checks safety/audit evidence.
- `00_05_e/agent_models.py`: adds typed scan report and attribution contracts.
- `00_05_e/observability.py`: adds `run_id` and `operation_id` helpers.
- `00_05_e/guardrails.py`: adds high-signal detectors for email, card last four, secret-like tokens, and sensitive keywords.
- `00_05_e/inventory/agent_inventory.json`: updates controls and write paths.

Regression tested:

```bash
python -m py_compile 00_05_e/*.py
python 00_05_e/main.py --mode unsafe
python 00_05_e/main.py --mode unsafe
python 00_05_e/scanner.py --output 00_05_e/out/shopping_summary.json --log 00_05_e/logs/agent_events.jsonl
python 00_05_e/assess.py --snapshots 00_05_e/snapshot --current 00_05_e/out/shopping_summary.json
python 00_05_e/rollback.py --output 00_05_e/out/shopping_summary.json --snapshots 00_05_e/snapshot --quarantine 00_05_e/quarantine --actionlog 00_05_e/action_log.jsonl
python 00_05_e/validate.py --output 00_05_e/out/shopping_summary.json --snapshot 00_05_e/snapshot --action-log 00_05_e/action_log.jsonl --quarantine 00_05_e/quarantine
```
