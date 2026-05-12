# Certified Open-Vocabulary MOT under Partial Annotations

Method name: **PARC-Track** (Partial-Annotation Robust Certification for Open-Vocabulary Tracking)

This document is the formal experiment and paper specification for the first PARC-Track implementation. It keeps the main line focused on **Certified Open-Vocabulary MOT under Partial Annotations** rather than generic conformal prediction for OVMOT.

Core claim:

> We do not assume unmatched tracklets are false, do not assume tracklets are independent, and do not require solving a hard graph optimization problem. Instead, PARC-Track certifies released open-vocabulary trajectories using null-superset video-block e-values and polynomial self-consistent graph selection.

中文核心表述：

> 我们不假设未匹配 GT 的轨迹就是 false，不假设视频内 tracklets 独立，也不依赖 NP-hard 图优化。PARC-Track 通过 null-superset video-block e-values 和 polynomial self-consistent graph selection，在部分标注开放词表视频中认证发布轨迹的真实虚假率，并通过 protected identity skeleton 控制 CLEAR-MOT IDSW/min。

## Abstract Draft

Open-vocabulary multi-object tracking aims to localize and associate objects from arbitrary text queries, but current systems provide no statistical certificate on the reliability of released novel-category trajectories. This is particularly problematic under partial annotations, where an unmatched predicted trajectory is not necessarily false, since many real novel objects may be unlabeled. We introduce PARC-Track, a partial-annotation robust framework for certified open-vocabulary MOT. Instead of calibrating on falsely assumed negative tracklets, PARC-Track uses a null-superset video-block calibration that only requires verified positives and treats all unverified tracklets as a conservative superset of false trajectories. This yields valid block-level p-values and e-values for actual false tracklets without assuming tracklet independence. At test time, we select tracks using a polynomial-time self-consistent greedy selector, whose false tracklet rate guarantee depends only on e-value self-consistency and not on solving an NP-hard path-packing problem. To certify identity continuity, we further introduce a protected identity skeleton and prove that CLEAR-MOT identity switches are upper bounded by false links, missed protected continuations, and sensor gaps, each of which can be calibrated separately. Experiments on OVT-B, TAO/OV-TAO, BDD100K-MOT, and UAVDT evaluate certified novel-tracklet reliability, tracking quality, and identity-switch control under sparse labels and domain shift.

中文摘要：

开放词表多目标跟踪需要在任意文本查询下输出目标轨迹，但现有方法只优化 TETA、HOTA、IDF1 等准确率指标，无法保证发布的 novel-category 轨迹有多少是真实可靠的。更关键的是，OVMOT benchmark 往往是部分标注的：一个未匹配 GT 的预测轨迹不一定是 false，可能是真实存在但未标注的 novel object。我们提出 PARC-Track，一个面向部分标注开放词表跟踪的风险认证框架。PARC-Track 不把 unmatched tracklets 当作负例，而是采用 null-superset video-block calibration：只移除被可靠认证的 positive tracklets，其余未认证轨迹全部保留为 false tracklet 的保守超集。该设计在 video-level exchangeability 下得到对真实 false tracklets 有效的 block p-values 和 e-values，不需要 tracklet-level i.i.d. 假设。测试时，我们进一步提出 self-consistent greedy graph selector，用多项式时间选择满足 e-value 自洽条件的互不冲突轨迹集合，从而避免 NP-hard path-packing 优化，同时保持 false tracklet rate 控制。最后，我们构建 protected identity skeleton，证明 CLEAR-MOT IDSW/min 可由 false links、missed protected continuations 和 sensor gaps 三项上界，并分别进行有限样本校准。实验在 OVT-B、TAO/OV-TAO、BDD100K-MOT 和 UAVDT 上验证了方法在稀疏标注和域漂移下的风险控制与跟踪性能。

## 1. Introduction

Open-Vocabulary Multi-Object Tracking (OVMOT) aims to track target categories described by arbitrary text queries. Recent systems such as OVTrack, VOVTrack, OVT-B, and OVTR improve detection, classification, and association under open vocabularies, but their reported TETA, HOTA, IDF1, AssA, and ClsA metrics do not answer a deployment-critical question: among released novel-category trajectories, how many may be false, and how often may identities switch per unit time?

This is hard for four reasons.

First, OVMOT benchmarks are often partially or federatedly annotated. A predicted tracklet unmatched to ground truth is not necessarily false; it may be a real but unlabeled novel object. Treating unmatched tracklets as negative calibration examples contaminates the calibration false pool with real objects that have high objectness, semantic consistency, and temporal stability. This raises the false-block maximum, over-conservatizes calibration, and may make certified releases nearly empty.

Second, candidate tracklets in the same video are dependent. Prompt drift, occlusion, motion blur, night scenes, and crowding can produce many correlated false tracklets. The statistical unit should therefore be the video block, not the individual tracklet.

Third, releasing tracks is not simple thresholding. Candidate paths share detection nodes and association edges. Selecting one path can exclude another. Exact utility maximization under vertex-disjoint constraints reduces to hard graph selection such as maximum-weight independent set or path packing.

Fourth, identity switches are evaluator-dependent graph events. CLEAR-MOT IDSW, HOTA AssA, and IDF1 use different matching protocols. PARC-Track certifies CLEAR-MOT IDSW because it is a count-based event metric with a clean graph decomposition; HOTA and IDF1 are reported empirically.

PARC-Track converts OVMOT into a certified graph decision problem. It selects mutually compatible candidate paths that satisfy false-tracklet e-value self-consistency and identity-risk constraints.

Contributions:

1. **Partial-annotation robust certified OVMOT formulation.** We define risk-certified OVMOT under partial annotations using one-sided reliable labels: verified positives are true, while unverified tracklets remain unknown.
2. **Null-superset video-block e-values.** For each calibration video, verified positives are removed and all unknown tracklets are retained as a conservative superset of false tracklets. This yields valid p-values and e-values for actual false tracklets under video-level exchangeability.
3. **Finite-resolution aware release calibration.** We characterize the finite-sample power threshold of release-grid e-values and tune the power e-calibrator using the rule \(\gamma^\star=-1/\log(G/(n+1))\), selected only on tuning data.
4. **Polynomial self-consistent greedy graph selection.** Uniform SCS-Greedy selects compatible tracklets in polynomial time. The FTR guarantee depends only on e-value self-consistency, not on solving an NP-hard utility optimum.
5. **Protected identity skeleton for CLEAR-MOT IDSW control.** CLEAR-MOT IDSW/min is upper bounded by false links, missed protected continuations, and sensor gaps, each calibrated separately; tightness is reported empirically.

