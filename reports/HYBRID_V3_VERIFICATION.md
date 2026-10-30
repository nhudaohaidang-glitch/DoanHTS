# Hybrid v3: trained candidate and source-separated validation

2026-10-30. User authorized combining IoT-23 with other vertical-scan data while retaining Normal/SYN/vertical classes.

Model SHA256 e10f81b3e3ec9b458c4d574ee978cf0f2efa45954b4f8fe0c86fed6a3a26c35d. Architecture6-8-3, input divisors[8,2,1,1,1,1], shift1=7, shift2=0, hidden_scale8, score_scale64. Selected seed11/alpha0.01 by the predeclared integer validation objective. No weight was changed after accessing the reserved test PCAP.

## Real development data

Train3083windows/9captures: old v1 challenge182lab windows, IoT-23 Philips Hue4 benign2880windows, verified IoT-23 native SYN-only DDoS episode34 with21complete windows. Validation1829windows/11captures: old v2 holdout210lab windows, IoT-23 Amazon Echo5 benign1619windows. Earlier challenge/holdout data is explicitly DEVELOPMENT for v3, not v3 independent test. Vertical labels come from recorded controlled-lab attacks, never renamed from horizontal IoT-23 labels. All samples use exactly the existing one-second packet-derived contract and nonempty-window validity rule.

Quantized training data has55unique normal,27SYN,25scan points. Class balancing repeats these to165fit rows. These repeats are not independent captures or additional traffic. Evaluate metrics on all original windows. Train integer:3083/3083; validation float/integer:1829/1829, macro-F1=1, FPR0, capture-balanced class recall1. Threshold baseline selected only on validation is also perfect; no AI-over-baseline advantage is claimed.

Nine candidates were fitted (seeds11/23/47 x alpha0.01/0.1/0.001), selected using equal capture weighting within each class, macro-F1 then worst-source FPR ties. Search produced one convergence warning overall. Independent rerun of the selected train configuration converged in189iterations with no warning and reproduced identical integer arrays; original frozen model/metrics were left unchanged. Floating coefficients are saved separately for reproducibility and hashed in FREEZE.json.

## Reserved external test

Somfy01 was fixed in the protocol before fitting and its PCAP was fetched only after model freeze; protected192.168.1.158 came from publisher flow metadata before packet-feature inspection. It is an IPv4 ingress subset, not a claim about every protocol/endpoint in the capture.705nonempty complete windows all correctly normal, FPR0 for float/integer and baseline. On the SAME705windows, frozen v2 yields486normal and219scan, FPR31.0638%. Test weights were never retuned after this result.

This external test has ONLY normal. No held-out native IoT-23 SYN/vertical claim is supported. SYN native34 is one22second training episode; after quantization all21windows become one point. Fresh post-freeze lab collection remains necessary for a complete new three-class test.11session hybrid-v3 profile includes sparse normal, changed payloads/rates and guarded namespace reset/resume. It has not run in this cloud (network namespaces unavailable).

## Software and arithmetic verification

-57unittests passed, including four new hybrid protocol/data/evaluation checks plus existing real-loopback MQTT tests and network lifecycle mocks. New network-packet fixtures do not send packets.
-Actual selected model exported to self-contained Gowin v3; generic HEX core and embedded ROM core each PASS550vectors,84cycles. Testbench covers reset, latched input, ignored start while busy, done pulse and stable outputs.
-Python/Bash syntax and diff whitespace checked. v1/v2 default paths/version behavior retained; v3 has separate files, model and data folders.
-The packet/cache data comes from reviewed official source hashes in spec/HYBRID_V3_SOURCES.json; predeclared split/test protocol in spec/HYBRID_V3_PROTOCOL.json. No arbitrary new class mapping, synthetic training feature table, or PCAP replay was used. The trained weights use genuine provided lab CSV and actual native PCAP-derived features.

Vendor synthesis, routed timing, FPGA/CPU/bus integration, actual packet blocking and end-to-end latency remain unmeasured for v3. Prior v2 Gowin resource/Fmax screenshots cannot be reused as v3 measurements. Package preserves old frozen lab v2 and includes the reserved native cache only for frozen evaluation; it cannot be imported into development by the builder.

## Delivery smoke check

Code/model updater contains129payload files. Installation on the previous committed kit changes52files; four protected data/model/environment sentinels remain byte-identical, and reapplying reports already_current. Installed payload passes all57tests, evaluates the shipped Somfy cache against the shipped frozen model, and produces the11session hybrid-v3 dry-run plan. Development downloader verifies the three already-downloaded native sources; the prepare CLI rebuilds a CSV byte-identical to the actual4912row development input. The public update contains no raw PCAP, ELF, object or simulation executable, and no raw uploaded lab CSV; it contains the trained model, metadata/vectors and the small public native test feature cache. Independent scalar checks all550exported vector scores/classes; compiled C guard accepts1/7/8packets and skips onlyRAW0/null output.
