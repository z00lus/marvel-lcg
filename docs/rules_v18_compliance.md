# Rules Reference 1.8 solo compliance

Status: implementation complete for the fork's supported one-hero solo scope.

Rules Reference 1.8 is the only runtime rules model. New Quick Game,
Campaign, and Advanced Setup sessions record `v18_all`. Historical v1.6/v1.7
execution flags and branches are not present in `WorldRule`; legacy rule names
are recognized only by new-game request sanitization. A replay or save without
`v18_all` is rejected before world initialization with a clear compatibility
error.

## Evidence matrix

| Rules area | Implementation evidence | Automated evidence | Status |
|---|---|---|---|
| Choice, Otherwise, and for-each | `game/effect/effect_checker.py`, `game/event/manager.py`, `game/player/action/player_action.py` | `test_v17_choice_rules.py` | Complete |
| Ownership, control, and permanent cards | `game/card/card.py`, inventory/permanent components, player elimination cleanup | `test_v17_ownership_control.py` | Complete for solo; cross-player elimination is out of scope |
| Referential abilities | `game/operate/referential.py`, direct `Worlds` lookup | `test_v17_referential_abilities.py` | Complete |
| Uniqueness | `face_name.py`, player setup, encounter reveal replacement | `test_v17_uniqueness.py` | Complete |
| Actions, activations, and costs | effect initiation/payment and activation deferral | `test_v17_actions_activations_costs.py` | Complete |
| Counters, modifiers, and card state | counter movement, dynamic modifiers, cleanup, ready rules | `test_v17_counters_modifiers_card_state.py` | Complete |
| Attacks and villain transitions | attack pipeline and stage continuity | `test_v17_attacks_villain_transitions.py` | Complete |
| Setup and identity attribution | player setup and resource-card identity routing | `test_v17_setup_you.py` | Complete for solo |
| Timing priority | `TimingPriority` and event scheduling | `test_v18_timing_priority.py`, `test_v18_defined_terms_timing.py` | Complete |
| Surge queue | deferred encounter queue | `test_v18_surge_queue.py` | Complete |
| Reveal lifecycle and Quickstrike | nested reveal-response scheduling | `test_v18_reveal_lifecycle.py` | Complete |
| Overkill | defeat-first excess-damage sequence | `test_v18_overkill.py` | Complete |
| Calculate Damage | explicit enemy-attack calculation message | `test_v18_calculate_damage.py` | Complete |
| Ability/card initiation | table-before-restriction/cost sequence with rollback | `test_v18_ability_initiation.py` | Complete |
| Referential target legality | independent and dependent instruction targeting | `test_v18_referential_targeting.py` | Complete |
| Swaps | orientation, same-title state transfer, lifecycle, atomic failure | `test_v18_swaps.py` | Complete |
| Remaining engine clarifications | duplicate targets, deck reset, removed cards, PSS limit, printed star | `test_v18_misc_rules.py` | Complete |
| FAQ and card errata | affected card scripts plus `data/cards.json` | `test_v18_card_errata.py`, Wonder Man and Hercules focused suites | Complete for content present in the fork |
| Setup UI | solo, campaign, advanced payloads and server normalization | `test_v18_setup_ui.py`, `test_v18_replay_policy.py` | Complete |
| Replay serialization | scene checksum/load and controller input stream | `test_v18_synthetic_replay.py` and its repository fixture | Complete at the deterministic serialization layer |

The detailed v1.6-to-v1.7 source audit remains in
`tasks/01-v17-gap-audit-matrix.md`; the row-by-row card audit remains in
`tasks/13-card-errata-audit.md`. Those working files are intentionally ignored
by Git, while this final summary is repository documentation.

## Explicit exclusions and evidence limits

- Multiplayer-only ordering, cross-player elimination handoff, PvP, and broad
  four-player interactions are outside this fork's supported scope.
- Organized-play Game Environment deck-construction restrictions are not
  enforced. The starter-deck workflow uses the unrestricted Legacy model.
- The Moon Knight erratum whose card is absent from this fork is documented as
  content absent rather than partially implemented.
- Personal replays and the original project's external replay corpus are not
  repository fixtures and are not claimed as passing evidence.
- The committed synthetic replay proves deterministic scene parsing, checksum
  validation, compatibility policy, and complete controller-stream playback.
  Focused system tests provide the semantic evidence for individual rules.
- A fresh browser-driven Rhino/Klaw and Campaign-continuation smoke session was
  not automated as part of this audit. Existing manual solo play found earlier
  card-specific issues, which were fixed separately; this limitation is about
  evidence breadth, not a known remaining rules deviation.

Within the audited solo scope, there is no known Rules Reference 1.8 deviation.
Future card integrations still require their own metadata, script, and focused
semantic validation.

## Targeted validation

Run the explicit rules suites only; never use unrestricted unittest discovery:

```bash
.venv/bin/python -m unittest \
  unit_test.test_world_rule \
  unit_test.test_v17_choice_rules \
  unit_test.test_v17_ownership_control \
  unit_test.test_v17_referential_abilities \
  unit_test.test_v17_uniqueness \
  unit_test.test_v17_actions_activations_costs \
  unit_test.test_v17_counters_modifiers_card_state \
  unit_test.test_v17_attacks_villain_transitions \
  unit_test.test_v17_setup_you \
  unit_test.test_v18_timing_priority \
  unit_test.test_v18_defined_terms_timing \
  unit_test.test_v18_surge_queue \
  unit_test.test_v18_reveal_lifecycle \
  unit_test.test_v18_overkill \
  unit_test.test_v18_calculate_damage \
  unit_test.test_v18_ability_initiation \
  unit_test.test_v18_referential_targeting \
  unit_test.test_v18_swaps \
  unit_test.test_v18_misc_rules \
  unit_test.test_v18_card_errata \
  unit_test.test_v18_setup_ui \
  unit_test.test_v18_replay_policy \
  unit_test.test_v18_synthetic_replay
```

Also run Python compilation, the TypeScript build, card-module imports, and
JSON checksum verification described in `AGENTS.md`.
