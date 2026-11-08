# Capture35 automatic-label correction

The user reported378 packet-level native-DDoS-matched SYN-open packets,406 complete nonempty ingress windows, and9 windows satisfying the extractor's pure-SYN/native-DDoS rule. All9 exported raw vectors were [1,60,127,1,1,1].

The previous generic extractor incorrectly wrote project class1 labels from that packet rule alone. One SYN per second does not establish SYN flood, and a native DDoS flow label does not establish its subtype in every constituent window. The feature vector also cannot establish Normal; no replacement Normal labels are justified.

The corrected generic extractor exports only unlabelled packet-pattern candidates at all rates. It does not add a post-hoc PPS threshold, change the model, change the feature contract, or remove valid q0=0 windows. The previously manually reviewed capture34 source and frozen model/data are unchanged.

The local repair utility preserves the original generated y.csv under a clearly marked legacy name, backs up/replaces the old generated HTML page, and copies candidates without project labels. Original features, native labels, PCAPs and source reports remain intact. It audits every complete ingress window in the existing evidence CSV, including mixed windows, so the9 sparse pure windows are not used to claim absence of concentrated SYN traffic in the entire capture. The actual peak values for the user's406 windows are not available in this workspace yet.

Tests cover sparse and dense synthetic inputs without automatic project labels, exact raw/q preservation, reversible label/page backups, repeated repair, refusal to overwrite user-modified labels, rejection of misaligned evidence, and the distinction between pure-window samples and mixed-window SYN peaks.
