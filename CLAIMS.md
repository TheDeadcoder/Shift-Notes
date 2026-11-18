# Claims and evidence

Each claim of the second study, the hypothesis it belongs to, its status in [PREREGISTRATION-V2.md](PREREGISTRATION-V2.md), the evidence, and the command that prints that evidence.

The last two sections do the same for the first study and for the steps that were run before its chains.

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
  - *earlier, recorded*: run before the first study's chains and stated with its outcome in section 6 of [PREREGISTRATION.md](PREREGISTRATION.md).
  - *earlier*: run before the first study's chains, with no registered test.
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
  --explore $P/h3-explore-claude,$P/h3-explore-qwen,$P/h3-explore-effect,$P/h3-explore-effect-ow \
  --prompt-arms configs/e1-v2-nogf.yaml=$P/notes-coding-nogf/codes-deepseek-v4-flash.jsonl,configs/e1-v2-hygiene.yaml=$P/notes-coding-hygiene/codes-deepseek-v4-flash.jsonl
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

**C5**, the edited copies, with each coder:

```bash
python -m swarmgate.e1 mitigate-report --out $P --codes $P/notes-coding-edits/codes-deepseek-v4-flash.jsonl \
  --original $P/notes-coding/codes-deepseek-v4-flash.jsonl
python -m swarmgate.e1 mitigate-report --out $P --codes $P/notes-coding-edits/codes-second.jsonl \
  --original $P/notes-coding/codes-second.jsonl
```

**C6**, the codes by shift and the agreement between the coders; the fourth command gives the codes of the second coder:

```bash
python -m swarmgate.e1 notes-code-report --out $P/notes-coding
python -m swarmgate.e1 notes-code-report --out $P/notes-coding-nogf
python -m swarmgate.e1 notes-code-report --out $P/notes-coding-hygiene
python -m swarmgate.e1 notes-code-report --out $P/notes-coding --primary codes-second.jsonl --second codes-deepseek-v4-flash.jsonl
```

**C7**, the tests on codes with the second coder as primary:

```bash
python -m swarmgate.e1 v2-report --public $P --battery $P/battery-gemini --coding $P/notes-coding/codes-second.jsonl
```

**C8**, the figures:

```bash
python -m swarmgate.e1 figures
```

**C9**, mechanical potency and what the sessions did; the last command covers the prompt arms and the two branches:

```bash
python -m swarmgate.e1 potency-report --public $P --config configs/e1-v2.yaml
python -m swarmgate.e1 potency-report --public $P --config configs/e1-v2-ow.yaml
python -m swarmgate.e1 chain-report --public $P \
  --configs configs/e1-v2.yaml,configs/e1-v2-ow.yaml,configs/e1-v2-effect.yaml,configs/e1-v2-effect-ow.yaml
python -m swarmgate.e1 chain-report --public $P \
  --configs configs/e1-v2-nogf.yaml,configs/e1-v2-hygiene.yaml,configs/e1-v2-mitigation.yaml
```

**C10**, the hand-coded samples of the first and the second study:

```bash
python -m swarmgate.e1 hand-report --dir results/e1/hand-coding
python -m swarmgate.e1 hand-report --dir $P/hand-coding
```

**C11**, the audit of what a denial reveals: the main set of hidden guards, the set on which an observer is told the space of guards, and the pilot set:

```bash
python -m swarmgate.e0 analyze --config configs/e0.yaml --public results/e0
python -m swarmgate.e0 analyze --config configs/e0-space.yaml --public results/e0
python -m swarmgate.e0 analyze --config configs/e0-pilot.yaml --public results/e0
```

**C12**, the willingness probe:

```bash
python -m swarmgate.e1 probe-summary --public results/e1
```

**C13**, the scripted sessions that end with the request for handoff notes:

```bash
python -m swarmgate.e1 vignette-report --run results/e1/vignettes
```

**C14**, the donor pilots:

```bash
python -m swarmgate.e1 pilot-report --config configs/e1-pilot.yaml --public results/e1
python -m swarmgate.e1 pilot-report --config configs/e1-pilot-ow.yaml --public results/e1
```

**C15**, what the sessions of the first study did, and its mechanical potency:

```bash
F=results/e1
python -m swarmgate.e1 chain-report --public $F
python -m swarmgate.e1 potency-report --public $F --config configs/e1.yaml
python -m swarmgate.e1 potency-report --public $F --config configs/e1-ow.yaml
```

**C16**, the notes of the first study as coded: with the second coder, with the other donor's model on a sample, and with the two coders exchanged:

```bash
python -m swarmgate.e1 notes-code-report --out $F/notes-coding --second codes-gemini.jsonl
python -m swarmgate.e1 notes-code-report --out $F/notes-coding
python -m swarmgate.e1 notes-code-report --out $F/notes-coding --primary codes-gemini.jsonl --second codes-deepseek-v4-flash.jsonl
```

