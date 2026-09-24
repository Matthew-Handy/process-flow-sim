# Step 5 — Etching

## The physics

Etching removes material. What makes it interesting is that *how much*
and *in which direction* are set by two independent things.

### Selectivity

Silicon does not have an etch rate. It has an etch rate **in a given
chemistry**. SF6 plasma tears through silicon at hundreds of nm/min and
barely marks silicon dioxide; CHF3 does the reverse. The ratio

    S = rate(target) / rate(other)

is the **selectivity**, and it is a property of the material–chemistry
pair, never of a material alone. This is why `Material` in
`materials.py` carries only identity and colour: putting an etch rate
on it would be a category error, and it would have had to be unpicked
here.

Selectivity is what makes multi-layer processing possible at all. You
cannot open a contact through 500 nm of oxide onto a 100 nm silicon
region without a chemistry that stops when it gets there.

### Directionality

Wet chemical etching is **isotropic**: the etch front advances at the
same rate in every direction. Under a mask edge it therefore eats
sideways as fast as it eats down, producing **undercut**. A film 200 nm
thick cannot be patterned to better than about 400 nm of linewidth loss
by a wet etch, which is a hard floor on resolution.

Reactive ion etching is **directional**: ions are accelerated vertically
into the wafer, so removal happens overwhelmingly downward and sidewalls
stay near-vertical. This is the single reason sub-micron patterning
exists. Every feature on a modern chip is defined by a directional etch.

## The model

`anisotropy` is the fraction of the process time that behaves
directionally. It runs 0 (pure wet) to 1 (pure RIE), and the etch is
computed in two passes.

### Directional pass — a time budget down each column

The clean trick here is to think of it as *time*, not depth. Each cell
costs

    dz / rate(material of that cell)

minutes to clear. A cumulative sum down each column then gives the time
at which the etch front would reach every cell, and removing everything
whose arrival time is inside the budget handles multi-layer stacks,
selectivity and etch stops with no special cases:

- A slow material has a high per-cell cost, so it eats the budget and
  the etch slows down exactly as it should.
- A material the chemistry does not attack has rate 0, so its cost is
  **infinity** — that cell and everything below it can never be
  reached. One convention gives you both masking (from above) and etch
  stopping (from below), because physically those are the same thing.

### Isotropic pass — the mirror of conformal deposition

Whatever time was not directional removes material equally in all
directions. Conformal deposition fills every *empty* cell within reach
of a solid; isotropic etching clears every *solid* cell within reach of
open space. Same distance transform, run the other way:

    distance = distance_transform_edt(solid, sampling=(dz, dx))
    remove where distance <= rate * isotropic_time

`sampling` again supplies the physical cell size, so the etch front is
circular even when `dx != dz`.

## What it produces

Same mask, same chemistry, same five minutes, on a 200 nm oxide film
under a 1000 nm resist line:

| anisotropy | oxide linewidth at the base |
|---|---|
| 1.0 | 1000 nm — exactly the mask |
| 0.7 | 938 nm |
| 0.3 | 894 nm |
| 0.0 | 868 nm |

At 1.0 the mask transfers faithfully. As directionality falls the line
narrows from both sides, and the profile develops the classic undercut
shape: narrowest at the top, where the sidewall has been exposed to the
etchant longest, widening toward the base.

## Assumptions, stated plainly

- **The two passes are sequential, not simultaneous.** A real etch does
  both at once. Running directional first then isotropic slightly
  overstates undercut at the bottom of deep features.
- **The isotropic pass thresholds one distance field per material.** It
  does not trace the etchant's path through intervening materials, so a
  slow film does not shield a fast one lying behind it laterally.
- **No aspect-ratio dependence.** Real deep etches slow down as the
  trench gets deeper because reactants struggle to reach the bottom and
  products struggle to leave (RIE lag). Not modelled; it is on the
  advanced list.
- **No sidewall passivation.** The Bosch process alternates etch and
  passivation to get near-vertical deep trenches, leaving scalloped
  walls. Not modelled.
- **Rate constants are representative, not measured.** Real rates depend
  on tool, pressure, power and gas ratios. The *selectivity ratios* are
  the physically meaningful part here.

## If someone asks

**"Why isn't etch rate a property of your Material class?"** Because
selectivity is a property of the material–chemistry pair. Silicon's rate
in SF6 and in CHF3 differ by about two orders of magnitude, so a single
number on the material would be meaningless.

**"How does your etch stop work?"** There is no separate etch-stop
mechanism. A material the chemistry does not attack has rate zero, so
its per-cell clearing time is infinite and the cumulative sum down that
column never gets past it. Masking and etch stopping are the same code
path.

**"Why does undercut make the line narrower at the top than the
bottom?"** The top of the sidewall is exposed to the etchant from the
first moment; the bottom is only exposed once the front has worked its
way down. Exposure time varies with depth, so removal does too.
