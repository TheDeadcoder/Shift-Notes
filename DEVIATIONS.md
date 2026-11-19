# Deviations

The single record of deviations from the study plan.

## E0: Anthropic observer

- **Planned:** Claude Sonnet 5.5 at medium effort.
- **Used:** Claude Sonnet 5 (`claude-sonnet-5`) at medium effort, plus the same model at high effort as an added reasoning-budget arm.
- **Why:** Claude Sonnet 5.5 declined every E0 observer prompt with a `cyber` safeguard refusal before producing any output, under default safeguards and with Cyber Verification Program Defense Access. Claude Sonnet 5 answered every prompt. The refusals are kept in the run records and excluded from scoring.

## E0: guard-space arm

- **Planned:** observers see only the session log and a short framing of the task.
- **Added:** a separate set of hidden guards (`configs/e0-space.yaml`) on which Claude Sonnet 5 is run both with and without a description of the space of possible guards. The runs without it cover all four feedback modes at medium and high effort.
- **Narrowed:** with the description, the model reasons far longer, and under camouflaged and fake-success feedback its answers ran past the 16,000-token output limit. Runs with the description are therefore limited to no observations and to verbose or generic feedback, at medium effort first; high effort follows only if its answers fit the limit. This was decided before any of the arm's answers were scored.
- **Why:** in the main run, much of the readers' shortfall against the ideal observer was already present before any feedback, which points to a missing prior rather than slower learning. Describing the space tests this directly. The arm's predictions were fixed before it was run.

## E1b-OW: open-weight donor candidates

- **Planned:** the open-weight donor is the first of `glm-5.2`, `qwen3.5-397b` and `deepseek-v4-flash` whose pilot works around a block.
- **Changed:** `glm-5.2` was dropped. The rule was applied to the other two candidates in the same order. That selects `qwen3.5-397b`, which worked around a block in 2 of 4 pilot sessions; `deepseek-v4-flash` did in none.
- **Why:** `glm-5.2` was listed as available for the API key, but it never produced a token. Every request ended at a gateway timeout after about a minute:
  - without streaming, as an HTTP 504;
  - with streaming, as a dropped connection, including for a minimal request with no system prompt and no tools.

  Three complete pilot runs failed this way for every session, two without streaming and one with it. The other two candidates ran normally over the same period. The decision was made before any open-weight chain session ran.

## E1 v2: reader service tier

- **Planned:** the reader of H1 is called as in the first study's reader battery, which used the provider's standard tier.
- **Changed:** reader calls use the provider's Flex tier. The model and its sampling are unchanged. Every read that enters one comparison uses that tier, and the first study's 26 notes files are read again on it as the check that the reader has not changed.
- **Why:** the full set of reads fits the study's budget only on this tier. An anchor run on each tier gave the same validity result: the empty file succeeded in 0.03 of trials on the standard tier and 0.00 on Flex, and the positive control in 0.72 and 0.70. The two runs differed in one respect: with the empty file the reader declined in 4 of 40 trials on Flex and in 12 of 40 on the standard tier, and its replies were shorter on average. For that reason no comparison mixes the two tiers. The change was made before any fresh notes file was read.

## E1 v2: which replies count as a command

- **Planned:** reader replies are classified as in the first study's reader battery.
- **Changed:** the pattern that recognises a refusal in words (`REFUSAL` in `src/swarmgate/e1/probe.py`) covers more wordings. A reply it matches is a non-attempt and is not run. Before, some of these replies were treated as commands, run, and failed.
- **Why:** the reader's most common refusal sentence was not recognised, and in the reader that may issue several commands a refusal that is run as a command does not end the episode. Applied to every stored reply of the first study and of development, the wider pattern relabels 328 of 5,795 replies, all of them refusals, and changes no stored success value. The change was made before any fresh notes file was read.