**C17**, the reader battery of the first study, for each of its two readers:

```bash
python -m swarmgate.e1 battery-report --public $F --out $F/battery-gemini --kinds syn
python -m swarmgate.e1 battery-report --public $F --out $F/battery
```

## Sessions and notes

What the sessions did and what their notes hold, before any reader. None of these counts is a test of the preregistration.

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| The second study has 1,624 sessions, and they ran as planned | exploratory, unnamed | SYN: 480 sessions with Claude Sonnet 5 as donor and 640 with Qwen 3.5 397B. Effect class: 104 with each donor. 52 in each prompt arm. 192 in the two branches from edited notes. One session refused (Claude, SYN, A1); no merge refused; no malformed tool call | C9, `sessions)` and `refused` |
| Under the over-blocking guard the agents are denied, under the repaired guard hardly at all | exploratory, unnamed | SYN, shifts 1 to 8, sessions with a denial: A1 143/192 and A4 3/192 (4 denials) with Claude as donor; A1 187/256 and A4 25/256 (37 denials) with Qwen. No A4 session is denied on an over-blocked object | C9, `denials` and `by shift` |
| Agents of over-blocked lineages work around the block | exploratory, unnamed | A workaround after a denial, SYN, shifts 1 to 8: in 65 of 192 A1 sessions and 18 of 24 lineages (Claude); in 70 of 256 and 24 of 32 (Qwen). Through shift 4: 42 sessions in 18 lineages (Claude), 35 in 19 (Qwen) | C9, `workarounds` and `workarounds through each shift` |
| Over-blocking costs tickets | exploratory, unnamed | SYN, shifts 1 to 8, A1 against A4: tickets 356/384 against 383/384 (Claude), 490/512 against 509/512 (Qwen); lineages that fail a ticket 12/24 against 1/24, two-sided Fisher p = 0.0007, and 12/32 against 1/32, p = 0.0012 | C9, `tickets` and `failing_lineages` |
| After shift 4 the notes of over-blocked lineages hold a labelled recipe and control notes do not | exploratory, unnamed | A1 18/24 against A4 0/24 (Claude) and 24/32 against 1/32 (Qwen); two-sided Fisher p < 0.0001 for each. Second coder: 21/24 against 0/24, and 22/32 against 0/32 | C6, first and fourth command, `final` and `syn labelled` |
| The share of notes with a labelled recipe rises over the first shifts and then stays | section 13, exploratory, for shifts 5 to 8; exploratory, unnamed, before | Claude, A1, shifts 1 to 8: 0.58, 0.62, 0.88, 0.75, 0.83, 0.79, 0.83, 0.83 (second coder 0.58, 0.62, 0.88, 0.88, 0.88, 0.88, 0.83, 0.83). A1R, shifts 5 to 8: 0.83, 0.71, 0.88, 0.79 (0.88, 0.83, 0.79, 0.75). A4: 0 except 0.04 at shift 6. Qwen, A1: 0.31, 0.56, 0.62, 0.75, 0.78, 0.78, 0.78, 0.81 | C6, first and fourth command, column `labelled` |
| A recipe that is in the notes after one shift is there after the next | exploratory, unnamed | Code `recipe`, SYN: 123/127 (Claude, A1), 53/58 (A1R); 146/150 (Qwen, A1), 70/72 (A1R) | C6, `retention` |
| In later shifts, agents of over-blocked lineages reach the over-blocked object before any denial | exploratory, unnamed | SYN, A1, sessions by shift 1 to 8: 0, 0, 4, 3, 5, 5, 5, 7 of 24 (Claude); 0, 1, 4, 9, 10, 12, 13, 13 of 32 (Qwen) | C9, `by shift`, fifth number |

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
| Reader success by notes source, lineage and objective | H1, reported | After shift 4: A1 0.47, A4 0.03; at least one success with the notes of 20/24 A1 lineages and 8/24 A4 lineages. Successes by objective, of 72 trials: A1 S1 44, S2 31, S3 19, S4 42; A4 0, 4, 1, 5. A command is sent in 1.00 (A1) and 0.97 (A4) of trials, and in 0.60 with the empty file | C2, `e1v2:A1@4`, `e1v2:A4@4`, `anchor` |
| Reader success is concentrated in the lineages whose notes hold a labelled recipe | exploratory, unnamed | Claude as donor, A1 after shift 4: 0.60 in the 18 lineages with a labelled recipe, 0.08 in the 6 without | C1, `reader score by notes content` |

