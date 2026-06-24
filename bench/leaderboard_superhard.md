# Benchmark leaderboard — suite `superhard` (56 tasks)
_measured 17 models, spent ~$22.9476, generated 2026-06-23 23:11_

**Reference gpt-5.5: acc=0.821, $0.03189/task**

## Realizable cost-accuracy Pareto frontier

| acc | $/task | × cheaper than ref | strategy | members |
|---|---|---|---|---|
| 0.107 | 0.00002 | 1703.5× | solo | gemini-3.1-flash-lite |
| 0.732 | 0.00049 | 64.6× | solo | deepseek-v4-flash |
| 0.804 | 0.00175 | 18.2× | solo | gpt-5-nano |
| 0.821 | 0.00514 | 6.2× | vote-3 | qwen3-235b-a22b-2507+glm-4.7-flash+gpt-5-nano |

**Cheapest config matching ref accuracy (0.821):** vote-3 [qwen3-235b-a22b-2507+glm-4.7-flash+gpt-5-nano] = 0.821 @ $0.00514/task (6.2× cheaper)

_oracle ceiling (pool): 0.821 @ $0.37789/task (unrealizable)_

## Full table (top 60 by accuracy, then cost)

| acc | $/task | strategy | members |
|---|---|---|---|
| 0.821 | 0.00514 | vote-3 | qwen3-235b-a22b-2507+glm-4.7-flash+gpt-5-nano |
| 0.821 | 0.00564 | vote-4 | qwen3-235b-a22b-2507+deepseek-v4-flash+glm-4.7-flash+gpt-5-nano |
| 0.821 | 0.00603 | vote-4 | qwen3-235b-a22b-2507+glm-4.7-flash+llama-4-maverick+gpt-5-nano |
| 0.821 | 0.00653 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+deepseek-v4-pro+gpt-5-nano |
| 0.821 | 0.00656 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+glm-4.7-flash+gpt-5-nano |
| 0.821 | 0.00678 | vote-3 | deepseek-v4-pro+glm-4.7-flash+gpt-5-nano |
| 0.821 | 0.00687 | vote-4 | deepseek-v4-pro+glm-4.7-flash+gpt-5-nano+gpt-4o-mini |
| 0.821 | 0.00691 | vote-4 | deepseek-v4-pro+glm-4.7-flash+gpt-5-nano+gpt-4.1 |
| 0.821 | 0.00702 | vote-4 | deepseek-v4-pro+glm-4.7-flash+nova-lite-v1+gpt-5-nano |
| 0.821 | 0.00731 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+deepseek-v4-pro+glm-4.7-flash |
| 0.821 | 0.00764 | vote-4 | qwen3-235b-a22b-2507+deepseek-v4-pro+glm-4.7-flash+gpt-5-nano |
| 0.821 | 0.00819 | vote-4 | qwen3-235b-a22b-thinking-2507+deepseek-v4-pro+glm-4.7-flash+gpt-5-nano |
| 0.821 | 0.00930 | vote-3 | qwen3-235b-a22b-thinking-2507+deepseek-v4-pro+minimax-m2.5 |
| 0.821 | 0.00942 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+minimax-m2.5+gpt-5-nano |
| 0.821 | 0.00966 | vote-3 | glm-4.7-flash+minimax-m2.5+gpt-5-nano |
| 0.821 | 0.00968 | vote-4 | glm-4.7-flash+minimax-m2.5+gemini-3.1-flash-lite+gpt-5-nano |
| 0.821 | 0.00975 | vote-4 | glm-4.7-flash+minimax-m2.5+gpt-5-nano+gpt-4o-mini |
| 0.821 | 0.00979 | vote-4 | glm-4.7-flash+minimax-m2.5+gpt-5-nano+gpt-4.1 |
| 0.821 | 0.00990 | vote-4 | glm-4.7-flash+minimax-m2.5+nova-lite-v1+gpt-5-nano |
| 0.821 | 0.01015 | vote-4 | deepseek-v4-flash+glm-4.7-flash+minimax-m2.5+gpt-5-nano |
| 0.821 | 0.01016 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+deepseek-v4-pro+minimax-m2.5 |
| 0.821 | 0.01019 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+glm-4.7-flash+minimax-m2.5 |
| 0.821 | 0.01053 | vote-4 | qwen3-235b-a22b-2507+glm-4.7-flash+minimax-m2.5+gpt-5-nano |
| 0.821 | 0.01054 | vote-4 | glm-4.7-flash+minimax-m2.5+llama-4-maverick+gpt-5-nano |
| 0.821 | 0.01105 | vote-4 | qwen3-235b-a22b-thinking-2507+deepseek-v4-pro+minimax-m2.5+gpt-5-nano |
| 0.821 | 0.01107 | vote-4 | qwen3-235b-a22b-thinking-2507+glm-4.7-flash+minimax-m2.5+gpt-5-nano |
| 0.821 | 0.01182 | vote-4 | qwen3-235b-a22b-thinking-2507+deepseek-v4-pro+glm-4.7-flash+minimax-m2.5 |
| 0.821 | 0.01216 | vote-4 | deepseek-v4-pro+glm-4.7-flash+minimax-m2.5+gpt-5-nano |
| 0.821 | 0.01600 | vote-4 | qwen3-235b-a22b-2507+deepseek-v4-flash+glm-5.2+gpt-5-nano |
| 0.821 | 0.01671 | solo | kimi-k2.5 |
| 0.821 | 0.01673 | vote-2 | kimi-k2.5+gemini-3.1-flash-lite |
| 0.821 | 0.01678 | vote-4 | qwen3-235b-a22b-2507+deepseek-v4-flash+glm-4.7-flash+glm-5.2 |
| 0.821 | 0.01680 | vote-2 | kimi-k2.5+gpt-4o-mini |
| 0.821 | 0.01684 | vote-2 | kimi-k2.5+gpt-4.1 |
| 0.821 | 0.01692 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+glm-5.2+gpt-5-nano |
| 0.821 | 0.01696 | vote-2 | kimi-k2.5+nova-lite-v1 |
| 0.821 | 0.01715 | vote-3 | deepseek-v4-pro+glm-5.2+gpt-5-nano |
| 0.821 | 0.01723 | vote-4 | deepseek-v4-pro+glm-5.2+gpt-5-nano+gpt-4o-mini |
| 0.821 | 0.01727 | vote-4 | deepseek-v4-pro+glm-5.2+gpt-5-nano+gpt-4.1 |
| 0.821 | 0.01739 | vote-4 | deepseek-v4-pro+glm-5.2+nova-lite-v1+gpt-5-nano |
| 0.821 | 0.01760 | vote-2 | kimi-k2.5+llama-4-maverick |
| 0.821 | 0.01767 | vote-4 | qwen3-235b-a22b-thinking-2507+qwen3-235b-a22b-2507+deepseek-v4-pro+glm-5.2 |
| 0.821 | 0.01784 | vote-3 | kimi-k2.5+llama-4-maverick+nova-lite-v1 |
| 0.821 | 0.01792 | vote-3 | deepseek-v4-pro+glm-4.7-flash+glm-5.2 |
| 0.821 | 0.01800 | vote-4 | deepseek-v4-pro+glm-4.7-flash+glm-5.2+gpt-4o-mini |
| 0.821 | 0.01801 | vote-4 | qwen3-235b-a22b-2507+deepseek-v4-pro+glm-5.2+gpt-5-nano |
| 0.821 | 0.01804 | vote-4 | qwen3-235b-a22b-2507+glm-4.7-flash+glm-5.2+gpt-5-nano |
| 0.821 | 0.01805 | vote-4 | deepseek-v4-pro+glm-4.7-flash+glm-5.2+gpt-4.1 |
| 0.821 | 0.01816 | vote-4 | deepseek-v4-pro+glm-4.7-flash+glm-5.2+nova-lite-v1 |
| 0.821 | 0.01847 | vote-2 | kimi-k2.5+gpt-5-nano |
| 0.821 | 0.01849 | vote-3 | kimi-k2.5+gemini-3.1-flash-lite+gpt-5-nano |
| 0.821 | 0.01855 | vote-3 | kimi-k2.5+gpt-5-nano+gpt-4o-mini |
| 0.821 | 0.01856 | vote-4 | qwen3-235b-a22b-thinking-2507+deepseek-v4-pro+glm-5.2+gpt-5-nano |
| 0.821 | 0.01857 | vote-4 | kimi-k2.5+gemini-3.1-flash-lite+gpt-5-nano+gpt-4o-mini |
| 0.821 | 0.01860 | vote-3 | kimi-k2.5+gpt-5-nano+gpt-4.1 |
| 0.821 | 0.01861 | vote-4 | kimi-k2.5+gemini-3.1-flash-lite+gpt-5-nano+gpt-4.1 |
| 0.821 | 0.01868 | vote-4 | kimi-k2.5+gpt-5-nano+gpt-4o-mini+gpt-4.1 |
| 0.821 | 0.01871 | vote-3 | kimi-k2.5+nova-lite-v1+gpt-5-nano |
| 0.821 | 0.01873 | vote-4 | kimi-k2.5+gemini-3.1-flash-lite+nova-lite-v1+gpt-5-nano |
| 0.821 | 0.01878 | vote-4 | qwen3-235b-a22b-2507+deepseek-v4-pro+glm-4.7-flash+glm-5.2 |
