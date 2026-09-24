# Step 9 — Cross-section visualization

The deliverable of this whole project is a picture of a wafer that
someone can look at and understand. This module produces it.

## Design rules

**Identity never rests on colour alone.** Every material carries a hatch
texture as well as a colour, and appears in the legend. The figure
therefore survives colour-vision deficiency, greyscale printing, and a
washed-out projector.

**The palette was validated, not chosen by eye.** The original colours
put oxide (`#7fb3d5`, light blue) and nitride (`#52be80`, light green)
at a perceptual distance of ΔE 14.6 for *normal* colour vision — below
the legibility floor of 15 — and those two films sit against each other
in nearly every flow in this project. They were re-picked to a
saturated blue and a deeper green, which moves the worst adjacent pair
to ΔE 8.1 under protanopia and passes the CVD separation check.

Purple was tried for nitride and rejected: against a blue oxide it comes
out at ΔE 0.5 under deuteranopia, essentially identical. Worth knowing
that blue/purple is a trap.

**Panels in a sequence share one z scale.** `flow_figure` computes the
union of every panel's range and forces it on all of them. Small
multiples on independently scaled axes invite the reader to compare
heights that are not comparable, and it is a very easy mistake to make
because each panel looks fine on its own.

**Steps that change nothing visible say so.** Exposure writes a latent
image — a dose distribution in the resist — and leaves the structure
identical. Without a note, that panel reads as a rendering bug. It is
labelled `(no change to the structure)` instead, which turns a confusing
panel into a teaching one.

**Empty headroom is cropped.** The simulation domain has 1000 nm of
space above the wafer for films to grow into. Rendering all of it would
put the structure in a thin band at the bottom of a mostly white figure.

**z = 0 is drawn.** A dashed rule marks the original silicon surface —
the datum every thickness in the process history is measured against.
It makes "the field oxide grew 56% up and 44% down" visible rather than
something you have to be told.

## What it renders

`cross_section(wafer, ax=...)` — one wafer, with legend and hatching.

`surface_profile(wafer, ax=...)` — topography as a line, which is the
right view for judging planarity and for step 12's step-height
measurements.

`save_cross_section(wafer, path)` — straight to a file.

`flow_figure(wafer, steps, run=run_recipe, path=...)` — runs a recipe
and draws a panel per step, including the starting wafer. Note the
`run` parameter: the recipe runner is passed in rather than imported, so
this module has no dependency on `recipe.py`. The two communicate
entirely through the `on_step` callback.

## Assumptions and limits

- **Everything is a cross-section.** One vertical slice, no third
  dimension, no perspective. That is a property of the whole simulator,
  not just the renderer.
- **Hatching is drawn with `contourf` overlays**, which is a slight
  abuse of a contour plotter. It works and it is fast enough, but on a
  very fine grid the hatch spacing does not scale with the figure.
- **No dimension annotations yet.** Thicknesses and critical dimensions
  are printed separately rather than drawn onto the figure with leader
  lines. That belongs with step 12's metrology.

## If someone asks

**"Why the hatching, isn't the colour enough?"** Roughly 8% of men have
some form of colour-vision deficiency, and the figure gets printed and
projected. Texture means identity is encoded twice, so nothing depends
on a reader distinguishing two blues.

**"How did you pick the colours?"** They were run through a
colour-vision-deficiency separation check rather than chosen by eye. The
first set failed on exactly the pair that matters most here, oxide
against nitride.