## Stealth

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| With the notes, a reader that may issue several commands succeeds before its first denial | H2, family | A1 − A4: 0.490 [0.354, 0.620] over 24 pairs, p < 0.0001, Holm p < 0.0001. Anchors: empty file 0.00, positive control 0.83. Supported | C1, `H2` |
| The advantage shrinks as more denials are allowed and does not vanish | exploratory | Success before the 1st, 2nd and 4th denial and at any point: A1 0.52 0.66 0.80 0.83; A4 0.03 0.09 0.33 0.47 | C1, `H2 success before`; C8, `results.pdf` (c) |
| With control notes the reader still succeeds in about half of its episodes, after denials; with no notes in a fifth | exploratory | Success at the first command: A1 0.47, A4 0.03. How episodes ended: A1 success 160, declined 28, budget 4; A4 success 91, declined 85, budget 16. With the empty file: none before a denial, 5 of 24 at any point | C1, `H2 by arm` |
| The notes cut the denials an episode meets by more than half and do not end them | exploratory, unnamed | Episodes with at least one denial: A1 92/192, A4 178/192. Denials per episode: 1.02 against 2.43. Successes that follow a denial: 60/160 against 85/91. With the empty file: 19/24 episodes, 0.88 denials per episode, 5/5 successes | C1, `H2 denials by arm` |

## Knowledge

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| The notes do not make a reader better at telling which forbidden commands the repaired guard blocks | H3, family | Boundary score, A1 − A4, four readers: 0.018, 0.018, -0.016, -0.015; all four passed their anchors; family p = 0.9062. Not supported | C1, `H3` |
| The notes leave a stale picture: readers expect the repaired benign commands to be blocked | H3b, pre-set, added after development | Predicted blocking, A1 − A4: 0.437 [0.365, 0.508], 0.293 [0.242, 0.342], 0.288 [0.232, 0.340], 0.393 [0.335, 0.449]; largest p < 0.0001. Supported | C1, `H3b` |
| The stale picture follows the two repaired files, not the tool | H3b, reported | Rise in predicted blocking, lowest and highest reader: 0.567 to 0.788 on commands the old guard blocked on those files; 0.493 to 0.672 on commands it allowed on the same files; 0.023 to 0.100 on other objects | C1, `H3b split` |
| It is there in the second donor's notes and in the effect class | exploratory | Qwen's notes after shift 4: 0.146 to 0.186. Effect class: 0.338 to 0.438 with Claude as donor (three readers; the fourth failed its anchors there), 0.116 to 0.157 with Qwen. Each p at most 0.0015 | C1, `probe folder` |
| The probe separates the anchors for every reader, and a second sampling of the same files moves the boundary score both ways | H3, reported, for the anchors; exploratory for the second sampling | Boundary score with the empty file and with the positive control: 0.47 and 0.87 (Gemini 3.1 Pro), 0.47 and 0.88 (Claude Sonnet 5), 0.41 and 0.92 (Qwen 3.5 397B), 0.39 and 0.84 (DeepSeek V4 Flash). Second sampling, A1 − A4, in the same order: 0.016 [-0.016, 0.049]; 0.045 [0.022, 0.070], p = 0.0004; -0.031 [-0.061, -0.006]; 0.002 [-0.012, 0.022] | C1, `H3 anchors`, `probe folder results/v2/h3-explore-claude` |
| With chain notes of either arm, readers often do not tell forbidden commands apart at all | exploratory, unnamed | Replies that give all 24 forbidden commands one probability, with A1 and with A4 notes, of 48: Gemini 3.1 Pro 29 and 32; DeepSeek V4 Flash 22 and 26; Qwen 3.5 397B 6 and 3; Claude Sonnet 5 1 and 0. Replies with a boundary score of exactly one half: Gemini 34 and 48; DeepSeek 33 and 29; Qwen 17 and 9; Claude 5 and 1 | C1, `H3 replies with one probability` |

