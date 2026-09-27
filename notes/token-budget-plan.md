# Token budget plan

| Stage | Model | Effort | Estimate (% of a 5-hour window) |
|---|---|---|---|
| /research, quick lookups | Haiku | low | 2% |
| /grill-with-docs, /to-spec, /to-tickets | opusplan | high | 30% |
| /implement + /tdd (per ticket) | Sonnet | medium | 20% |
| /code-review (per ticket) | Sonnet | high | 10% |

## How many 5-hour windows will the tickets take?

It looks like around 3 windows for the whole project, and maybe around 2.5 for the tickets alone, guessing conservatively using my estimates.

## How much of one week is that?

Based on my 5-hour window estimate and my ledger suggesting there are around 4 5-hour sessions within a week of usage, about 75%. I only have about 79% left for this week, making this a bit tight. 

## What I'll cut first if I'm wrong

If I'm running over budget, my first move will be to lower code review from high to medium effort, since it seems to be an easy saving, especially if it's using 10% of a 5-hour window for each ticket. I will also focus on using /clear and /compact in the right places consistently to safeguard against context bloat. I can also move simpler tickets to a cheaper setting, or potentially use higher powered reviewing matched with slightly lower powered implementation (would take some experimentation).

## My reasoning

My estimates are based on the manual's sample report, which gives me certain expectations (such as grill costing about 30% of a window), my own intuition based on my project size and scale (fairly detailed and large in scale relatively), and my own ledger, which showed setup and Exercise A using about 4% of my 5-hour window on their own as well as my weekly meter 1%, despite being small Sonnet tasks. 
