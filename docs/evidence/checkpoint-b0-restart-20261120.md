# B0 checkpoint loss and replay evidence — 20 November 2026

## Run identities

- Initial run: `TREATMENT=B0`, `FAULT=F0`, `RUN_ID=b0-checkpoint-20261120`; exit code 0.
- Restart: same treatment and run ID, attempt 2, without reset between attempts; exit code 1 from the final F0 audit.
- Effective B0 checkpoint from the initial run: `/checkpoints/ephemeral/b0-checkpoint-20261120/B0`.

## Observed behavior

- Initial F0 completed with 300 MinIO objects, 300 metadata rows, 300 distinct recording IDs, 300 object HEAD checks, and 30 micro-batches.
- On attempt 2, the new driver replayed all 30 batches and performed 300 Iceberg metadata appends again.
- The audit then reported `F0 metadata row count: expected 300, found 600`. This nonzero exit is the expected at-least-once outcome for B0 after its ephemeral checkpoint was lost; it is evidence of replay and duplicate metadata, not a successful clean reconciliation.
- MinIO afterward reported 300 objects in `audiomoth` and 2,401 objects in `warehouse`. The warehouse count is an object-store file count, not a metadata row count. The Iceberg row count is the 600 reported by the audit.
- `/data/state/checkpoints/b0-checkpoint-20261120/B0` was absent on the VM. The effective checkpoint path was under the driver's `/checkpoints/ephemeral` tmpfs; the run container was removed after the attempt. Together with the lab's T5 tmpfs verification, this is consistent with ephemeral checkpoint loss.

## Evidence files

- `b0-f0-checkpoint-20261120.log` — initial B0/F0 run.
- `b0-restart-checkpoint-20261120.log` — same-run-ID restart and replay.
- `checkpoint-b0-restart-summary-20261120.txt` — 30 replayed batches, 300 metadata appends, audit result, object-store counts, and persistent-root check.
- `reset-before-b0-checkpoint-20261120-retry.log` — reset that immediately preceded the successful initial run.
- `check-before-b0-restart-20261120.log` — environment lock check.

The B0 initial run and restart are now observed. The restart's audit failure is part of the result: B0 has no durable progress checkpoint and no idempotence guard. The B1 counterpart is documented in `b1-f0-20261120.md`, where the persistent checkpoint survived restart and the 300-row reconciliation remained clean.