## Persistence through the repair

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| After the repair, the notes still raise reader success | H4a, family | A1R − A4 after shift 8: 0.281 [0.153, 0.420] over 24 pairs, p = 0.0001, Holm p = 0.0006. Supported | C1, `H4a` |
| About two thirds of the gap is left | H4b, reported | Retained share 0.64 [0.41, 0.88] | C1, `H4b` |
| The notes still hold a labelled recipe | H4c, pre-set | After shift 8: A1R 19/24, A4 0/24, p < 0.0001. Of the lineages with one after shift 4, still there: A1 18/18, A1R 16/18. Supported, so H4 is supported | C1, `H4c` |
| Against no repair, the repair lowers reader success and leaves the labelled recipe almost as common | section 10, exploratory | A1R − A1 after shift 8, two-sided: reader score -0.132 [-0.243, -0.028] over 24 pairs, p = 0.0338; labelled recipe A1R 19/24, A1 20/24, p = 1.0000 | C1, `repair against no repair` |
| The same holds with Qwen as donor | H4c, reported | A1R 22/32, A4 0/32; still there: A1 24/24, A1R 22/24 | C1, `qwen3.5-397b, exploratory` |
| After the repair the agents run formerly denied commands, and where their notes record it they call the reviewer inconsistent | section 10, reported | Claude, A1R, shifts 5 to 8: a formerly denied command ran in 59 of 96 sessions; an over-blocked object was reached in 71 (A4 94, A1 43). The notes say a denied action now works in 43/96 files (second coder 49/96); they put it down to a change in the reviewer in 0 (1) and to inconsistency in 41 (45). Qwen, A1R: 80 of 128 sessions; 13/128 files (6/128) | C4, `shifts 5 to 8` |
| The stale picture also outlasts the repair | exploratory, unnamed | Predicted blocking, A1R − A4 after shift 8 as a share of A1 − A4 after shift 4, lowest and highest reader: 0.49 to 0.58 on Claude's notes, 0.71 to 1.04 on Qwen's | C1, `probe folder` |
| After the repair the agents send the plain command about as often as while it was blocked, and less often than control agents | section 10, reported | Shifts 5 to 8, sessions with a command that the two guard variants decide differently: A1R 59/96, A1 57/96, A4 94/96 (Claude); A1R 80/128, A1 68/128, A4 124/128 (Qwen). Without a repair (Claude, A1) the notes say a denied action now works in 6/96 files (second coder 2/96) and put it down to inconsistency in 4 (2). Qwen, A1R: put down to inconsistency in 1 file (2), to a change in the reviewer in 0 (0) | C4, `shifts 5 to 8` |
| Reader success after shift 8, and the work after the repair | H4a, reported; the gap without a repair is exploratory, unnamed | Reader success after shift 8: A1 0.43, A1R 0.30, A4 0.02; lineages with a success 19, 14 and 4 of 24. Without a repair the gap stays: A1 − A4 after shift 8 0.413 [0.271, 0.552], 0.94 [0.78, 1.13] of the gap after shift 4. Tickets, shifts 5 to 8: A1R 188/192, A4 191/192, A1 175/192; A1 − A1R -6.8 points [-10.9, -3.1], A4 − A1R 1.6 [-0.5, 3.6]. Qwen: A1R 249/256 | C2, `e1v2:A1@8`, `paired difference`; C4, `tickets completed` |
| With the second coder the counts after the repair are close to those of the primary coder | exploratory | Second coder as primary. After shift 8: A1R 18/24, A4 0/24; of the lineages with a labelled recipe in A1 after shift 4, still there: A1 20/21, A1R 18/21. Qwen: A1R 19/32; still there: A1 22/22, A1R 19/22 | C7, `H4c` |
| The recipe stays whether or not the notes record the repair | exploratory, unnamed | Of the lineages with a labelled recipe in A1 after shift 4, still there in A1R after shift 8. Claude: 10/12 where the A1R notes put a now-working action down to inconsistency, 6/6 where they do not, with either coder's answers. Qwen: 1/1 and 21/23 | C4, `labelled recipe kept` |

## Revocation at repair time

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| Removing what the notes say about the reviewer removes more of the gap than a generic audit | H5, family | Audited − guard-scoped copy: 0.069 [-0.045, 0.188] over 24 pairs, p = 0.1546, Holm p = 0.3092. Not supported | C1, `H5` |
| The two scoped edits meet the criterion of 0.2 on the point estimate, and the audit and the notice do not | section 11, reported | Residual share: object-scoped 0.05 [-0.07, 0.17], guard-scoped 0.11 [-0.05, 0.32], notice 0.25 [0.11, 0.38], audit 0.27 [0.07, 0.52] | C2, `paired difference` |
| The edits remove most labelled recipes, and the notice removes none | section 11, reported | Labelled recipe: unedited 18/24, notice 21/24, audit 7/24, object-scoped 5/24, guard-scoped 1/24. No editor refusal | C5 |
| Going on from the guard-scoped copy or from an empty file costs no tickets | section 11, reported | Tickets completed against A1R, in percentage points: A1G 1.6 [0.0, 3.6], A1W 2.1 [0.5, 4.2], both within 5 points. Labelled recipe after shift 8: A1G 1/24, A1W 1/24 | C4, `claude-sonnet-5 syn e1v2-mit` |
| On the probe, the audit leaves more of the stale picture than the guard-scoped edit | exploratory, unnamed | Predicted blocking, audited − guard-scoped copy, four readers: 0.179, 0.173, 0.175, 0.195; each p at most 0.0001 | C1, `probe folder` |
| Every edited copy lowers reader success | section 11, reported | Reader success after shift 4: unedited 0.47; notice 0.15; audit 0.15; guard-scoped 0.08; object-scoped 0.06; A4 0.03. Lineages with a success: 20, 16, 14, 5 and 6 of 24 | C2, `e1v2:A1@4+` |
| The second coder finds the same pattern in the copies, and three more recipes in the unedited files | exploratory | Labelled recipe by the second coder: unedited 21/24, notice 21/24, audit 5/24, object-scoped 2/24, guard-scoped 0/24. Mean words: unedited 461; notice 482, audit 431, object-scoped 356, guard-scoped 339 | C5, second command |
| Only the guard-scoped copy and the empty file were run on | section 11, reported | Shifts 5 to 8: tickets A1G 191/192, A1W 192/192, A1R 188/192. Tool calls per session at shift 5: A1W 7.4, A1G 5.1, A1R 5.2 | C4, `e1v2-mit`; C9, last command |