## 2. Problem Formulation

Given video \(X_{1:T}=(X_1,\ldots,X_T)\) and open vocabulary \(\mathcal V=\mathcal V_{\rm base}\cup\mathcal V_{\rm novel}\), the tracker generates at release epoch \(t\) a fixed-budget candidate path set

\[
\mathcal P_t = \{p_1,\ldots,p_M\}.
\]

Insufficient candidates are padded with dummy paths so the hypothesis universe size is fixed. Each path is a sequence of detection nodes and association edges:

\[
p=(d_{p,1},e_{p,1},d_{p,2},\ldots,d_{p,L_p}).
\]

Each detection node contains box, mask, visual embedding, predicted query/category, and frame index:

\[
d=(b_d,m_d,z_d,c_d,s_d).
\]

Each path has latent validity \(Y_p\in\{0,1\}\), where \(Y_p=1\) means a true valid tracklet and \(Y_p=0\) means an actual false tracklet. Under partial annotation, we observe only one-sided labels \(A_p\in\{0,1\}\):

\[
A_p=1 \Rightarrow Y_p=1,\qquad A_p=0 \not\Rightarrow Y_p=0.
\]

For released novel tracklets \(\mathcal R_t^{\rm novel}\), actual false discovery proportion is

\[
{\rm FDP}^{\rm actual}_t
=
\frac{\sum_{p\in\mathcal R_t^{\rm novel}}(1-Y_p)}
{|\mathcal R_t^{\rm novel}|\vee 1}.
\]

The target risk is

\[
{\rm FTR}^{\rm actual}_t
=
\mathbb E[{\rm FDP}^{\rm actual}_t]
\le \alpha_1.
\]

Because \(Y_p\) may not be fully observable on test benchmarks, experiments also report unsupported tracklet rate:

\[
{\rm UTR}_t
=
\frac{\sum_{p\in\mathcal R_t^{\rm novel}}\mathbf 1[A_p=0]}
{|\mathcal R_t^{\rm novel}|\vee 1}.
\]

Since \(Y_p=0\Rightarrow A_p=0\), actual FDP is upper bounded by UTR. Exact FTR is estimated only on audited or exhaustively checked subsets. In the experiments, audited FTR is therefore an empirical diagnostic on the supported-plus-audited released subset, not a verified upper bound on actual FTR; conservative and worst-case FTR columns are reported to make the audit-coverage assumptions explicit.

For CLEAR-MOT, let \(M_s(g)\in\mathcal I_{\rm pred}\cup\{\emptyset\}\) be the predicted ID matched to GT object \(g\) at frame \(s\). An identity switch occurs when the last matched predicted ID changes from \(i_{\rm old}\) to \(i_{\rm new}\neq i_{\rm old}\). The target identity risk is

\[
{\rm IDR}_t
=
\mathbb E\left[
\frac{{\rm IDSW}^{\rm CLEAR}_t}{\mathrm{minutes}(1:t)}
\right]
\le \alpha_2.
\]

## 3. Method: PARC-Track

PARC-Track consists of:

1. three-way data protocol;
2. candidate path generation;
3. tracklet scoring;
4. null-superset video-block calibration;
5. release-grid e-value construction;
6. finite-resolution aware \(\gamma\) tuning on the tuning set;
7. uniform self-consistent greedy graph selection;
8. protected identity skeleton.

The locked main method is **PARC-Track with Null-Superset Block E-Values, finite-resolution tuned \(\gamma\), and uniform SCS-Greedy**. Slot-weighted SCS is an appendix efficiency extension rather than the main method.

### 3.1 Three-Way Data Protocol

Data are split into tuning, calibration, and test subsets:

\[
\mathcal D
=
\mathcal D_{\rm tune}
\cup
\mathcal D_{\rm cal}
\cup
\mathcal D_{\rm test}.
\]

The tuning set freezes the detector/tracker backbone, candidate generator, beam width \(K\), merge/split thresholds, score weights, release grid, e-calibrator parameter \(\gamma\), Mondrian bins, query embedding clusters, audit budget, and IDSW budget split.

The calibration set is used only to compute null-superset block maxima and calibrate false-link, missed-continuation, and sensor-gap risk. For the cleanest finite-sample theorem, it can be split into disjoint subsets \(\mathcal D_{\rm cal}^{\rm FTR}\), \(\mathcal D_{\rm cal}^{+}\), \(\mathcal D_{\rm cal}^{-}\), and \(\mathcal D_{\rm cal}^{\rm gap}\). Cross-fitting may be used in implementation, but the main theorem uses disjoint calibration subsets.

The test set is used only for final evaluation.

### 3.2 Candidate Path Generation

For a video prefix \(X_{1:t}\), generate detection nodes \(\mathcal D_t=\{d_1,\ldots,d_N\}\) and association edges

\[
\mathcal E_t
=
\{e=(d_i,d_j): s_j>s_i,\ s_j-s_i\le G_{\max}\}.
\]

Edge features include IoU, motion, appearance, semantic agreement, mask consistency, gap length, and crowding. Candidate paths may come from baseline tracker outputs, detection-graph beam search, fragment merge/split, or top-\(K\) path proposals. The final budget is fixed to \(|\mathcal P_t|=M\). All generator hyperparameters are frozen on the tuning set.

### 3.3 Tracklet Score

At checkpoint \(L\), score path \(p\) as

\[
S_{p,L}
=
w_{\rm obj}S_{\rm obj}(p,L)
+w_{\rm sem}S_{\rm sem}(p,L)
+w_{\rm temp}S_{\rm temp}(p,L)
+w_{\rm assoc}S_{\rm assoc}(p,L).
\]

Larger scores indicate more reliable novel tracklets. The main smoke implementation uses synthetic score components but preserves this interface. Main real-data experiments can use uniform weights \(w_{\rm obj}=w_{\rm sem}=w_{\rm temp}=w_{\rm assoc}=0.25\); learned weights must be tuned only on \(\mathcal D_{\rm tune}\).

### 3.4 Mondrian Cells

Each path is assigned a Mondrian cell

\[
m(p)=({\rm novelty}(c),{\rm qCluster}(c),{\rm occ}(p),{\rm domain}(p)).
\]

Cells may include novelty bins, query embedding clusters, occlusion bins, day/night, rain/clear, camera motion, detection density, or optical-flow magnitude. If a cell has too few calibration videos, fallback is fixed on the tuning set:

\[
(\nu,q,o,d)\rightarrow(\nu,q,o)\rightarrow(\nu,q)\rightarrow\nu\rightarrow{\rm global}.
\]

