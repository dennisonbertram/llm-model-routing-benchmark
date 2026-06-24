# Surprises (live)
1. Our routers matched Fugu-Ultra's accuracy (15/15) at ~30x lower cost AND ~10x lower latency — and never traded accuracy for cost (every routed choice was correct).
2. ~95% of the "30x" is NOT router cleverness — a single gpt-5.5 call is already ~22x cheaper than fugu-ultra at the same 15/15. The router adds only ~1.3-1.4x on top. The real finding: Fugu's orchestration didn't earn its cost on solvable tasks.
3. Fugu's cost is fair-billed: even counting ONLY its visible answer tokens (stripping ~83% orchestration overhead), fugu-ultra is still 3.7x a single gpt-5.5 call.
4. Falsification clean: 0/15 tasks where Fugu was cheaper than gpt-5.5; 0/15 where Fugu beat gpt-5.5 on accuracy. Nothing beat a single frontier call — these tasks are within frontier capability, so the honest claim is "cheaper at matched accuracy," not "better."
5. Per-task cost ratios are wildly skewed (max 15,489x on a trivial QA item) — quote the aggregate ~30x, never the max.