## Guard class

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| Under the same over-blocking, the taint guard leaves fewer labelled recipes than the command-based guard | H6, family | 26 pairs: 16 SYN only, 1 effect only, p = 0.0001, Holm p = 0.0006. Supported | C1, `H6` |
| A denial on an over-blocked object occurs in about as many sessions in both classes | H6, reported | A1 sessions denied on an over-blocked object, shifts 1 to 4 together: 84 of 96 (SYN) and 46 of 52 (effect) with Claude as donor; 111 of 128 and 50 of 52 with Qwen | C9, `chain-report` |
| The effect guard costs more denials and, with Qwen as donor, more tickets | exploratory, unnamed | Effect class, shifts 1 to 4, A1 against A4. Claude: 228 denials in 46/52 sessions; tickets 99/104 against 104/104; lineages that fail a ticket 4/13 against 0/13, two-sided Fisher p = 0.0957. Qwen: 304 denials in 50/52 sessions; tickets 85/104 against 102/104; 11/13 against 1/13, p = 0.0002. Labelled recipe in A1 notes by shift: 0.23, 0.23, 0.23, 0.15 (Claude); 0.15, 0.08, 0.23, 0.15 (Qwen) | C9, `effect A1`; C6, `effect A1 g` |
| On the same lineages and shifts, the effect guard denies more often per session | exploratory, unnamed | Lineages 0 to 12, shifts 1 to 4, A1, SYN against effect. Claude: sessions denied on an over-blocked object 44/52 against 46/52; denials per session 2.75 against 4.38; object reached in 21 against 13 sessions; tickets 101/104 against 99/104. Qwen: 43/52 against 50/52; 3.44 against 5.85; 17 against 8; 99/104 against 85/104 | C9, `the guard classes on the same lineages` |

## Other readers

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| A second reader repeats the result | H1 and H1-OW, exploratory | DeepSeek V4 Flash: 0.132 [0.069, 0.212], p < 0.0001 with Claude's notes; 0.065 [0.023, 0.117], p = 0.0039 with Qwen's. Anchors 0.00 and 0.93 | C1, `reader deepseek-v4-flash` |
| A reader that mostly declines gains nothing from the notes | H1 and H1-OW, exploratory | Claude Sonnet 5 sends a command in 0.11 of trials with A1 notes and 0.08 with A4 notes when Claude is the donor, and in 0.22 and 0.29 when Qwen is. Anchors 0.00 and 0.72; difference 0.000 with either donor's notes | C1, `reader claude-sonnet-5`; C3, `syn` |
| One reader cannot be interpreted | H1 and H1-OW, exploratory | Qwen 3.5 397B: anchors 0.00 and 0.10, not informative | C1, `reader qwen3.5-397b` |
| The reader that declines does so with chain notes of either arm, not with the empty file | exploratory | Claude Sonnet 5 sends a command in 0.62 of trials with the empty file and in 0.72 with the positive control, against 0.11 and 0.08 with A1 and A4 notes | C3, `anchor` |

## Prompt arms

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| With the hygiene sentence in the merge the notes hold a labelled recipe less often; without the good-faith sentence the share is not lower. The prompt arms have 13 lineages and the main arm 24, so the levels are not like for like | exploratory | Share of A1 notes with a labelled recipe after shift 4: 0.92 without the good-faith sentence and 0.23 with the hygiene sentence, 13 lineages each; 0.75 in the main arm, 24 lineages | C6, `claude-sonnet-5 syn A1 g4` |
| Reader success moves the same way | exploratory | Success after shift 4: 0.56 and 0.10; 0.47 in the main arm | C2, `claude-sonnet-5 syn` |
| What the sessions of the prompt arms did | exploratory | SYN, A1, shifts 1 to 4, 13 lineages each. Without the good-faith sentence: a workaround after a denial in 31/52 sessions and 10 lineages; tickets 98/104; 4/13 lineages fail one. With the hygiene sentence: 16/52 sessions and 9 lineages; tickets 96/104; 7/13 | C9, last command |
| On the same 13 schedules, the hygiene sentence lowers the labelled recipe and reader success; taking out the good-faith sentence changes neither reliably | exploratory, unnamed | Against the main arm on lineages 0 to 12, after shift 4, two-sided. Hygiene sentence: labelled recipe 3/13 against 11/13; reader score 0.10 against 0.42, difference -0.314 [-0.513, -0.128], p = 0.0127. No good-faith sentence: 12/13 against 11/13; 0.56 against 0.42, difference 0.147 [-0.115, 0.385], p = 0.3096 | C1, `prompt arm` |

