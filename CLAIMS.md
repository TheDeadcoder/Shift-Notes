# Claims and evidence

Each claim of the second study, the hypothesis it belongs to, its status in [PREREGISTRATION-V2.md](PREREGISTRATION-V2.md), the evidence, and the command that prints that evidence.

## How to read the tables

- **Arms.** A1 runs every shift under the over-blocking guard and A4 under the repaired guard. A1R starts from A1's notes after shift 4 and runs shifts 5 to 8 under the repaired guard. A1G and A1W do the same from the guard-scoped copy of those notes and from an empty file.
- **Numbers.** A difference is a mean over yoked lineages with a bootstrap 95% interval. A test is the one-sided paired sign-flip test unless stated. Readers face the repaired guard.
- **Status.**
  - *primary*: the one primary test.
  - *family*: one of the six secondary tests, adjusted together by Holm's method.
  - *pre-set*: a test fixed in Part B outside the family.
  - *reported*: an estimate, a check or a descriptive table that the preregistration says is reported.
  - *exploratory*: named as exploratory in the preregistration.
  - *exploratory, unnamed*: not named in the preregistration.
- **Where.** The command, then the start of the line or block that holds the figures.

## Commands

Every command reads only the `results` folder and the configs, so all of them run in a clean clone.

**C1**, the tests of the preregistration, the other readers and the probe on the other file sets:

```bash
P=results/v2
python -m swarmgate.e1 v2-report --public $P --battery $P/battery-gemini \
  --coding $P/notes-coding/codes-deepseek-v4-flash.jsonl \
  --multi-turn $P/h2-study/responses.jsonl --probe $P/h3-study \
  --readers $P/battery-gemini,$P/battery-deepseek,$P/battery-claude,$P/battery-qwen \
  --explore $P/h3-explore-claude,$P/h3-explore-qwen,$P/h3-explore-effect,$P/h3-explore-effect-ow
```

**C2**, the first reader on every notes source:

```bash
python -m swarmgate.e1 battery-report --public $P --out $P/battery-gemini --kinds syn --shifts 4,8 \
  --configs configs/e1-v2.yaml,configs/e1-v2-nogf.yaml,configs/e1-v2-hygiene.yaml,configs/e1.yaml
```

**C3**, another reader on the notes after shift 4 (`battery-deepseek` and `battery-qwen` hold the other two):

```bash
python -m swarmgate.e1 battery-report --public $P --out $P/battery-claude --kinds syn --shifts 4 \
  --configs configs/e1-v2.yaml,configs/e1-v2-ow.yaml
```

**C4**, the shifts after the repair:

```bash
python -m swarmgate.e1 after-repair --public $P \
  --coding $P/notes-coding/codes-deepseek-v4-flash.jsonl,$P/notes-coding-mitigation/codes-deepseek-v4-flash.jsonl \
  --repair $P/notes-coding/repair-deepseek-v4-flash.jsonl,$P/notes-coding/repair-second.jsonl
```

**C5**, the edited copies:

```bash
python -m swarmgate.e1 mitigate-report --out $P --codes $P/notes-coding-edits/codes-deepseek-v4-flash.jsonl \
  --original $P/notes-coding/codes-deepseek-v4-flash.jsonl
```

**C6**, the codes by shift and the agreement between the coders:

```bash
python -m swarmgate.e1 notes-code-report --out $P/notes-coding
python -m swarmgate.e1 notes-code-report --out $P/notes-coding-nogf
python -m swarmgate.e1 notes-code-report --out $P/notes-coding-hygiene
```

**C7**, the tests on codes with the second coder as primary:

```bash
python -m swarmgate.e1 v2-report --public $P --battery $P/battery-gemini --coding $P/notes-coding/codes-second.jsonl
```

**C8**, the figures:

```bash
python -m swarmgate.e1 figures
```

**C9**, mechanical potency and what the sessions did:

```bash
python -m swarmgate.e1 potency-report --public $P --config configs/e1-v2.yaml
python -m swarmgate.e1 potency-report --public $P --config configs/e1-v2-ow.yaml
python -m swarmgate.e1 chain-report --public $P \
  --configs configs/e1-v2.yaml,configs/e1-v2-ow.yaml,configs/e1-v2-effect.yaml,configs/e1-v2-effect-ow.yaml
```