## 4. Null-Superset Video-Block Calibration

In calibration video \(i\), only reliable positives are removed:

\[
A_p=1\Rightarrow Y_p=1.
\]

Unknown tracklets remain in the conservative null superset. For cell \(m\) and checkpoint \(L\):

\[
\mathcal N_{i,m,L}
=
\{p:A_p=0,\ m(p)=m,\ L_p\ge L\}.
\]

The true false set is

\[
\mathcal F_{i,m,L}
=
\{p:Y_p=0,\ m(p)=m,\ L_p\ge L\}.
\]

By one-sided reliability,

\[
\mathcal F_{i,m,L}\subseteq\mathcal N_{i,m,L}.
\]

Optional high-score audit may certify additional positives, but it must preserve \(A_p=1\Rightarrow Y_p=1\).

The null-superset block maximum is

\[
\widetilde M_{i,m,L}
=
\max_{p\in\mathcal N_{i,m,L}} S_{p,L}.
\]

If \(\mathcal N_{i,m,L}\) is empty, set \(\widetilde M_{i,m,L}=+\infty\). Since the null superset contains all false paths,

\[
\widetilde M_{i,m,L}\ge M^F_{i,m,L},
\qquad
M^F_{i,m,L}=\max_{p\in\mathcal F_{i,m,L}}S_{p,L}.
\]

## 5. Release-Grid E-Values

Use a finite time-based release grid:

\[
\mathcal L=\{0.5s,1s,2s,4s,8s,16s,\ldots,L_{\max}\}.
\]

The default weights are uniform \(w_j=1/(J+1)\), with \(\sum_j w_j\le 1\).

For test path \(p\) with \(m=m(p)\),

\[
\widetilde p_{p,L}
=
\frac{
1+\sum_{i=1}^n\mathbf 1[\widetilde M_{i,m,L}\ge S_{p,L}]
}{n+1}.
\]

The release-grid anytime p-value is

\[
\widetilde p_p^{\rm any}
=
\min_{j:L_j\le L_p}
\frac{\widetilde p_{p,L_j}}{w_j}
\wedge 1.
\]

The e-calibrator is

\[
f_\gamma(p)=\gamma p^{\gamma-1},\qquad 0<\gamma<1,
\]

with \(\int_0^1 f_\gamma(u)\,du=1\). The path e-value is

\[
E_p=f_\gamma(\widetilde p_p^{\rm any}).
\]

For actual false paths, \(\mathbb E[E_p]\le 1\).

### 5.5 Finite-Resolution Aware \(\gamma\) Tuning

With \(n\) calibration videos and a release grid with \(G\) uniform-weight checkpoints, the smallest attainable anytime p-value is

\[
p_{\min}^{\rm any}=\frac{G}{n+1}.
\]

For \(f_\gamma(p)=\gamma p^{\gamma-1}\), the largest attainable e-value is

\[
E_{\max}(\gamma,n,G)
=
\gamma
\left(
\frac{G}{n+1}
\right)^{\gamma-1}.
\]

Let \(r=G/(n+1)\). Maximizing \(\log E_{\max}=\log\gamma+(\gamma-1)\log r\) gives

\[
\gamma^\star=-\frac{1}{\log r}
=
-\frac{1}{\log(G/(n+1))}.
\]

Implementation uses this expression as a tuning guide and selects \(\gamma\) from a fixed tuning-set grid, for example

\[
\gamma\in\{0.15,0.20,0.25,0.35,0.50,0.65,0.80\}.
\]

No calibration or test labels are used to choose \(\gamma\). This tuning mainly affects power, not validity: for any fixed \(0<\gamma<1\), \(f_\gamma\) remains a valid e-calibrator.

## 6. Polynomial Self-Consistent Greedy Selector

Given \(M\) candidate paths and FTR level \(\alpha_1\), a selected set \(\widehat{\mathcal R}\) is self-consistent if

\[
p\in\widehat{\mathcal R}
\Rightarrow
E_p\ge \frac{M}{\alpha_1|\widehat{\mathcal R}|}.
\]

SCS-Greedy enumerates \(k=M,\ldots,1\), forms candidate set

\[
\mathcal C_k=\{p:E_p\ge M/(\alpha_1 k)\},
\]

sorts by utility, and greedily adds paths that do not share detection nodes, use only safe association edges, and respect the protected identity skeleton. The first size-\(k\) set found is released; otherwise the output is empty.

Using bitsets for detection conflict, a scan is \(O(M\bar L/w)\), and worst-case enumeration is \(O(M^2\bar L/w)\). No NP-hard path-packing solver is required.

### 6.4 Slot-Weighted Self-Consistency Extension

Uniform SCS uses \(a_p=1/M\), giving the threshold \(M/(\alpha_1 k)\). This is clean but can be power-inefficient when many low-priority candidate slots are retained only to keep a fixed hypothesis universe.

As an efficiency extension, assign nonnegative slot weights fixed by the tuning-set proposal protocol:

\[
a_1,\ldots,a_M\ge0,\qquad \sum_{r=1}^{M}a_r\le1.
\]

For selected path \(p\) in frozen slot \(r(p)\), require

\[
E_p
\ge
\frac{1}{\alpha_1|\widehat{\mathcal R}|a_{r(p)}}.
\]

The proof is unchanged:

\[
\frac{\mathbf 1[p\in\widehat{\mathcal R}]}
{|\widehat{\mathcal R}|\vee1}
\le
\alpha_1 a_{r(p)}E_p.
\]

Summing over false paths gives

\[
{\rm FTR}
\le
\alpha_1
\sum_{p\in\mathcal H_0}a_{r(p)}
\le
\alpha_1.
\]

Candidate schedules include uniform weights, power-law weights \(a_r\propto r^{-q}\), and exponential weights \(a_r\propto \exp(-(r-1)/\tau)\). The schedule and its parameters must be selected on the tuning set, not on calibration or test labels.

## 7. Protected Identity Skeleton

Each candidate edge has two scores:

\[
r_e^+ \quad \text{for not being a false link},
\qquad
r_e^- \quad \text{for preserving identity continuation}.
\]

Safe edges are

\[
\mathcal E^+(\lambda_+)=\{e:r_e^+\ge\lambda_+\}.
\]

Protected continuation candidates are

\[
\mathcal E^-(\lambda_-,\lambda_+)
=
\{e:r_e^-\ge\lambda_-,\ r_e^+\ge\lambda_+\}.
\]

