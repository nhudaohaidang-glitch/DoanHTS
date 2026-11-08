# AI v1 diagnosis and separate v2 development workflow

2026-10-29. No measured v2 network accuracy is claimed.

## Evidence from the user's diagnostic archive

Using repository code, reproduced all 182 stored predictions, scores and quantized inputs. AI: 130/182 correct, macro-F1 0.7105091795, normal false-positive rate 26/78. Frozen baseline: 156/182 correct. Independently SHA-checked and re-extracted the two supplied PCAPs (normal_retry, scan_slow); all 52 corresponding CSV rows match. Other five PCAPs were not uploaded. Seven supplied capture logs report zero kernel drops.

The diagnostic conclusion and exact raw-feature statistics are in `ai_part2/handoff/DIAGNOSTIC_V1_CHALLENGE01.md`. No private PCAP or uploaded archive is committed. SYN cookies and residual SYN_RECV state were observed; service interruption or FPGA protection is not established.

## Changes

- Preserve v1 model, RTL and reference artifacts. Separate v2 train/validation collector, fixed input divisors [8,2,1,1,1,1], same six raw features and 6-8-3 architecture.
- Fit three candidates on train; select by integer validation macro-F1/FPR. Threshold baseline also selects only on validation. Export a model/metrics hash record before holdout collection.
- Keep development and holdout captures in separate directories/manifests. Holdout evaluator checks the pre-collection selection record, capture IDs/times and exact PCAP reuse against development.
- Reset only the owned isolated lab between sessions to avoid inherited TCP state. Stop on kernel capture drops. Source pacing no longer sends catch-up bursts after VM pauses.
- Add v2 Gowin filenames and matching C quantization symbols, keeping v1 generation defaults compatible.
- Provide a checksum-verified update ZIP using the existing backup/rollback installer, plus Vietnamese commands.

## Verification performed in the cloud

- 41 unittest cases passed, including actual loopback Mosquitto publish/receive, two legitimate clients and large payloads, offline assessment, UI API, updater preservation/rollback, v2 protocol and export validation. V2 dataset fixtures are artificial and are not an accuracy benchmark.
- Artificial v2 fixture: train/export then Icarus simulation of both memory-file core and self-contained generated core: 288 vectors each, 84 cycles minimum/maximum. This checks arithmetic/RTL agreement only.
- Reviewed real v1 self-contained core: 360 vectors, 84 cycles, still passes.
- Evaluator CLI emitted JSON, predictions, per-capture CSV and HTML from artificial post-freeze fixtures. Tampered model, pre-freeze records and development capture reuse are rejected in tests.
- Bash syntax, Python compilation and git diff whitespace checks passed.
- Update payload: 75 files. Installing on the previous committed kit changed 16 files; existing v1 model/metrics, challenge CSV/PCAP and environment sentinel were byte-preserved. Reapplying reports already_current. Installed payload passed the same 41 tests.

No Linux network namespaces can be created in this cloud workspace. Collector orchestration was tested with mocked network commands; actual v2 session collection, source pacing under VM load, AppArmor access and holdout accuracy must run on the user's Ubuntu. Gowin synthesis, routed timing and live packet blocking have not been tested for v2. Existing v1 synthesis screenshots do not establish v2 hardware performance.
