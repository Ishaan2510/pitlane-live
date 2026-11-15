# How the Strategy tab works

The Strategy tab answers one kind of question: what if one driver had stopped on different
laps, or on different tyres, in a race that has already happened? This page says how the
answer is worked out, how well the method has been checked, and where it should not be
trusted. The numbers on this page are recomputed every time race data is built.

## The short version

- We change **one driver** and hold **everyone else exactly as they raced**.
- The driver starts from the lap times they really set. Each lap is adjusted only for the
  tyres they would have been on instead.
- The tyre effect comes from a model fitted to that race's own lap times.
- Every answer comes with a range from {{runs}} simulations, and a confidence level.
- Overtaking and traffic are **not** modelled. A Safety Car bunching the field up is
  **not** modelled either. Both are flagged on the result when they matter.

## The tyre model

For every race we fit one model to the clean laps of the whole field:

```
lap time = driver pace + fuel × lap number + compound offset + deg rate × tyre age
```

- **Driver pace** is one number per driver: how quick that car and driver were that day.
- **Fuel** is one number per race. Cars get lighter and the track rubbers in, so laps get
  quicker as the race goes on, by a few hundredths of a second per lap.
- **Compound offset** is how much slower or quicker a compound is than the most-used one
  when both are new.
- **Deg rate** is the time lost for every lap of age on the tyre. This is the number the
  whole tab turns on, and it is shown with every result.

Only clean laps are used: green flag for the whole lap, not an in-lap or out-lap, not the
first lap, not the first lap after a restart, not deleted, and within 107% of that driver's
usual pace. A compound gets a curve instead of a straight line only when the curve
predicts unseen drivers better.

Fuel burn and tyre age rise together during a stint, so the model can confuse them. When
the fitted fuel number is not believable, it is fixed at 0.035 s per lap and the race says
so. That happened in {{fuel_prior_races}} of {{modelled}} modelled races.

## The simulation

For the chosen driver, lap by lap:

```
new lap = real lap − model(real tyres) + model(new tyres)
```

Because it starts from the real lap, everything the model does not know stays in the
answer: the traffic they really met, their mistakes, the weather. Then:

- The real pit stops are taken out and the new ones are put in, each costing the median
  pit loss measured in that race (or the Safety Car or VSC figure when the stop falls in a
  real Safety Car or VSC period and that figure could be measured). A stop left where it
  really was keeps what it really cost.
- Laps under a Safety Car, VSC or red flag keep their real times whatever the tyres.
- The new race time is compared with every other car's real time, lap by lap, to give a
  position.

## How well it works

We check the tyre model in the hardest fair way we can: fit it **without** a driver, give
it only that driver's first-stint pace, and ask it to predict the rest of their race from
the tyres they were on.

| Check, across {{modelled}} races | Result |
|---|---|
| Races with a model | {{modelled}} of {{races}} |
| Races the Strategy tab will simulate | {{simulated}} of {{races}} |
| Error on an unseen driver, per lap (median race) | {{median_lodo_mae_s}} s |
| Error on an unseen driver, per stint (median race) | {{median_stint_mae_s}} s |
| Lap-time variation explained (median R²) | {{median_r2}} |
| Typical scatter of a lap around the fit | {{median_rmse_s}} s |
| Compound fits rated high / medium / low confidence | {{high}} / {{medium}} / {{low}} |

The per-stint number is the one to remember. A stint the model has not seen is off by
about {{median_stint_mae_s}} seconds in total. Strategy calls are often decided by less
than that, so a result that says "three seconds quicker" is not a finding. The range on
every result includes this error.

## What it gets right

On a normal dry race the model explains most of the lap-to-lap variation, tells a
high-wear track from a low-wear one without being told, and predicts a driver it has never
seen to about half a second a lap. It is good at the shape of a strategy question: how much
an extra stop costs, roughly when old tyres stop being worth keeping, and what a stop under
a Virtual Safety Car saves.

## Where it fails

- **Safety Cars and red flags.** A real Safety Car closes the field up: a ten second lead
  becomes nothing. Our field is fixed and cannot close up, so seconds gained or lost before
  a Safety Car are carried through it. A call that leaves the real race before a Safety Car
  or red flag is marked low confidence for this reason, whatever the tyre model says.
- **Traffic.** Coming out of the pits behind a slower car can cost more than the stop
  saved. We report who the driver would have rejoined behind and how many laps they would
  have spent behind a slower car, but we do not turn that into time.
- **Nobody reacts.** In a real race the car ahead covers an undercut. Here it does not.
- **Tyre management.** The deg rates are those of tyres driven the way the drivers chose
  to drive them, often saving them. A tyre pushed harder to make a new strategy work would
  wear faster than the model says.
- **Compound offsets.** Race data often makes the softer tyre look no quicker than the
  harder one when new, because the softer tyre is usually on the car in the opening stint,
  in traffic, with everyone saving tyres. Where that happens the compound is marked low
  confidence.
- **The model's fastest strategy flatters itself.** Searching thousands of strategies for
  the best one also finds the model's own errors. Read "model's fastest" as a suggestion to
  look at, not as proof a team got it wrong.
- **Wet and mixed races** are not simulated at all. When to switch to slicks decides them
  and the model knows nothing about a drying track.
- **Longer stints than anyone ran.** Past the oldest tyre seen in that race the model is
  guessing, and says so.

## Reading a result

- The headline position always comes with a range: the positions that 80% of the
  simulations fall in.
- **High** confidence means the tyres involved were well measured and nothing above
  applies. It does not mean the answer is certain.
- **Low** confidence results are shown muted, with the reason. Treat them as a sketch.
- The same link always gives the same numbers: the random draws are seeded and the seed is
  in the link.
