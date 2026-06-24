# S4 Live Evidence
Status: Complete with live evidence. Captured 2026-06-22. Live: gpt-4o-mini, gpt-5.5, fugu, fugu-ultra. No mocks. Machine-readable: source/headtohead_results.json. Adversarially reviewed (Opus): all numbers reproduce; claim safe with caveats.

15 identical tasks, all systems, same graders + cost method:
  gpt-4o-mini  acc=0.733  $0.00003/task
  gpt-5.5      acc=1.000  $0.00191/task   (22.3x cheaper than fugu-ultra)
  fugu(mini)   acc=1.000  $0.01497/task
  fugu-ultra   acc=1.000  $0.04261/task   20.2s/task
  heuristic-router  acc=1.000  $0.00135/task  (31.7x cheaper than fugu-ultra)
  classifier-router acc=1.000  $0.00145/task  (29.4x cheaper than fugu-ultra)

Falsification: 0/15 Fugu-cheaper-than-gpt5.5; 0/15 Fugu-beats-gpt5.5; routers match 1.000 (no accuracy traded). Fugu billed at its real $5/$30 rate; even visible-tokens-only it's 3.7x a gpt-5.5 call.
Honest claim: router matches Fugu-Ultra accuracy at ~30x lower cost / ~10x lower latency on solvable tasks; "cheaper at matched accuracy," NOT "better" (all tasks within frontier capability; n=15).