A node-disjoint matching or forest \(\mathcal K(\lambda_-,\lambda_+)\) is built from protected continuations. Skeleton components are contracted before graph selection, so detections connected by the skeleton cannot be assigned to different predicted IDs.

## 8. Theory

Assumptions:

1. Calibration videos and test videos are video-level exchangeable.
2. Positive labels are one-sided reliable: \(A_p=1\Rightarrow Y_p=1\).
3. Candidate generator, score function, release grid, Mondrian cells, e-calibrator, and audit policy are frozen on tuning data.
4. Candidate budget is fixed at \(|\mathcal P_t|=M\).

**Theorem 1: Null-Superset Block p-Value Validity.** For any actual false test path \(p\), fixed cell \(m\), and checkpoint \(L\),

\[
\Pr(\widetilde p_{p,L}\le u)\le u,\qquad \forall u\in[0,1].
\]

Proof sketch: the test false path score is bounded by the test false block maximum; null-superset maxima dominate false block maxima; the resulting rank p-value over exchangeable video-level false block maxima is super-uniform.

**Theorem 2: Release-Grid Anytime Validity.** With \(\sum_jw_j\le1\),

\[
\Pr(\widetilde p_p^{\rm any}\le u)\le u.
\]

This follows by a finite union bound over release-grid checkpoints.

**Theorem 3: False-Path E-Value Validity.** Since the anytime p-value is super-uniform and \(f_\gamma\) integrates to one,

\[
\mathbb E[E_p]\le1
\]

for every actual false path.

**Theorem 4: SCS-Greedy Controls Actual Novel FTR.** If every false path has valid e-value and the output set satisfies self-consistency, then

\[
\mathbb E\left[
\frac{|\widehat{\mathcal R}\cap\mathcal H_0|}
{|\widehat{\mathcal R}|\vee1}
\right]
\le \alpha_1.
\]

The proof uses

\[
\frac{\mathbf 1[p\in\widehat{\mathcal R}]}
{|\widehat{\mathcal R}|\vee1}
\le
\frac{\alpha_1}{M}E_p
\]

for each false path, sums over \(\mathcal H_0\), and does not require independence or utility optimality.

**Lemma 5: CLEAR-MOT IDSW Graph Decomposition.**

\[
{\rm IDSW}^{\rm CLEAR}
\le
{\rm BadLink}^{\rm ub}(\lambda_+)
+
{\rm MissCont}^{\rm ub}(\lambda_-,\lambda_+)
+
{\rm Gap}^{\rm sensor}.
\]

Every CLEAR-MOT identity switch is covered by at least one of: a selected false link, a missed protected continuation, or a sensor/candidate-coverage gap.

**Theorem 6: Finite-Sample IDSW/min Control.** With disjoint calibration subsets and budget split

\[
\beta_++\beta_-+\beta_{\rm gap}=\alpha_2,
\]

calibrating each minute-normalized upper-bound loss to its budget yields

\[
\mathbb E\left[
\frac{{\rm IDSW}^{\rm CLEAR}_{n+1}}
{\mathrm{minutes}(n+1)}
\right]
\le \alpha_2.
\]

The default split is \(\beta_+=\beta_-=\beta_{\rm gap}=\alpha_2/3\).

**Proposition 7: Non-Trivial Discovery under Separation and Bounded Conflict.** If true eligible paths have bounded conflict degree \(\Delta\) and utility separation from false eligible paths, SCS-Greedy retains a constant fraction of eligible true discoveries:

\[
\mathbb E[
|\widehat{\mathcal R}\cap\mathcal T|
]
\gtrsim
\frac{(1-\eta)\pi_k|\mathcal T|}{\Delta+1}
\mathrm{slack}(M,k).
\]

## 9. Experiments

Datasets:

1. OVT-B for novel-category tracklet certification.
2. TAO / OV-TAO for long-tail and partial annotation.
3. BDD100K-MOT for day/night, rain/clear, and crowded driving scenes.
4. UAVDT for aerial view, small objects, camera motion, and high density.

Backbones:

1. OVMOT backbones: OVTrack, VOVTrack, OVTR if available.
2. Composable baselines: GroundingDINO or OWLv2 plus ByteTrack or OC-SORT.
3. SAM-based detector/segmenter plus association graph.
4. Oracle proposal upper bound using GT or high-quality detections to test the certification layer.

Risk-control baselines:

1. confidence threshold;
2. per-frame conformal detection threshold;
3. tracklet-level p-value plus BH;
4. tracklet-level e-BH;
5. treating unmatched as false plus block calibration;
6. null-superset block p-values;
7. null-superset block e-values;
8. null-superset plus high-score audit;
9. PARC-Track full.

Graph-selection baselines:

1. post-filter e-BH;
2. SCS-Greedy;
3. LP relaxation;
4. small-scale ILP upper bound;
5. min-cost flow where applicable.

Metrics:

Risk metrics include exact FTR on audited/exhaustive subsets, UTR on partial-label benchmarks, CLEAR-MOT IDSW/min, BadLink upper bound, MissCont upper bound, and Gap sensor risk. Tracking metrics include TETA, LocA, AssA, ClsA, HOTA, IDF1, MOTA, IDSW, novel recall, certified TETA, and delay-to-certification.

Core experiments:

1. **Missing-GT Diagnostic.** Audit high-score unmatched candidate paths to estimate actually true, actually false, and unknown proportions.
2. **FTR Control under Partial Labels.** Compare confidence thresholding, tracklet-level methods, unmatched-as-false calibration, null-superset calibration, audit-enhanced calibration, and PARC-Track.
3. **SCS-Greedy vs Post-Filtering.** Compare FTR, released tracks, true tracks, utility, and runtime.
4. **IDSW/min Control.** Report IDSW/min, certified upper bound, BadLink, MissCont, Gap, IDF1, HOTA, and tightness.
5. **Domain Stress Test.** Compare global, Mondrian, null-superset, and audit-enhanced calibration under day-to-night, clear-to-rain, normal-to-crowded, and ground-to-UAV shifts.

Ablations:

1. no audit vs top-\(B\) audit;
2. null-superset vs unmatched-as-false;
3. global vs Mondrian calibration;
4. with vs without query cluster;
5. release-grid choice;
6. uniform vs maturity weights;
7. equal IDSW budget split vs tuning-set split;
8. no protected skeleton vs protected skeleton;
9. post-filter vs SCS-Greedy;
10. score component ablation.

## 10. Paper Outline

