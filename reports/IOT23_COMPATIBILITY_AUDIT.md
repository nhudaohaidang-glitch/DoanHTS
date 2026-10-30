# IoT-23 compatibility audit before training

2026-10-30. No IoT-23 model has been trained in this audit. The reviewed lab v2 remains unchanged.

Primary reference read: https://www.stratosphereips.org/datasets-iot23 . The publisher describes PartOfAHorizontalPortScan as multiple destination IPs sharing a port; DDoS identifies attack flows toward a destination and is not a TCP SYN-specific label. The smaller archive contains labeled flows without PCAP. Individual scenario files are available.

Inspected five labeled logs already present from the earlier dataset preparation in /workspace/doanhts-ai/data/iot23-starter, and rechecked their SHA256 against that download manifest. These logs were not inputs to the lab v2 trainer. Their source URLs and exact counts are recorded in IOT23_SUBSET_AUDIT.json. The manifest hashes are local provenance checks, not publisher-provided checksums.

| Capture | Rows | Label inventory |
|---|---:|---|
| Malware34-1 | 23145 | Benign1923, C&C6706, HorizontalScan122, DDoS14394 |
| Malware44-1 | 237 | Benign211, C&C-FileDownload11, C&C14, DDoS1 |
| Malware3-1 | 156103 | Benign4536, C&C8, HorizontalScan145597, Attack5962 |
| Honeypot4-1 | 452 | benign452 |
| Honeypot5-1 | 1374 | benign1374 |

Total181311 connection records, not181311 packets or one-second windows. DDoS in this subset:14393 TCP flows and2 UDP flows. TCP alone does not establish SYN flood; flow history is not an exact per-packet/window SYN count. HorizontalScan:145718 TCP flows and1 UDP flow. The presence of generic Attack/C&C labels is not permission to relabel them SYN/scan. These five files do not establish whole-dataset vertical-scan coverage or independent three-way train/validation/test coverage for the chosen classes.

Parser details to handle before any import: detailed label field aliases include det_label; two benign logs use lowercase benign. Preserve original values/provenance while recognizing explicitly equivalent case/header spellings. The earlier scratch prepare_iot23.py did not handle all these forms and must not be used unchanged as a training importer.

Current hardware contract: six ingress IPv4 packet-derived features in exact one-second windows, three outputs Normal/SYN/VerticalScan. Zeek connection duration/orig_pkts/history cannot simply be renamed to these features; a connection may span windows and full-flow statistics may require future packets. Reconstructing current FPGA inputs needs matching packet data, direction/protected-target definitions, flow-label association and a documented rule for mixed-label windows. Do not assign all packets of a long flow to its start second or spread counts uniformly without evidence.

Decision required before dependent training: keep the group's SYN/vertical scope and inspect matching PCAP behavior, or formally change the dataset/model/hardware/demo class contract. A native-label Normal/DDoS/HorizontalScan model could be studied separately but must not be presented as the existing SYN/vertical model. No such class change is assumed here.

Next work independent of that decision: stream/audit selected official logs and their provenance; avoid a blind full download. After class/input contract is resolved, choose sufficient independent captures, split by capture rather than random adjacent windows, build train-only preprocessing, fit/quantize a new model in a separate directory, compare a baseline and test on held-out captures, then regenerate matching RTL/firmware and rerun simulation/synthesis. Reuse the MLP core only if input/output dimensions and arithmetic remain compatible. Do not promise95% or reuse the lab100% as an IoT-23 score.
