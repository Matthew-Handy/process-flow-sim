"""
Run the LOCOS isolation recipe and render the whole flow.
LOCOS -- local oxidation of silicon -- was the standard way to isolate
neighbouring transistors for about two decades. A silicon nitride pad
covers the areas where devices will go; nitride blocks oxygen, so a long
wet oxidation grows thick field oxide everywhere else and nothing at all
underneath the pad. Strip the pad and you are left with bare silicon
islands separated by thick recessed oxide.

Writes two figures into figures/.
"""

import matplotlib

matplotlib.use("Agg")

import numpy as np

from procsim.materials import SI3N4, SIO2
from procsim.recipe import load_recipe, recipe_summary, run_recipe
from procsim.viz import flow_figure, save_cross_section
from procsim.wafer import Wafer

RECIPE = "recipes/locos_isolation.yaml"

steps = load_recipe(RECIPE)
wafer = Wafer()

flow_figure(
    wafer, steps, run=run_recipe, ncols=2,
    path="figures/locos_flow.png",
    suptitle="LOCOS isolation — cross-section after every process step",
)
save_cross_section(wafer, "figures/locos_final.png",
                   title="LOCOS isolation, finished")

oxide = wafer.thickness_of(SIO2)
print("Finished wafer")
print(f"  field oxide     : {oxide.max():6.0f} nm")
print(f"  active-area oxide: {oxide.min():6.0f} nm")
print(f"  nitride left    : {wafer.thickness_of(SI3N4).max():6.0f} nm")
print(f"  isolation step  : {np.ptp(wafer.surface_profile_nm()):6.0f} nm")
print()
print("Process history")
print(recipe_summary(wafer))
print()
print("Figures written to figures/locos_flow.png and figures/locos_final.png")