1. Introduction: risk certificates, partial annotations, video dependence, graph selection, CLEAR-MOT binding, and PARC-Track.
2. Related Work: open-vocabulary detection/tracking, partial/federated annotations, conformal risk control and e-values, MOT identity metrics.
3. Problem Formulation: latent validity, one-sided labels, actual FTR, UTR, candidate path graph, CLEAR-MOT IDSW/min.
4. Method: split protocol, candidate paths, tracklet score, Mondrian cells, audit, null-superset calibration, release-grid e-values, SCS-Greedy, protected skeleton.
5. Theory: p-value validity, anytime validity, e-value validity, FTR theorem, IDSW decomposition, IDSW/min control, power proposition.
6. Experiments: setup, missing-GT diagnostic, FTR control, graph selection, IDSW/min, domain stress, ablations.
7. Limitations.
8. Conclusion.

## 10.1 Phase-1b Synthetic Validation Summary

The current synthetic stress results support the following paper-facing interpretation:

1. Finite p-value resolution creates a predictable release cliff governed by \(E_{\max}(\gamma,n,G)\).
2. With \(G=5\) and \(\gamma=0.5\), non-empty release starts around \(n=2400\), matching the condition \(E_{\max}\gtrsim 1/\alpha_1\) for large releases.
3. The gamma-calibration sweep validates the theoretical optimum. When \(n=800\) and \(G=5\), \(\gamma^\star\approx0.197\), and \(\gamma=0.20\) releases non-empty tracks with high recall and empirical FTR \(0.0\) in the quick synthetic setting.
4. Weighted SCS is not promoted to the main method. It can help only when proposal rank is strongly aligned with true quality and released paths concentrate on high-mass slots; in the current synthetic stress regime, finite-resolution aware \(\gamma\) tuning is the dominant power improvement.
5. IDSW certification remains a secondary contribution until real CLEAR-MOT evaluator measurements replace the synthetic proxy. Median proxy tightness is promising, but tail cases remain loose.

## 11. Limitations

1. Guarantees rely on video-level exchangeability.
2. One-sided audit requires high-precision positive certification.
3. Null-superset calibration is conservative and may reduce recall.
4. The IDSW theorem is bound to CLEAR-MOT and does not directly certify HOTA or IDF1.
5. Online recalibration requires delayed labels and is only an appendix extension.
6. Finite-sample claims apply to fixed candidate budget \(M\) and released candidate paths.

## 12. Finite p-Value Resolution and Smoke Status

With \(n\) calibration videos, the smallest block conformal p-value is

\[
p_{\min}^{\rm block}=\frac{1}{n+1}.
\]

For a finite release grid with uniform weights \(w_j=1/G\), the smallest release-grid anytime p-value is

\[
p_{\min}^{\rm any}=\frac{G}{n+1}.
\]

For the e-calibrator \(f_\gamma(p)=\gamma p^{\gamma-1}\), the largest attainable e-value is therefore

\[
E_{\max}
=
\gamma
\left(
\frac{G}{n+1}
\right)^{\gamma-1}.
\]

For SCS-Greedy to release \(k\) paths at risk level \(\alpha_1\), a necessary finite-resolution feasibility condition is

\[
E_{\max}
\ge
\frac{M}{\alpha_1 k}.
\]

In the current smoke setting, \(n=2400\), \(G=5\), and \(\gamma=0.5\), giving \(E_{\max}\approx 10.96\). This is just above the large-release self-consistency threshold near \(10\) when \(\alpha_1=0.10\) and \(k\approx M\). Smaller calibration sizes may validly produce empty releases because finite p-value resolution prevents any path from reaching the required e-value.

The smoke setting validates implementation and theorem preconditions: null-superset construction, release-grid e-values, self-consistency, SCS-Greedy compatibility constraints, and synthetic IDSW upper-bound decomposition. It is not used as the main evidence for real-data risk control. Paper claims must be based on synthetic stress tests and real-data experiments with frozen three-way splits.

The Phase-1b stress suite additionally evaluates \(\gamma\) against calibration size. For fixed

\[
r=\frac{G}{n+1},
\]

the \(\gamma\) that maximizes \(\gamma r^{\gamma-1}\) is approximately

\[
\gamma^\star=-\frac{1}{\log r}.
\]

Thus smaller calibration sets may need smaller \(\gamma\) for non-empty release. As with all e-calibrator choices, \(\gamma\) must be fixed using the tuning protocol.

## 13. Dataset Adapter Contract

A dataset can enter real MOT benchmark experiments only if its adapter verifies:

1. ordered video frame sequences;
2. per-frame tracking annotations;
3. persistent track IDs;
4. category or query labels;
5. video IDs;
6. timestamps or frame indices;
7. enough metadata to form tune/cal/test splits without leakage.

Archives that contain only images and single-frame JSON labels are cataloged as `not_mot_tracking_benchmark` and must not be used to support real OVMOT/MOT claims. They may be used only for proxy inspection or future detector-only preparation.

## 14. IDSW Tightness Protocol

For identity-risk experiments, report the CLEAR-MOT decomposition:

\[
{\rm certified\ UB}
=
{\rm BadLink}^{\rm ub}
+
{\rm MissCont}^{\rm ub}
+
{\rm Gap}^{\rm sensor}.
\]

The tightness diagnostic is

\[
{\rm Tightness}
=
\frac{{\rm certified\ UB}}{{\rm actual\ CLEAR\ IDSW/min}}.
\]

On synthetic smoke data, where a real CLEAR-MOT evaluator is not available, the implementation reports a synthetic observable proxy based on selected bad links plus uncovered selected continuations and marks it explicitly as a proxy. Real-data experiments must replace this proxy with actual CLEAR-MOT IDSW/min from the evaluator.

## 15. Phase-2 OVT-B Missing-GT Audit

The first real-data audit targets OVT-B and uses GroundingDINO only as an audit proposal generator, not as a claimed OVMOT backbone. The current Phase-2 subset processed:

```text
OVT-B videos processed: 250
GroundingDINO detections: 10809
Linked candidate paths: 3898
High-score unmatched tracklets exported for audit: 246
```

After a second-pass visual review and a targeted recheck of the overly conservative `uncertain` bucket, the audit labels are:

```text
Actually true: 184
Actually false: 57
Uncertain: 5
Actually true rate: 74.80%
Verified positives for calibration: 131
Verified positive rate: 53.25%
Audit passes: visual_audit_second_pass, visual_audit_uncertain_recheck
```

This confirms the core partial-annotation diagnostic:

\[
A_p=0\not\Rightarrow Y_p=0.
\]

