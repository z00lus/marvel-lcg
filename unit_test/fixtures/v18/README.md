# Synthetic Rules Reference 1.8 replay fixtures

These fixtures contain no personal gameplay, card art, or downloaded data.
They test the serialized scene loader and controller replay stream; focused
rules tests remain the semantic evidence for individual v1.8 mechanics.

To regenerate `replay_loader_minimal.json` after editing it, recalculate its
checksum through the same serializer used by the game:

```bash
.venv/bin/python -c "from engine import Engine; from engine.lib import Json, Ver; Ver.Initialize(); data = Json.Load('unit_test/fixtures/v18/replay_loader_minimal.json'); Json.Save(data, 'unit_test/fixtures/v18/replay_loader_minimal.json', ignore_check_sum=False)"
```

Run the complete fixture explicitly with:

```bash
.venv/bin/python -m unittest unit_test.test_v18_synthetic_replay
```
