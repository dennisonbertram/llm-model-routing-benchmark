# The Committee and the Expert

### What 56 hard problems, 17 models, and Sakana Fugu taught me about when many beats one

Here is a question worth sitting with: **Can a room full of dumb people, coordinating together in a good harness, produce an output better than a single smarter person?**

It's the question underneath a whole genre of AI engineering. Model routing, mixtures of agents, multi-agent debate, self-consistency voting, Sakana's Fugu conductor — they are all, in spirit, the same wager. Take a bunch of models that are individually cheaper or weaker than the frontier, wire them together cleverly, let them confer, vote, critique, escalate — and hope the *system* lands somewhere the single best model can't reach. It's the wisdom of crowds, ported to silicon.

I wanted to know if the wager pays. So I built a benchmark and bought the answer with real API calls.

## The setup

Fifty-six genuinely hard problems — number theory and combinatorics with exact integer answers, graded by brute force so "correct" means *provably* correct, not "an LLM judge liked it." Hard enough that the frontier model, GPT-5.5, gets only 46 of them. Seventeen models, from `gpt-4o-mini` up through both of Sakana Fugu's multi-agent conductors. Every model and every committee runs the *same* problems, with the *same* grader and the *same* cost accounting — Fugu billed honestly on every orchestration token it burns. About \$23, all in. The raw measurements are public; you can re-derive every number below in ten lines of Python.

Then I let the committees vote.

## The answer is no

On a single hard problem, the crowd does not beat the expert. Not "rarely." Not in my data, not once.

GPT-5.5 solves 46 of the 56. Fugu-mini solves 46. Fugu-Ultra solves 46. And here is the part that should stop you: **they are the same 46.** Cell for cell, the multi-agent conductor — orchestrating a whole pool of models, conferring internally, spending 3× to 7× more and up to four minutes per question — arrives at exactly the set of answers a single GPT-5.5 call already had. The committee did not find one problem the expert missed. Neither did anyone else: across all seventeen models, **not a single one solves a problem GPT-5.5 gets wrong.** The ceiling of the entire pool *is* the best individual in it.

Ten problems — a nasty family of nonlinear modular recurrences — go unsolved by everyone, conductor and expert alike. You cannot vote a correct answer into existence when no one in the room has it. That is the whole game in one sentence.

The crowd's only real product here is **price**. A single small model, `gpt-5-nano`, lands one problem behind the frontier at *eighteen times cheaper*. A cheap three-model vote matches GPT-5.5's full score at *six times cheaper*. Those are real wins — but they are efficiency wins, not intelligence wins. Nobody out-thought the expert. They just reached the expert's answer for less money. And orchestration, the most elaborate form of "coordinate the crowd," was the *worst* deal on the board: top-tier expert results at a multiple of top-tier expert cost.

This matches the dumb, durable intuition we already hold about people. A hundred random strangers, however well you organize the meeting, will not collectively out-prove a single strong mathematician on a single hard proof. Coordination doesn't manufacture an insight that isn't in anyone's head.

## But the disagreement is trying to tell you something

Here's the wrinkle that makes this interesting rather than merely deflating.

When you watch *when* the committee is right, a clean signal falls out. Average across twenty different cheap three-model votes: **when the models all agree, they are right 94% of the time. When they disagree, the vote is right only 41% of the time** — worse than a coin flip among the answers on the table.

Read that again, because it inverts the usual pitch. The value of the vote is not the vote. Consensus isn't producing the right answer; it's *reporting* that the answer was easy — easy enough that even the cheap models converge, and on those, you barely needed the expert at all. Disagreement is the real product: it's a smoke alarm. It tells you, reliably, *this one is hard, and the crowd is about to guess wrong — go get the expert.*

That's exactly how the best-performing cheap configuration works. Let the cheap models answer; when they agree, pocket it; when they fight, escalate to GPT-5.5. You spend frontier money only on the genuinely hard tail, and you match frontier accuracy for a fraction of the bill. The committee earns its keep not by being smart, but by knowing — out loud, measurably — when it's out of its depth.

## So what is the crowd actually for?

If a room of ordinary minds can't out-reason one expert on a single hard question, why do we believe in crowds at all? Because we've all watched them win — just not at this.

A crowd's edge was never the one-off question. It's **time and scale.** A hundred ordinary people will flatten a lone genius on a sprawling, months-long project — not because anyone in the hundred is smarter, but because the work has more pieces than a single head can hold. They divide it. They hold context in parallel. They carry threads the expert would have to drop to pick up another. The genius isn't beaten on any one decision; the genius is beaten by *throughput*, by the sheer surface area of a real project. Past a certain size, the single expert stops being the smartest person in the room and starts being the bottleneck.

We have been pointing our multi-model machinery at precisely the task where it cannot win. A prompt is a single hard question. Routing a committee over a prompt is staging the strangers-versus-mathematician fight on purpose — and then acting surprised when the mathematician wins, and charges us extra for the strangers.

## The relocation

This is not a knock on Sakana Fugu. Fugu is a genuinely capable conductor; it reaches the frontier and it does it honestly. The finding isn't that orchestration is bad. The finding is that **we've been aiming it at the wrong target.**

The interesting frontier for model routing is not *which model answers this prompt.* On that question, the answer is boringly settled: pick one good model, and escalate to a better one only when the cheap ones visibly disagree. The interesting frontier is *the long-running task* — the project with a dozen moving parts, with context that won't fit in any single window, with sub-goals that can run in parallel and threads that need holding while other threads advance. That is the shape of work where many ordinary agents genuinely beat one brilliant one, for the same reason a hundred people beat a genius on a year-long build: not by being smarter per step, but by holding more, dividing more, and never having to drop a thread.

Maybe the secret of model routing was never about prompts at all. Maybe it's this: stop using the crowd to *answer*, and start using it to *execute.* Route models not over questions, but over projects.

---

*Honest fine print, because the whole point is that you can check me. This result is about hard **exact-answer math** — number theory and combinatorics with a single right integer. It is a fair test of orchestration on hard, verifiable problems; it is **not** a test of orchestration on coding, open-ended reasoning, or long-horizon agentic work — which is, conveniently, exactly the regime the back half of this essay claims is the real opportunity. That's a hypothesis here, not a finding. Each model-task pair was measured once, at temperature zero, n=56; one problem is ~1.8 points, so when I say two strong models "tie," I mean their one-problem gap is inside the noise. The methodology was independently audited, read-only, by a different model (OpenAI's Codex), which caught real bugs before I published. The raw data, the code, the task generator, and the audit's fixes are all in this repository — re-run it, break it, tell me where I'm wrong.*

---

**The reference document** — the full research report, with the complete results table, the cost-accuracy frontier, and every figure cited above — is [`bench/Model-Routing-vs-Fugu.md`](bench/Model-Routing-vs-Fugu.md) (and a typeset [PDF](bench/Model-Routing-vs-Fugu.pdf)). The experimental design is in [`METHODOLOGY.md`](METHODOLOGY.md); the raw measurements are in [`bench/matrix_superhard.json`](bench/matrix_superhard.json). Start at the [README](README.md).