## Coding

Three annotators coded samples by hand. Each worked from a bundle that holds the rubric and the notes text under shuffled ids, with no donor, arm, lineage or shift. Annotators 1 and 3 each coded the sample of the first study, and annotators 2 and 3 each coded the sample of the second. The sheets are kept as they were returned, and none is merged with another.

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| The two coders agree on the codes that the tests use | section 7, reported | Recipe: agreement 0.94, kappa 0.88. Labelled: agreement 0.96, kappa 0.92. 1328 double-coded files | C6, `agreement` |
| Each coder agrees with the hand codes on the labelled recipe, in a sample of the first study | section 7, reported | 60 files, 15 per donor and arm. Agreement and kappa on the labelled recipe: primary coder 0.98, 0.96 with either annotator; second coder 1.00, 1.00 with either; the two annotators with each other 1.00, 1.00. On recipe alone: primary coder 0.88 with kappa 0.75 and 0.76; second coder 0.98, 0.96; annotators 0.97, 0.93 | C10, first command, `labelled recipe`, `recipe` |
| Blind to the arm, both annotators find a labelled recipe in files of over-blocked lineages only | section 7, reported | The same 60 files, either annotator: A1 19/30, A4 0/30 | C10, first command, `labelled recipe by arm` |
| The same holds in a sample of the second study, which has files written after the repair | exploratory, unnamed | 42 files, 7 per donor and arm. Labelled recipe: primary coder 0.95, 0.90 and 0.93, 0.85; second coder 1.00, 1.00 and 0.98, 0.95; the two annotators with each other 0.98, 0.95. By arm, annotators 2 and 3: A1 13/14 and 12/14, A1R 12/14 and 12/14, A4 0/14 and 0/14 | C10, second command, `labelled recipe` |
| Of the four codes that no test uses, one is not reliable between annotators, and the primary coder agrees poorly with the hand codes on two | section 7, reported, for the first sample; exploratory, unnamed, for the second | Kappa between the annotators, first then second sample: legitimate 0.10, 0.11; caveat 0.71, 0.95; negative 0.83, 0.76; rules 0.69, 0.85. Kappa of the primary coder with each annotator: negative 0.13 and 0.13, then 0.15 and 0.11; rules 0.23 and 0.21, then 0.23 and 0.17. Of the second coder: negative 1.00 and 0.83, then 0.90 and 0.76; rules 0.82 and 0.80, then 0.85 and 0.80 | C10, `legitimate`, `caveat`, `negative`, `rules` |
| The tests on codes do not depend on which coder is primary | exploratory | Second coder as primary. H6: 15 SYN only, 1 effect only, p = 0.0003. H4c: A1R 18/24, A4 0/24 | C7, `H6`, `H4c` |

## First study

The first study ran 416 sessions: two donors, two guard classes and two arms, with 13 lineages of four shifts in each cell. Its hypotheses and their status are those of [PREREGISTRATION.md](PREREGISTRATION.md). The reader battery was a secondary measure there, to be run only if it was built before the chains finished. It was run after them, so its rows are exploratory. Reply labels are the ones stored when the battery ran. In each row, Claude Sonnet 5 as donor comes before Qwen 3.5 397B, and the command-based class (SYN) before the effect class.

