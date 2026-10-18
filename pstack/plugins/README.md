# pstack plugins for DeepSeek Harness

`pstack-extras.patch.yml` carries three rows:

- `tomato-reminder` — re-states the mode reminder at the start of each turn.
- `preset-tomato-agent` — a delegand that starts already knowing it is a pstack delegate.
- `preset-standard-override` — the shipped standard preset plus the allowlist that lets `subagent` name a preset.

## tomato-reminder

A skill body enters context once, on the turn it is invoked. In a long conversation the routing rule fades and the model stops treating a later request as work the mode should route. Cursor answers this with a Custom Mode that re-sends the whole skill every turn; that costs the full body on every request and, being ordinary history, is the first thing a compaction pass drops.

This plugin sends one line instead, only while the mode is on, and replaces it rather than stacking a new one each turn:

| Moment | What happens |
|---|---|
| Prompt carries `/tomato-mode` | Mode turns on |
| Prompt carries `/tomato-off` | Mode turns off and the line is cleared |
| First step of a turn, mode on | The line is admitted to the surface |
| Later steps of the same turn | Nothing added |
| Next turn | The line is replaced, not appended |

Detection reads the user messages the loop already claimed for the turn, so the state follows what the operator typed. The line carries the absolute path to `SKILL.md`, so a conversation whose body was compacted away can still recover it.

`pre-step` runs once per step, and a turn can hold many steps. The `step === 1` guard is what keeps this to one line per turn rather than one per tool call.

## Presets

`standard` is re-declared with `allowedAgentPresets: [standard, tomato-agent]`. That allowlist is what turns `agent_preset` into a model-visible enum on the `subagent` tool; without it the tool refuses a preset choice. `tomato-agent` carries the same rows as `standard` and differs only in its persona, so a child starts knowing it is a pstack delegate.

`comment-sicko` has no preset yet. A skill that wants it inlines `../../agents/comment-sicko.md` into the brief until it does.

## Install

```bash
# 1. Link the generated tree where DSH looks first.
ln -sfn ~/.agents/pstack/generated/deepseek/skills ~/.dsh/skills

# 2. Apply the patch rows.
cat ~/.agents/pstack/plugins/pstack-extras.patch.yml \
  >> ~/.dsh/profiles/desktop/cordis.patch.yml

# 3. Restart DSH.
```

Step 2 appends rows; it does not merge. Running it twice duplicates them, so check the profile first.

## Verify

The plugin has no dependencies on the DSH packages, so it loads outside the host:

```bash
node --input-type=module -e "
import('/Users/xiongzhipeng/.agents/pstack/plugins/tomato-reminder/index.js')
  .then(m => console.log(m.name, typeof m.apply));
"
```

Then start a session, run `/tomato-mode`, and confirm the reminder appears once per turn and that the surface holds a single copy after several turns.

## Model windows

A model's `contextWindow` sets when DSH condenses a conversation. The trigger is `min(W × 0.8, W − maxTokens − 65536)`; the shipped `headroomTokens` is 65,536. Every route here uses `maxTokens: 32768`:

| Model | contextWindow | Trigger | Share |
|---|---|---|---|
| DeepSeek V4.1 Flash Fast | 448000 | 349,696 | 78% |
| DeepSeek V4.1 Flash | 448000 | 349,696 | 78% |
| GLM 5.3 Flash | 448000 | 349,696 | 78% |
| GPT Luna 6.0 | 448000 | 349,696 | 78% |
| Claude Haiku 5.5 | 200000 | 101,696 | 51% |

The 448,000 windows match DeepSeek's real capacity, so the same conversation keeps the same trigger point after switching routes. A window set above what the provider serves does not delay condensation; the provider rejects the request before the trigger fires.

The Haiku window is 200,000 because its target trigger is about 100,000: `200000 − 32768 − 65536 = 101696`, which is below `200000 × 0.8 = 160000`. Its 51% share is lower than the others because the fixed 65,536 headroom is a larger fraction of a smaller window.
