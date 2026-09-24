# Step 8 — Recipes

## The idea

Up to here, a process flow was Python: a script calling `deposit`, then
`oxidize`, then `etch`. That works, but it conflates two different
things — the *flow* (what happens, in what order, with what parameters)
and the *simulator* (how each operation is computed).

In a fab those are separate artefacts. The flow is a document. It gets
reviewed, revised, version controlled, argued about in meetings, and
handed between people. The tools that execute it are somebody else's
problem.

So a recipe here is **data**: a list of steps, each naming an operation
and its parameters, living in a YAML or JSON file.

```yaml
steps:
  - op: oxidize
    comment: thin pad oxide to cushion nitride stress on the silicon
    temperature_c: 900
    time_min: 20
    ambient: dry

  - op: deposit
    material: nitride
    thickness_nm: 120
    rate_nm_s: 2.0
    time_s: 60
```

That file diffs cleanly in git, which means a process change shows up in
review as a change to two numbers rather than a change to a script.

## Design decisions

**Materials are written by name.** `material: nitride` rather than
`material: 3`. A recipe is meant to be read by people, so the engine
resolves names and aliases (`oxide`, `SiO2`, `sio2` all mean the same
thing) before calling the operation. Integers still pass through
untouched.

**`comment` keys are ignored.** So the reasoning behind a step can live
next to the step, in the same file, instead of in someone's notebook.

**`on_step` is a callback, not a feature.** `run_recipe` takes an
optional `on_step(index, operation, wafer)` and calls it after every
step. That single hook is how the visualization module renders a panel
per step *without the recipe engine importing matplotlib or knowing
that plotting exists*. It is also how step 12's metrology will hook in,
and how step 13's Monte Carlo will sample intermediate state.

If you take one structural idea from this module, take that one: when
module A needs to happen during module B's loop, the usual instinct is
to make B import A. A callback inverts it, and the two modules stay
independent.

**Errors name the step.** A bad parameter on step 7 of a nine-step flow
reports `step 7 (deposit): unexpected keyword argument`, not a bare
`TypeError` from somewhere inside the deposition code. When a flow is
data, the step index is the only coordinate the user has.

## Two views of the history

`recipe_table(wafer)` returns a pandas DataFrame, one row per step, one
column per parameter. It is wide and sparse, because oxidation and
exposure share almost no parameters — and that is correct for a
machine-readable export. It is what step 13 will write to CSV.

`recipe_summary(wafer)` returns text, one line per step, showing only
the parameters that step actually used and naming materials rather than
printing their ids:

```
 1. oxidation   temperature_c=900, time_min=20, ambient=dry, mean_growth_nm=27.8136
 2. deposition  material=Si3N4, thickness_nm=120, rate_nm_s=2, time_s=60, conformal=True
 3. spin_coat   material=resist, thickness_nm=400, planarize=True
 4. expose      dose_mj_cm2=120, clear_regions=[(0.0, 500.0), ...], from_aerial_image=False
 5. develop     dose_to_clear=50, contrast=3, tone=positive
 6. etch        chemistry=CF4/O2, time_min=2.5, anisotropy=0.9, rates_nm_min={Si3N4:60, ...}
```

Note that this is generated from `wafer.history`, not from the recipe
file. It records what the wafer **actually received**, which will
diverge from what the recipe asked for once step 10 adds variability.
That distinction — requested versus achieved — is the whole basis of
process control.

## If someone asks

**"Why is the recipe a file instead of a script?"** Because a process
flow is a document that gets reviewed and revised by people who are not
the person who wrote the simulator. Keeping it as data means a process
change is a two-line diff, not a code change.

**"How does the plotting get called if the recipe engine doesn't know
about it?"** An `on_step` callback. The caller passes in a function; the
engine calls it after each step and never learns what it does.