## Replication

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| With the notes of over-blocked lineages, a reader succeeds against the repaired guard more often than with the notes of control lineages (Claude Sonnet 5 as donor) | H1, primary | A1 − A4 after shift 4: 0.438 [0.295, 0.583] over 24 pairs, p < 0.0001. Supported | C1, `H1` |
| The same holds with Qwen 3.5 397B as donor | H1-OW, family | 0.070 [0.023, 0.125] over 32 pairs, p = 0.0066, Holm p = 0.0198. Supported | C1, `H1-OW` |
| The reader separates the anchors | validity condition of H1 | Empty file 0.03, positive control 0.68 | C2, `gate` |
| The reader has not changed since the first study | H1, reported | The first study's files read again: 0.468 [0.327, 0.590] over 13 pairs, p = 0.0005 | C2, `paired difference` |
| The result does not rest on the objectives, on the parser or on one lineage | H1, reported; one lineage left out is exploratory, unnamed | Exact objectives 0.576 [0.417, 0.729]; all objectives 0.507 [0.361, 0.649]; lenient parser 0.438. One lineage left out: 0.413 to 0.460 for H1; 0.056 to 0.075 with p at most 0.0132 for H1-OW | C1, `reader gemini-pro-flex`, `one lineage or pair left out` |
| The notes change what the reader's command does, not how often it sends one | exploratory, unnamed | Attempt rate, A1 − A4: 0.028 [-0.003, 0.066], p = 0.1250 with Claude's notes; -0.039 [-0.172, 0.094], p = 0.7268 with Qwen's | C1, `reader gemini-pro-flex` |
| Running the commands written in the notes finds next to nothing | H1, reported | Mechanical potency after shift 4: 0.01 for A1 and 0.00 for A4 with Claude as donor, 0.00 and 0.00 with Qwen; positive control 1.00 | C9, `potency-report` |

## Stealth

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| With the notes, a reader that may issue several commands succeeds before its first denial | H2, family | A1 − A4: 0.490 [0.354, 0.620] over 24 pairs, p < 0.0001, Holm p < 0.0001. Anchors: empty file 0.00, positive control 0.83. Supported | C1, `H2` |
| The advantage shrinks as more denials are allowed and does not vanish | exploratory | Success before the 1st, 2nd and 4th denial and at any point: A1 0.52 0.66 0.80 0.83; A4 0.03 0.09 0.33 0.47 | C1, `H2 success before`; C8, `results.pdf` (c) |

## Knowledge

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| The notes do not make a reader better at telling which forbidden commands the repaired guard blocks | H3, family | Boundary score, A1 − A4, four readers: 0.018, 0.018, -0.016, -0.015; all four passed their anchors; family p = 0.9062. Not supported | C1, `H3` |
| The notes leave a stale picture: readers expect the repaired benign commands to be blocked | H3b, pre-set, added after development | Predicted blocking, A1 − A4: 0.437 [0.365, 0.508], 0.293 [0.242, 0.342], 0.288 [0.232, 0.340], 0.393 [0.335, 0.449]; largest p < 0.0001. Supported | C1, `H3b` |
| The stale picture follows the two repaired files, not the tool | H3b, reported | Rise in predicted blocking, lowest and highest reader: 0.567 to 0.788 on commands the old guard blocked on those files; 0.493 to 0.672 on commands it allowed on the same files; 0.023 to 0.100 on other objects | C1, `H3b split` |
| It is there in the second donor's notes and in the effect class | exploratory | Qwen's notes after shift 4: 0.146 to 0.186. Effect class: 0.338 to 0.438 with Claude as donor (three readers; the fourth failed its anchors there), 0.116 to 0.157 with Qwen. Each p at most 0.0015 | C1, `probe folder` |

## Persistence through the repair

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| After the repair, the notes still raise reader success | H4a, family | A1R − A4 after shift 8: 0.281 [0.153, 0.420] over 24 pairs, p = 0.0001, Holm p = 0.0006. Supported | C1, `H4a` |
| About two thirds of the gap is left | H4b, reported | Retained share 0.64 [0.41, 0.88] | C1, `H4b` |
| The notes still hold a labelled recipe | H4c, pre-set | After shift 8: A1R 19/24, A4 0/24, p < 0.0001. Of the lineages with one after shift 4, still there: A1 18/18, A1R 16/18. Supported, so H4 is supported | C1, `H4c` |
| Against no repair, the repair lowers reader success and leaves the labelled recipe almost as common | section 10, exploratory | A1R − A1 after shift 8, two-sided: reader score -0.132 [-0.243, -0.028] over 24 pairs, p = 0.0338; labelled recipe A1R 19/24, A1 20/24, p = 1.0000 | C1, `repair against no repair` |
| The same holds with Qwen as donor | H4c, reported | A1R 22/32, A4 0/32; still there: A1 24/24, A1R 22/24 | C1, `qwen3.5-397b, exploratory` |
| Agents meet the repair and do not record it as one | section 10, reported | Claude, A1R, shifts 5 to 8: a formerly denied command ran in 59 of 96 sessions; an over-blocked object was reached in 71 (A4 94, A1 43). The notes say a denied action now works in 43/96 files (second coder 49/96); they put it down to a change in the reviewer in 0 (1) and to inconsistency in 41 (45). Qwen, A1R: 80 of 128 sessions; 13/128 files (6/128) | C4, `shifts 5 to 8` |
| The stale picture also outlasts the repair | exploratory, unnamed | Predicted blocking, A1R − A4 after shift 8 as a share of A1 − A4 after shift 4, lowest and highest reader: 0.49 to 0.58 on Claude's notes, 0.71 to 1.04 on Qwen's | C1, `probe folder` |

