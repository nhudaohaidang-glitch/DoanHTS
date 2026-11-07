# IoT-23 audit with SYN flood and vertical scan retained

2026-10-30. User explicitly retained Normal/SYN flood/vertical scan. No class was renamed. No IoT-23 model was trained, no frozen v2 weight was changed, and no packet was replayed on a network. All analysis is offline.

## Data inspected

Read directory indexes for the 20 malware captures listed by the publisher and the three benign scenario names. Inspected labelled logs from nine scenarios: malware3,8,20,21,34,44,42 and benign4,5. Downloaded complete original PCAPs3 and34, the publisher's filtered TCP-port80 subset from35, and benign4's PCAP.xz. These are a selected subset, not proof of whole-dataset absence of a behavior.

Downloads: malware34 PCAP126317980 bytes, SHA25692ec7e2f6658ee4b007d0b816986c46cc0338bc5e2bec6ceaaca566c695e4699; malware3 PCAP57919772 bytes, SHA256c674dc0c8d584fa66e6f00c60df973c5fbacad551c850a76d75ec9952641d00b; filtered35 subset1225095 bytes, SHA256adaccebdabad15e964507a88eced38cdea720a8c8e91ea14dc647d4f68e4351a. These are locally computed provenance hashes. Benign4 uncompressed PCAP4594492 bytes, SHA2563fb775c0391b6ad313a3f7845e634a277b07c3f6377346c2486ba63e1c22e90c; this also matches the publisher's public README.json SHA256.

Files can be retrieved under https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/IndividualScenarios/ . Dataset definitions: https://www.stratosphereips.org/datasets-iot23 . No raw PCAP or malicious executable is committed.

## SYN evidence

In capture34, 40568 valid IPv4/TCP packets from192.168.1.195 to71.61.66.148:80 have flag byte02 (SYN=1,ACK=0), and all match original-direction native Malicious/DDoS flow records within the declared1ms audit tolerance. The episode lasts22.0303seconds; counts across nonempty epoch seconds range53..1894packets. After dropping incomplete episode boundary seconds,21nonempty complete1second windows remain.

Another native DDoS stream in the same capture uses flag byte3a, which includes ACK; it is not automatically a SYN-open flood. Do not map all DDoS flows to the SYN class. Flow-to-packet matches are audit evidence; a production training pipeline still needs documented annotation rules, boundaries and treatment of mixed/unsupported traffic.

The existing Scapy feature extractor independently agrees with every six-feature raw vector for the selected21windows. The frozen lab v2 predicts SYN for all21, but these windows are from ONE22second episode and collapse to ONE quantized vector because packet_count saturates. This is an exploratory selected-class check, not an independently trained three-class IoT-23 result or evidence of generalization across captures.

## Vertical-scan coverage remains unresolved

Maximum distinct destination ports per directed IP pair among SYN-open packets over the ENTIRE supplied PCAP: capture34=2, capture3=1, filtered35subset=1, benign4=1. The two ports in capture34 occur for a C&C host, not automatically a scan. None of these inspected packet sets establishes the desired vertical-scan class. The seven inspected malware logs likewise do not establish a native labelled vertical class.

All-TCP destination-port cardinality can be much larger (e.g.1653in34) because a server replies to many client ephemeral ports. Those reply packets must not be relabelled as vertical scans. The audit tool reports SYN-open pair counts separately and tests this distinction.

This does not prove that every packet of every IoT-23 capture lacks vertical scanning. It does mean a three-class training run is not supported by the currently verified data. The source constraint has been asked explicitly: is a documented combination of IoT-23 and another vertical-scan source acceptable, or must all training data come from IoT-23? No hybrid source is silently assumed.

## New external failure of LAB v2

Protected destination192.168.1.132 in the official benign Philips Hue capture4. Retained only nonempty, complete epoch-aligned1second ingress windows, matching the existing raw-packet-count validity guard.3534ingress IPv4 packets yield2880eligible windows out of78845complete time slots. Empty slots are not classified or counted as correct negatives.

Frozen v2 predicts normal for896windows and scan for1984windows: selected-capture FPR68.8889%, normal accuracy31.1111%. There is no weight update or filtering by prediction. This exposes strong domain shift/sparse benign traffic failure; the lab100%result must not be used to justify blocking this external traffic. The arithmetic core remains consistent, but the current learned decision function is not ready for deployment outside the tested lab. Do not address this by disguising sparse valid traffic as empty or changing benign labels.

The v2 handoff can still be used for CPU/RTL arithmetic integration; new external training/validation and an untouched source-separated holdout are required before a deployment claim. All new training must be kept separate from the frozen lab v2. Existing reviewed code package now carries this finding as a notice while preserving its model/RTL bytes.

## Audit verification

New read-only tool tools/audit_iot23_scope.py handles det_label/detailed-label aliases and lowercase benign while retaining original labels, parses packet TCP flags directly, checks packet lengths/fragments and distinguishes reverse traffic. Four new tests passed with artificial log/packet fixtures; fixtures use fixed MAC addresses and do not send network traffic. First10000frames from34 were independently decoded by Scapy; all9407eligible TCP headers agree. Full selected native SYN vectors also agree with the existing feature reader. This audit does not train or evaluate an all-three-class IoT-23 model.