High-score unmatched OVT-B tracklets frequently correspond to real visual objects, so unmatched-as-false calibration would contaminate the false pool with true but unsupported trajectories. For theoretical calibration, only rows with `verified_positive_for_calibration=yes` are removed from the null-superset; uncertain rows and unverified positives remain in the conservative unknown pool.

## 16. Phase-2 Full-Universe Real Certification Scaffold

Phase-2d persists the full linked candidate universe rather than using only the 246-row audit subset:

```text
processed videos = 250
candidate universe paths = 3898
candidate nodes / detections = 10809
test candidates = 1770
calibration candidates = 1705
```

The finite-resolution denominator is now the number of scored calibration videos, not the total number of OVT-B videos:

```text
n_dataset_total = 1973
n_processed_videos = 250
n_rank_denominator = 88
n_nonempty_null_videos = 63
n_empty_null_videos = 25
n_inf_blockmax_videos = 25
p_min_theoretical = 0.05618
p_min_effective = 1.0
verified positives removed in calibration split = 28
```

The effective p-min includes empty null-superset calibration videos, which are represented by \(+\infty\) block maxima:

\[
p_{\min}^{\rm eff}
=
\left[
\frac{
G(1+n_{\infty})
}{
n_{\rm rank}+1
}
\right]\wedge 1.
\]

With \(G=5\), \(n_{\rm rank}=88\), and \(n_{\infty}=25\), the effective p-min is capped at \(1.0\). The full-universe scaffold therefore reports empty release for all tested candidate budgets. This is a useful diagnostic: the first 250-video OVT-B scaffold has too many empty-null calibration videos under the current sparse GroundingDINO proposal subset. The next implementation step is to reduce empty-null blocks by increasing scored calibration coverage, coarsening release/checkpoint requirements, or adjusting the proposal generator, while keeping the null-superset validity rule unchanged.

## 17. Phase-2e Calibration Coverage Recovery

The conservative empty-block convention remains the default validity-first diagnostic:

\[
\widetilde M_{i,m,L}=+\infty
\quad\text{when}\quad
\mathcal N_{i,m,L}=\emptyset.
\]

This is always conservative, but it can be overly pessimistic when many calibration videos have no null-superset candidates under the current proposal generator. Phase-2e therefore adds an explicit coverage-conditional recovery variant. Define

\[
C_{i,m,L}
=
\mathbf 1[\mathcal N_{i,m,L}\neq\emptyset].
\]

The coverage-conditional block p-value ranks only against calibration videos with nonempty null-superset blocks:

\[
\widetilde p^{\rm cov}_{p,L}
=
\frac{
1+
\sum_{i:C_{i,m,L}=1}
\mathbf 1[\widetilde M_{i,m,L}\ge S_{p,L}]
}{
1+\sum_i C_{i,m,L}
}.
\]

The implementation exposes this as:

```yaml
calibration:
  empty_block_policy: coverage_conditional
```

while preserving the original:

```yaml
calibration:
  empty_block_policy: conservative_infinity
```

The first recovery certification uses a short release grid, such as \([1{\rm s},2{\rm s}]\), and a larger calibration split, such as tune/cal/test \(=0.10/0.60/0.30\). Longer release grids remain an ablation target. Before running SCS-Greedy, Phase-2e writes a coverage feasibility report with \(n_{\rm rank}\), \(n_{\rm nonempty}\), \(n_{\rm empty}\), \(p_{\min}^{\rm any}\), \(\gamma^\star_{\rm eff}\), \(E_{\max}^{\rm eff}\), and the feasibility condition

\[
E_{\max}^{\rm eff}\ge \frac{1}{\alpha_1}.
\]

This separates two failure modes: a statistically impossible release due to finite resolution, and a selector failure despite sufficient e-value resolution.

## 18. Phase-2f 500-Video Feasibility Validation

The Phase-2e coverage sweep predicts the first feasible real-data certification region around:

```text
processed videos: 500
calibration ratio: 0.50
release grid: [2s]
empty-block policy: coverage_conditional
```

Phase-2f therefore keeps the manually reviewed OVT-B audit evidence fixed and reruns only the GroundingDINO scaffold proposal generation on the first 500 OVT-B videos. The 250-video audit labels remain the trusted model-assisted review artifact and are reused only when path identifiers match. The 500-video run writes a separate candidate universe under `outputs/phase2_500/` so the completed 250-video audit evidence is not overwritten.

The primary Phase-2f outputs are:

```text
candidate_universe.csv
real_cert_500_single_summary.csv
coverage_sweep_500_single.csv
coverage_projection_check_500_single.csv
```

The projection check compares the 250-video coverage model against the observed 500-video universe:

```text
projected_n_nonempty versus observed_n_nonempty
projected_p_min_eff versus observed_p_min_eff
projected_emax_eff versus observed_emax_eff
projected_feasible versus observed_feasible
```

The first success criterion is not high recall; it is a theorem-level non-empty release:

\[
E_{\max}^{\rm eff}\ge\frac{1}{\alpha_1},
\qquad
\max_p E_p\ge\frac{1}{\alpha_1},
\qquad
|\widehat{\mathcal R}|>0,
\qquad
\min_{p\in\widehat{\mathcal R}}
\left[
E_p-\frac{M}{\alpha_1|\widehat{\mathcal R}|}
\right]\ge 0.
\]

If the 500-video single-checkpoint run remains empty, the report must state whether the blocker is insufficient attainable resolution \((E_{\max}^{\rm eff}<10)\) or insufficient observed candidate e-values \((\max_p E_p<10)\). The next escalation is 1000 processed videos with the same single-checkpoint recovery setting before attempting longer release grids.

## 19. Phase-2g High-Evidence Mass Diagnostics

The 500-video single-checkpoint scaffold crosses the finite-resolution threshold:

```text
n_cal_total = 250
n_covered = 165
p_min_effective = 0.00602
gamma_star_eff = 0.1956
Emax_effective = 11.946
required_Emax = 10.0
```

However, uniform SCS still releases no tracks. Phase-2g diagnoses this as a high-evidence mass bottleneck rather than a p-value resolution bottleneck. For a candidate budget \(M\), define the unconstrained mass ratio

\[
{\rm mass\_ratio}_k
=
\frac{\alpha_1 k E_{(k)}}{M},
\]

where \(E_{(k)}\) is the \(k\)-th largest e-value among the top-\(M\) candidates. Unconstrained SCS feasibility requires

\[
\max_k {\rm mass\_ratio}_k \ge 1.
\]

On the 500-video scaffold, the best observed setting is:

```text
method = null_superset_no_audit
M = 25
max_e = 12.52
count_e_ge_10 = 12
best_mass_ratio = 0.716
```