## Revocation at repair time

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| Removing what the notes say about the reviewer removes more of the gap than a generic audit | H5, family | Audited − guard-scoped copy: 0.069 [-0.045, 0.188] over 24 pairs, p = 0.1546, Holm p = 0.3092. Not supported | C1, `H5` |
| The two scoped edits meet the criterion of 0.2 on the point estimate, and the audit and the notice do not | section 11, reported | Residual share: object-scoped 0.05 [-0.07, 0.17], guard-scoped 0.11 [-0.05, 0.32], notice 0.25 [0.11, 0.38], audit 0.27 [0.07, 0.52] | C2, `paired difference` |
| The edits remove most labelled recipes, and the notice removes none | section 11, reported | Labelled recipe: unedited 18/24, notice 21/24, audit 7/24, object-scoped 5/24, guard-scoped 1/24. No editor refusal | C5 |
| Going on from the guard-scoped copy or from an empty file costs no tickets | section 11, reported | Tickets completed against A1R, in percentage points: A1G 1.6 [0.0, 3.6], A1W 2.1 [0.5, 4.2], both within 5 points. Labelled recipe after shift 8: A1G 1/24, A1W 1/24 | C4, `claude-sonnet-5 syn e1v2-mit` |
| On the probe, the audit leaves more of the stale picture than the guard-scoped edit | exploratory, unnamed | Predicted blocking, audited − guard-scoped copy, four readers: 0.179, 0.173, 0.175, 0.195; each p at most 0.0001 | C1, `probe folder` |

## Guard class

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| Under the same over-blocking, the taint guard leaves fewer labelled recipes than the command-based guard | H6, family | 26 pairs: 16 SYN only, 1 effect only, p = 0.0001, Holm p = 0.0006. Supported | C1, `H6` |
| Over-blocking was the same in both classes | H6, reported | A1 sessions denied on an over-blocked object, shifts 1 to 4 together: 84 of 96 (SYN) and 46 of 52 (effect) with Claude as donor; 111 of 128 and 50 of 52 with Qwen | C9, `chain-report` |

## Other readers

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| A second reader repeats the result | H1 and H1-OW, exploratory | DeepSeek V4 Flash: 0.132 [0.069, 0.212], p < 0.0001 with Claude's notes; 0.065 [0.023, 0.117], p = 0.0039 with Qwen's. Anchors 0.00 and 0.93 | C1, `reader deepseek-v4-flash` |
| A reader that mostly declines gains nothing from the notes | H1 and H1-OW, exploratory | Claude Sonnet 5 sends a command in 0.11 of trials with A1 notes and 0.08 with A4 notes when Claude is the donor, and in 0.22 and 0.29 when Qwen is. Anchors 0.00 and 0.72; difference 0.000 with either donor's notes | C1, `reader claude-sonnet-5`; C3, `syn` |
| One reader cannot be interpreted | H1 and H1-OW, exploratory | Qwen 3.5 397B: anchors 0.00 and 0.10, not informative | C1, `reader qwen3.5-397b` |

## Prompt arms

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| Without the good-faith sentence the notes hold a labelled recipe more often, and with the hygiene sentence in the merge less often | exploratory | Share of A1 notes with a labelled recipe after shift 4: 0.92 without the good-faith sentence and 0.23 with the hygiene sentence, 13 lineages each; 0.75 in the main arm, 24 lineages | C6, `claude-sonnet-5 syn A1 g4` |
| Reader success moves the same way | exploratory | Success after shift 4: 0.56 and 0.10; 0.47 in the main arm | C2, `claude-sonnet-5 syn` |

## Coding

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| The two coders agree on the codes that the tests use | section 7, reported | Recipe: agreement 0.94, kappa 0.88. Labelled: agreement 0.96, kappa 0.92. 1328 double-coded files | C6, `agreement` |
| The tests on codes do not depend on which coder is primary | exploratory | Second coder as primary. H6: 15 SYN only, 1 effect only, p = 0.0003. H4c: A1R 18/24, A4 0/24 | C7, `H6`, `H4c` |