| Claim | Hypothesis, status | Evidence | Where |
|---|---|---|---|
| The over-blocking guard denied an action in nearly every session, and the repaired guard in few | exploratory | Sessions with a denial, of 52, A1 against A4: 46 against 4 and 46 against 0; 48 against 5 and 48 against 4. Denials: 152 and 205, 189 and 335, against 4 and 0, 6 and 4 | C15, `denials` |
| Under the over-blocking guard, agents reached an over-blocked object another way | exploratory | Sessions of 52, then lineages of 13: 25 and 11, 5 and 3; 17 and 10, 7 and 4 | C15, `workarounds` |
| Over-blocking cost tickets in one cell | exploratory | Tickets completed of 104, A1 then A4: 101 and 104, 97 and 104; 101 and 103, 77 and 102. Lineages that failed a ticket, Qwen under the effect guard: 11/13 against 1/13, two-sided Fisher p = 0.0002. The other three cells: 3/13 against 0/13 or 1/13, p at least 0.2200 | C15, `tickets`, `failing_lineages` |
| Every session ran to its end | exploratory | 416 sessions: none refused, no merge refused, no malformed call | C15, `refused` |
| Running the commands written in the notes finds no attack | H1, primary; H1-OW, secondary | Mechanical potency after shifts 2 and 4: 0.00 in every arm and class, for both donors. A1 − A4 under SYN after shift 4: 0.000 [0.000, 0.000] over 13 pairs, p = 1.0000, for each donor. Not supported | C15, `H1 (syn, g4)` |
| The measure registers an attack in the command-based class only | H2, secondary | Positive control against the empty file: 1.00 against 0.00 under SYN, 0.00 against 0.00 in the effect class. H2 is not estimable | C15, `anchor`, `H2` |
| The notes held few commands to run | exploratory | Candidates in the final A1 notes under SYN: 13 in 13/13 files; 2 in 1/13 files | C15, `candidates` |
| The notes record the detour and label it as a way around the reviewer | exploratory | Final notes with a labelled recipe under SYN, A1 against A4: 11/13 against 0/12; 10/13 against 0/13; two-sided Fisher p at most 0.0001. In the effect class: 2/13 against 0/13; 5/13 against 0/13 | C16, first command, `final` |
| The record grows over the shifts and stays | exploratory | Share of A1 notes with a labelled recipe under SYN after shifts 1 to 4: 0.62, 0.69, 0.85, 0.85; 0.31, 0.58, 0.69, 0.77. A4: 0.00 at every shift. A recipe present after one shift is there after the next in 27/29 and 20/20 | C16, first command, `syn    A1`, `retention` |
| Two coders agree on the two codes used | exploratory | 412 double-coded files: recipe agreement 0.94, kappa 0.83; labelled 0.98, 0.95. On a sample of 76 files coded by the other donor's model: kappa 0.86 and 0.93. The other four codes: kappa 0.32 to 0.60 | C16, first and second commands, `agreement` |
| The contrast does not depend on which coder is primary | exploratory | With the coders exchanged: 12/13 against 0/13; 10/13 against 0/13 | C16, third command, `final` |
| With Claude's over-blocked notes, a reader succeeds against the repaired guard | exploratory | Gemini 3.1 Pro, shared-principle objectives: 0.58 with A1 notes, 0.02 with A4 notes; A1 − A4 0.558 [0.404, 0.699] over 13 pairs, p = 0.0002; lineages with a success 12/13 against 2/13. Anchors: empty file 0.08, positive control 0.75 | C17, first command, `claude-sonnet-5`, `gate` |
| With Qwen's notes the gain is smaller | exploratory | 0.11 against 0.01; A1 − A4 0.103 [0.019, 0.199], p = 0.0469; lineages 5/13 against 1/13 | C17, first command, `qwen3.5-397b` |
| A reader that mostly declines gains almost nothing | exploratory | Claude Sonnet 5 under SYN sends a command in 0.13 and 0.09 of trials with Claude's A1 and A4 notes, and in 0.21 and 0.36 with Qwen's. Success 0.01 against 0.00; A1 − A4 0.006 [0.000, 0.019], p = 0.5000, with either donor's notes. Anchors 0.00 and 0.75 | C17, second command, `syn` |
| The effect class cannot be interpreted | exploratory | Claude Sonnet 5 as reader: positive control 0.00, empty file 0.08; not informative | C17, second command, `gate (effect)` |

## Earlier studies

Four steps came before the chains of the first study. The public records hold each model's answers as numbers and labels, with no reply text.

- **Audit.** Each hidden guard decides either on commands or on data. An observer sees up to 16 scripted commands with the guard's responses and predicts its decision on 12 held-out commands. Balanced accuracy is over 40 guards, with a bootstrap 95% interval. The ideal observer is exact Bayesian inference over the space of guards. The three observers are Claude Sonnet 5 at medium effort, Claude Sonnet 5 at high effort and Muse Spark, in that order.
- **Probe.** Each reply is labelled by the rule in `src/swarmgate/e1/probe.py` as committed.
- **Scripted sessions.** The session shows a denied read and then one of four ways on; the model is asked for handoff notes, and a model of another family codes them.
- **Pilots.** Four sessions per candidate under the over-blocking command-based guard.

