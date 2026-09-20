"""
Binary mask patterning, and how resist contrast sets sidewall slope.
"""

import numpy as np

from procsim.deposition import deposit
from procsim.lithography import develop, expose, spin_coat
from procsim.materials import PHOTORESIST, SIO2
from procsim.wafer import Wafer

CHARS = {0: ".", 1: "#", 2: "o", 5: "R"}


def show(w, r0, r1, c0, c1, rstep=10, cstep=14):
    for r in range(r0, r1, rstep):
        print("".join(CHARS.get(int(v), "?") for v in w.grid[r, c0:c1:cstep]))


print("=== 200 nm lines and spaces, positive tone ===")
w = Wafer()
deposit(w, SIO2, thickness_nm=100.0)
spin_coat(w, thickness_nm=400.0)
expose(w, dose_mj_cm2=120.0,
       clear_regions=[(x, x + 200) for x in range(0, 2000, 400)])
develop(w, dose_to_clear=50.0, contrast=3.0, tone="positive")
show(w, 380, 560, 0, 1000)

print("\nsidewall slope vs resist contrast")
for gamma in (1.5, 3.0, 10.0):
    w2 = Wafer()
    spin_coat(w2, thickness_nm=400.0)
    x = (np.arange(w2.n_cols) + 0.5) * w2.dx
    aerial = 0.5 * (1 + np.cos(2 * np.pi * x / 800.0))
    expose(w2, dose_mj_cm2=120.0, aerial_image=aerial)
    develop(w2, dose_to_clear=50.0, contrast=gamma, tone="positive")
    t = w2.thickness_of(PHOTORESIST)
    sloped = np.sum((t > 20) & (t < 380)) * w2.dx
    print(f"gamma={gamma:4.1f}   sloped-edge width = {sloped:.0f} nm")