"""
Confromal vs directiona; deposition into a trench. 
The trench in this is carved by hand, will produce it properly later
"""

from procsim.wafer import Wafer
from procsim.deposition import deposit
from procsim.materials import SIO2, VACUUM

CHARS = {0: ".", 1: "#", 2: "o"}

def show(w, r0, r1, c0, c1, rstep=8, cstep=2):
    for r in range(r0, r1, rstep):
        print("".join(CHARS.get(int(v), "?") for v in w.grid[r, c0:c1:cstep]))

def trench_wafer():
    w = Wafer()
    w.grid[500:650, 400:500] = VACUUM
    return w

for conformal in (False, True):
    w = trench_wafer()
    deposit(w, SIO2, thickness_nm=40.0, conformal=conformal)
    print(f"=== conformal={conformal} ===")
    show(w, 470, 680, 380, 520)
    print("total oxide cells:", int((w.grid == SIO2).sum()))
    print("oxide in a sidewall column:", int((w.grid[:, 402] == SIO2).sum()))
    print()