The gamma mass sweep over \(\gamma\in\{0.10,0.15,0.20,0.25,0.30,0.35,0.50\}\) does not change the conclusion:

```text
best_gamma_mass_ratio = 0.719
any_unconstrained_feasible = false
```

Thus the current 500-video run has enough maximum attainable evidence but too few high-evidence candidates. The next real-data escalation is 1000 processed videos with a single release checkpoint and coverage-conditional calibration, before trying longer release grids or weighted SCS.

## 20. Phase-2h 1000-Video Non-Empty Real Certification

Phase-2h scales the OVT-B scaffold to 1000 requested videos while keeping the same single-checkpoint recovery setting:

```text
release grid = [2s]
empty_block_policy = coverage_conditional
tune / cal / test = 0.10 / 0.50 / 0.40
alpha1 = 0.10
```

The proposal scaffold produces:

```text
requested videos = 1000
processed videos = 1000
videos with candidate paths = 996
GroundingDINO detections = 34101
candidate paths = 9346
unmatched audit pool = 1107
```

The observed coverage diagnostics match the projection from the 500-video run:

```text
projected covered calibration videos = 323
observed covered calibration videos = 335
projected Emax = 20.62
observed Emax = 21.25
projection feasible = true
observed feasible = true
```

For PARC-Track full, the finite-resolution diagnostics are:

```text
n_cal_total = 498
n_covered = 333
n_excluded_empty = 165
p_min_effective = 0.002994
gamma_star_eff = 0.1721
Emax_effective = 21.144
required_Emax = 10.0
```

Using the small-budget certification universe, PARC-Track obtains the first non-empty real-data certified releases:

```text
M = 25:  released = 25,  margin = 11.144, UTR = 0.040
M = 50:  released = 50,  margin = 11.144, UTR = 0.060
M = 100: released = 100, margin = 11.144, UTR = 0.080
M = 150: released = 126, margin = 0.0066, UTR = 0.079
M = 200: released = 106, margin = 2.276,  UTR = 0.075
M = 250: released = 0, high-evidence mass still insufficient
```

This establishes the first theorem-level non-empty real OVT-B certification scaffold:

\[
|\widehat{\mathcal R}|>0,
\qquad
\min_{p\in\widehat{\mathcal R}}
\left[
E_p-\frac{M}{\alpha_1|\widehat{\mathcal R}|}
\right]\ge0.
\]

The released subset initially had no overlap with the previously reviewed audit labels, so a targeted released-set audit was exported in Phase-2i. After reviewing the unsupported released paths, this run now has an audited released-set FTR diagnostic in addition to UTR.

## 21. Phase-2i Released-Set Audit Export

After the first non-empty 1000-video certification run, we export the released PARC-Track candidates for a targeted follow-up audit. The default export selects the strongest non-empty PARC row:

```text
method = parc_track_gamma_tuned_uniform_scs
candidate_budget_M = 150
released_total = 126
tau_k = 11.9048
self_consistency_margin = 0.0066
selected_e_min = 11.911
selected_e_mean = 19.679
selected_e_max = 21.144
```

The full release audit table is:

```text
outputs/phase2_1000/release_audit_parc_track_gamma_tuned_uniform_scs_M150.csv
```

Most released paths are already matched to official OVT-B annotations. The unsupported subset, which is the only part requiring additional visual review for an audited FTR estimate, contains:

```text
unsupported released paths = 10
released total = 126
UTR = 10 / 126 = 0.0794
```

The targeted unsupported audit export is:

```text
outputs/phase2_1000/release_audit_parc_track_gamma_tuned_uniform_scs_M150_unsupported.csv
outputs/phase2_1000/release_audit_parc_track_gamma_tuned_uniform_scs_M150_unsupported_labels.csv
outputs/phase2_1000/release_audit_parc_track_gamma_tuned_uniform_scs_M150_unsupported_viewer/index.html
```

This keeps the released-set audit small and directly aligned with the risk diagnostic:

\[
{\rm UTR}
=
\frac{
\#\{p\in\widehat{\mathcal R}: p\ \text{is unmatched and not verified positive}\}
}{
|\widehat{\mathcal R}|
}.
\]

After labeling the 10 unsupported released paths as `actually_true`, `actually_false`, or `uncertain`, the real-data audited FTR can be computed on the labeled released subset and compared against UTR.

The model-assisted released-set review gives:

```text
unsupported released paths = 10
actually true = 9
actually false = 0
uncertain = 1
auditor = human_visual_audit
```

Combining the official supported releases with the reviewed unsupported subset:

```text
released total = 126
official supported released = 116
audited labeled denominator = 125
audited FTR on supported + labeled released subset = 0.0
UTR = 0.0794
conservative FTR if uncertain is treated as false = 0.0079
```

The corresponding metrics are saved at:

```text
outputs/phase2_1000/release_audit_metrics_M150.csv
outputs/phase2_1000/release_audit_metrics_M150.json
```

## 22. Phase-2j Candidate-Budget Stability Around the First Release

Using the same 1000-video OVT-B scaffold, we sweep the PARC full candidate budget around the first successful point:

```text
M in {75, 100, 125, 150, 175, 200, 250}
```

The result is not isolated to \(M=150\). PARC full is non-empty for all budgets from 75 through 200:

```text
M = 75:  released = 75,  UTR = 0.0533, conservative FTR = 0.0000, margin = 11.144
M = 100: released = 100, UTR = 0.0800, conservative FTR = 0.0000, margin = 11.144
M = 125: released = 125, UTR = 0.0800, conservative FTR = 0.0080, margin = 1.911
M = 150: released = 126, UTR = 0.0794, conservative FTR = 0.0079, margin = 0.0066
M = 175: released = 106, UTR = 0.0755, conservative FTR = 0.0000, margin = 4.635
M = 200: released = 106, UTR = 0.0755, conservative FTR = 0.0000, margin = 2.276
M = 250: released = 0, high-evidence mass insufficient
```

The budget-sweep table is saved at:

```text
outputs/phase2_1000/table_m_sweep_parc_full_with_audit.csv
outputs/milestones/phase2h_first_real_nonempty/table_m_sweep_parc_full_with_audit.csv
```

This sweep strengthens the first real-data result: the non-empty certification is a stable small-budget regime rather than a single accidental operating point.

## 23. Phase-2k Three-Method Baseline Table

On the same 1000-video scaffold, same split, and same candidate-budget sweep, we compare:

1. unmatched-as-false block calibration;
2. null-superset no audit;
3. PARC full.

At the main operating point \(M=150\):

