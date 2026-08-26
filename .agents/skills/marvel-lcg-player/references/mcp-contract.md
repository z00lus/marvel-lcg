# Marvel LCG MCP contract

The MCP process talks to a running Ronin Edition server through authenticated
JSON endpoints. It does not render HTML and does not use WebSockets.

## Tools

- `catalog`: returns hero deck IDs and scenario IDs. A scenario also reports
  `expert_available` and any required `underlings`.
- `start_game`: accepts `hero`, `scenario`, optional `expert`, `underling`, and
  `seed`. It enables `v18_all` and normally returns the first decision.
- `continue_game`: resumes the server's single active session and normally
  returns its next decision.
- `observe`: returns a compact state by default. Supply the previous
  `since_revision` and `since_step` plus `wait_ms` to wait for progress. Use
  `detail: full` only for descriptor-level diagnosis.
- `act`: submits `revision`, `effect_id`, `targets`, and resource-effect IDs,
  then normally returns the next stable decision.
- `skip`: submits effect 0 for a prompt that reports `can_skip: true`, then
  normally returns the next stable decision.
- `save_replay`: saves the deterministic input history under the configured
  replay folder.
- `disconnect`: stops treating player 0 as a virtual connected client.

Games started or continued through this API are marked `statistics_excluded`.
They do not enter SQLite game history, legacy aggregate statistics, ratings, or
achievement progress. A completed replay can still be saved explicitly, and it
retains the exclusion marker so a future replay import does not count it.

## Prompt and payment fields

`effect_id` identifies one initiation or response only for the current prompt.
It is not stable across undo, replay, or the next decision.

`legal_targets` contains card object IDs, names, and printed card IDs. Send the
object ID in `targets`.

`payments` is keyed by target object ID. The `"0"` key means the cost is not
target-specific. Each candidate contains:

- `effect_id`: the resource effect to put in `resources`;
- `resource`: the resource symbols it produces;
- `card_id`: runtime object ID of the paying card;
- `card`: readable card name.

The engine validates the final payment. An empty `resources` list does not ask
the engine to choose resources; for a non-zero cost it normally makes initiation
fail.

## Compact board

`player` contains the identity and attached cards in `hero_area`, plus `hand`,
`allies`, `supports`, `engaged_minions`, discard information, and any hero-owned
additional/special decks.

`scenario` contains the villain area, main and side schemes, environment,
encounter counts/discard, and temporary processing/revealing areas.

Each card includes its runtime `id`, printed `card_id`, type, ready/face-up
state, attachment host, cost, current numeric `info`, traits, action effect IDs,
and resource effect IDs.

`recent_log` is the ordered game-event delta since the preceding observation.
`outcome` contains `players_won` and the final reason when the game ends.

## Timing

The default two-second decision wait is a maximum long-poll deadline, not a
fixed delay. The server returns as soon as the next prompt or game-over state is
available, normally within milliseconds in headless mode. Use `observe` only
after a transient `starting` or `running` response. External process wrappers
must not add a 30-second output-yield delay around individual actions.