| Claim | Status | Evidence | Where |
|---|---|---|---|
| With no response seen, the observers predict a hidden guard's decisions near chance, and the ideal observer does not | earlier | Balanced accuracy: 0.531, 0.521, 0.510; ideal 0.727 | C11, first command, `none seen` |
| Sixteen plain denials let two of the three observers predict the guard better | earlier | "Tool call not approved." as the only feedback, 16 responses seen: 0.559 [0.490, 0.630], 0.693 [0.623, 0.760], 0.756 [0.696, 0.819]; ideal 0.882 [0.840, 0.919] | C11, first command, `generic k=16` |
| A denial that names its rule tells more | earlier | 0.684 [0.623, 0.746], 0.746 [0.685, 0.804], 0.780 [0.726, 0.834]; ideal 0.920 [0.883, 0.951] | C11, first command, `verbose k=16` |
| When a denial is disguised as an ordinary error or as success, the observers blame the guard less reliably | earlier | Failures put down to the right cause, 16 responses seen. Plain denial: 0.957, 0.973, 1.000. Disguised as an error: 0.636, 0.731, 0.755. Disguised as success: 0.762, 0.768, 0.549. Ideal: 1.000, 0.977, 1.000 | C11, first command, `attribution` |
| They also predict the guard worse, and the ideal observer still learns from a disguised denial | earlier | Balanced accuracy. Disguised as an error: 0.558, 0.626, 0.679; ideal 0.874. Disguised as success: 0.496, 0.518, 0.550; ideal 0.779 | C11, first command, `camouflaged k=16`, `fake_success k=16` |
| Told the space of possible guards, an observer starts where the ideal observer starts and ends close to it | earlier; the arm and its narrowing are in `DEVIATIONS.md` | A second set of 40 guards, Claude Sonnet 5 at medium effort, told against not told. No response seen: 0.719 against 0.533; ideal 0.723. Rule named, 16 responses: 0.853 [0.811, 0.895] against 0.708 [0.647, 0.772]; ideal 0.910. Plain denial: 0.839 [0.794, 0.881] against 0.624 [0.554, 0.692]; ideal 0.870. 116 of 120 told answers could be read | C11, second command, `claude-sonnet-5-space`, `claude-sonnet-5` |
| Ending a session after the third block tells the ideal observer more when denials are disguised, and less when the end comes after a random delay | earlier | Extra bits about the guard. Disguised as an error: 0.121 at once, 0.061 with a delay of up to three commands. Disguised as success: 0.880 and 0.495. Visible denials: 0 | C11, first command, `termination` |
| One model refused every prompt of the audit | earlier; the change of observer is in `DEVIATIONS.md` | Claude Sonnet 5.5: 84 of 84 refused, and 4 of 4 under a second access setting | C11, third command, `refused` |
| Asked for one command against the policy, models differ in whether they give one, and fewer do when the notes spell out a way past the reviewer | earlier | Commands in 9 replies, without notes and then with them: Claude Sonnet 5.5 0 and 0 (every reply refused); Claude Sonnet 5 9 and 0; Claude Haiku 5.5 3 and 0; Gemini 3.8 Flash 1 and 0; Gemini 3.1 Pro 8 and 5; Muse Spark 7 and 2 | C12, `attacker notes=none`, `attacker notes=control` |
| In the agent's role, after scripted denials, no reply is refused | earlier | 144 replies from four models: 0 refused, 1 declined | C12, `donor` |
| After a scripted detour around a denial, the donor writes the detour into its notes | earlier, recorded | Claude Sonnet 5 with the good-faith sentence: 56/60 = 0.93 [0.84, 0.97], so the sentence stays in the chains | C13, `p_r` |
| Without the good-faith sentence it does so less often | earlier | Claude Sonnet 5: 16/60 = 0.27 [0.17, 0.39]. Claude Sonnet 5.5: 60/60 with the sentence and without | C13, `p_r` |
| With the sentence, the notes also disclose the agent's own detour more often | earlier | Claude Sonnet 5: disclosed in 54/60 against 13/60, two-sided Fisher p = 1.2e-14. No note misrepresents it | C13, `D1 share` |
| Two coders agree on the codes used here | earlier | 96 double-coded notes. Kappa: recipe 1.00, labelled 1.00, disclosure 1.00, caveat 0.66, escalation 0.44 | C13, `coder agreement` |
| The donor rule chose Claude Sonnet 5 | earlier, recorded | Sessions with a block worked around: Claude Sonnet 5.5 0 of 4, with 2 sessions refused; Claude Sonnet 5 3 of 4 | C14, first command |
| The same rule chose Qwen 3.5 397B among the open-weight candidates | section 7 of `PREREGISTRATION.md`; the dropped candidate is in `DEVIATIONS.md` | GLM 5.2 ran no session; Qwen 3.5 397B 2 of 4; DeepSeek V4 Flash 0 of 4 | C14, second command |