```text
unmatched-as-false block:
  released = 0
  diagnostic = resolution_below_required_emax

null-superset no audit:
  released = 126
  official supported = 116
  unsupported = 10
  UTR = 0.0794
  audited FTR = 0.0
  conservative FTR = 0.0079
  margin = 0.3799

PARC full:
  released = 126
  official supported = 116
  unsupported = 10
  UTR = 0.0794
  audited FTR = 0.0
  conservative FTR = 0.0079
  margin = 0.0066
```

The baseline table is saved at:

```text
outputs/phase2_1000/table_baseline_three_methods_with_audit.csv
outputs/phase2_1000/table_baseline_three_methods_M150.csv
outputs/milestones/phase2h_first_real_nonempty/table_baseline_three_methods_with_audit.csv
outputs/milestones/phase2h_first_real_nonempty/table_baseline_three_methods_M150.csv
```

In this global OVT-B scaffold, the primary contrast is that unmatched-as-false calibration is too conservative to release, while both null-superset variants are non-empty and satisfy the released-set audit diagnostics. The current scaffold does not yet show a power gain of audit removal over null-superset no-audit; this should be treated as an honest ablation finding and revisited with finer Mondrian cells or larger audit coverage.

## 24. Phase-2l Split-Seed Stability

We run a first seed-stability check at fixed \(M=150\), single checkpoint, coverage-conditional calibration, and PARC full:

```text
seed = 0: released = 126, UTR = 0.0794, conservative FTR = 0.0079, margin = 0.0066
seed = 1: released = 0, diagnostic = insufficient_high_e_mass_for_uniform_scs
seed = 2: released = 0, diagnostic = insufficient_high_e_mass_for_uniform_scs
```

This means the current 1000-video result is best framed as a proof-of-concept real certification scaffold rather than a split-stable main benchmark result. The seed table is saved at:

```text
outputs/phase2_1000/seed_stability/table_seed_stability_M150.csv
outputs/milestones/phase2h_first_real_nonempty/table_seed_stability_M150.csv
```

The next stability path is either to choose \(M\) on a tuning split, expand the processed OVT-B universe, or use stronger proposal coverage before claiming seed-stable real-data performance.

## 25. Current Paper Figures

The following paper-facing figures are generated:

```text
outputs/figures/fig_audit_result.png
outputs/figures/fig_gamma_heatmap.png
outputs/figures/fig_coverage_projection.png
outputs/figures/fig_m_sweep.png
outputs/figures/fig_seed_stability.png
```

The corresponding PDF versions are saved in the same directory. The milestone directory also contains PNG copies for the current frozen result.

## 26. Phase-3 journal Dual-Track Matrix

We extend the OVT-B proof-of-concept into a journal-oriented matrix while preserving the frozen first-real-nonempty milestone.

The Phase-3 OVT-B matrix uses the same 1000-video candidate universe and sweeps:

```text
alpha1 in {0.05, 0.10, 0.20}
seed in {0, 1, 2}
M in {75, 100, 125, 150, 175, 200, 250}
release grid = [2.0]
empty block policy = coverage_conditional
```

It includes eight method rows:

```text
unmatched_as_false_block
null_superset_no_audit
parc_track_gamma_tuned_uniform_scs
confidence_threshold
tracklet_p_bh
tracklet_e_bh
post_filter_e_bh
greedy_score_no_risk
```

The expanded matrix is saved at:

```text
outputs/phase3_ovtb/ovtb_alpha_seed_m_matrix.csv
outputs/phase3_ovtb/table_baseline_expanded.csv
outputs/phase3_ovtb/table_alpha_sweep.csv
```

The current stability picture is:

```text
alpha1 = 0.05: seed 0 non-empty; seeds 1 and 2 empty.
alpha1 = 0.10: seeds 0 and 1 non-empty; seed 2 empty.
alpha1 = 0.20: seeds 0, 1, and 2 non-empty.
```

At the main target \(\alpha_1=0.10\), the best PARC full operating points by seed are:

```text
seed 0: M = 150, released = 126, UTR = 0.0794, conservative FTR = 0.0079, margin = 0.0066
seed 1: M = 75,  released = 39,  UTR = 0.0256, conservative FTR = 0.0000, margin = 1.1775
seed 2: no non-empty release in the current M grid; high-evidence mass remains insufficient.
```

Thus the result now exceeds the earlier fixed-\(M\) seed check: two out of three seeds become non-empty at \(\alpha_1=0.10\) when the same \(M\)-grid is evaluated. It is still not yet a full journal-scale benchmark result; the next step is either full OVT-B coverage or stronger proposal coverage for seed 2.

## 27. CLEAR-MOT IDSW Evaluator Status

Because IDSW remains a main contribution, the code now includes a real CLEAR-MOT IDSW event evaluator. It expects event rows with:

```text
variant, video_id, frame_index, gt_id, pred_id
```

and optionally:

```text
badlink_ub, misscont_ub, gap_sensor, IDF1, HOTA
```

It outputs:

```text
actual_idsw_per_min
BadLink / MissCont / Gap
certified_UB
tightness
IDF1 / HOTA if available
```

Current command:

```bash
python -m parc_track.cli real idsw-eval --config configs/phase3_idsw_eval.yaml
```

The evaluator is implemented and unit-tested on a tiny CLEAR-MOT fixture. The current real OVT-B run reports `requires_idsw_events` because true CLEAR-MOT event exports have not yet been generated:

```text
outputs/phase3_idsw/idsw_eval_summary.json
```

This is the remaining blocker before IDSW can be claimed as a fully validated real-data result.

## 28. journal-Core Result Bundle

The paper-facing bundle is frozen at:

```text
outputs/milestones/core_results/
```

It contains current CSV tables, SHA256 hashes, and LaTeX table exports. A compact paper result summary is written to:

```text
docs/paper_results_summary.md
```

This bundle supports a dual-track writing strategy:

1. conference-style core: OVT-B audit, synthetic finite-resolution validation, OVT-B non-empty certification, expanded baselines;
2. journal extension: full OVT-B / TAO transfer, stronger seed stability, detector robustness, and real CLEAR-MOT IDSW validation.

## Implementation Note for First Smoke

The first implementation validates the statistical and graph-selection chain on synthetic partial-annotation candidate videos. The local `/datasets/MoGuiMianJu/dataset_bdd100k.zip` archive contains BDD100K 100k image/JSON label data but no detected MOT tracking sequence layout, so it is cataloged only as a future proxy dataset and is not used as evidence for real MOT benchmark performance in the first smoke run.
