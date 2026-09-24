# Step 7 — Chemical-mechanical polishing

## Why CMP exists

Every other step in this simulator broadly follows the surface it is
given. Deposition drapes over topography, etching cuts into it,
oxidation grows out of it. Topography therefore **accumulates**, and
after a handful of patterned layers the wafer is too rough to print on:
lithography has a depth of focus of a few hundred nanometres, and a
surface that varies by more than that cannot be imaged sharply
everywhere at once.

CMP is the only step whose product is *flatness*. It is what makes
multi-level metal possible, and its arrival in the early 1990s is a
large part of why interconnect stacks went from two layers to ten.

## The mechanism

Abrasive slurry under a rotating polishing pad. Preston's equation gives
the local removal rate as

    MRR = K_p * P * v

with `P` the local pressure and `v` the pad–wafer relative velocity. The
planarising behaviour comes entirely out of the `P`: the pad presses
hardest on whatever sticks up, so high features are removed faster than
low ones and the surface converges toward a plane.

## The model

Rather than simulate pad mechanics, the outcome is exposed as one
`planarity` knob blending two limiting behaviours:

- `planarity = 1` — everything is removed down to a single flat plane.
- `planarity = 0` — every column loses the same thickness and the
  topography survives intact. That is a blanket etch-back, not a polish.

Real CMP lands between, typically 0.6–0.9 over micron-scale features,
degrading as features get wider.

### Removal has to exceed the step

A consequence worth internalising, and it falls out of the model rather
than being coded in:

| removal | starting step | remaining step | planarization |
|---|---|---|---|
| 100 nm | 300 nm | 200 nm | 0.33 |
| 200 nm | 300 nm | 100 nm | 0.67 |
| 300 nm | 300 nm | 0 nm | 1.00 |
| 400 nm | 300 nm | 0 nm | 1.00 |

You cannot planarise a 300 nm step by removing 200 nm, no matter how
good the process is, because the low regions have not been reached yet.
Degree of planarization is capped at removal ÷ step until removal
catches up. This is why oxide fill is deliberately over-deposited before
CMP.

### Polish stops

`stop_on` names a material the slurry will not cut. Critically it is a
**global** clamp, not per-column: a polishing pad is rigid across many
features, so once it rides on the stop layer anywhere, removal
everywhere stops too.

That is exactly the STI planarisation scheme. A nitride pad on the field
areas, a trench filled with over-deposited oxide, and a polish that ends
flush the moment the nitride is exposed:

    nitride left     : 40 nm      (intact)
    oxide on field   : 0 nm       (cleared)
    oxide in trench  : 340 nm     (full)
    surface step     : 0 nm       (flat)

## Assumptions, stated plainly

- **No pressure-driven dishing.** A real pad flexes into wide soft
  regions and polishes them below the plane. This is the main reason
  layouts need dummy fill structures.
- **No erosion.** Dense arrays of features thin faster than isolated
  ones.
- **No pattern-density dependence at all.** Removal here depends on
  height, never on what fraction of the local area is hard material.
- **The stop is perfect.** A real nitride stop has finite selectivity,
  around 4:1 against oxide, so it does slowly thin.

Adding density dependence would be the single highest-value upgrade, and
it is the mechanism behind the three omissions above.

## If someone asks

**"Why is your polish stop global instead of per-column?"** Because the
pad is rigid over a length scale much larger than a feature. If one
column hit nitride and its neighbours kept polishing, you would be
modelling a pad that conforms to every feature, which is the opposite of
what makes CMP planarise.

**"Why does your model refuse to flatten a 300 nm step when I only
remove 100 nm?"** Because the low regions have not been touched yet. It
is not a limitation of the model, it is the reason fill layers are
over-deposited.
