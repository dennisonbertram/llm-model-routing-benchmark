# Surprises (live)

1. **GPT-5.5 cleared the entire suite (100%)** — including m8, which neither the cheap model nor
   gpt-4.1 could solve. A stronger model genuinely raised the ceiling that the base degree treated
   as "1 unsolvable item."

2. **Newer is not strictly better per item.** gpt-5.4 FIXED m8 but BROKE m10 (a hard-math item
   gpt-4.1 solved), netting the same 0.978 accuracy at 1.8x the cost — strictly dominated by
   gpt-4.1 here. Version number is not a capability guarantee; measure on YOUR tasks.

3. **The frontier model is overkill almost everywhere.** Always-gpt-5.5 costs $0.11943 for the
   45 tasks; the realizable 3-tier router reaches the SAME 100% accuracy for $0.00405 by sending
   exactly ONE item to gpt-5.5. ~96% of the always-5.5 spend was wasted.

4. **Reasoning-model latency is real.** gpt-5.5 averaged 2.75 s/call vs gpt-4.1's sub-second — a
   second routing axis (latency, not just cost) that argues further for reserving it for the tail.
