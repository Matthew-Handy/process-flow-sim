"""
Thermal oxidation of silicon (Deal-Grove model)
oxide growth is not linear in time. use x^2 + A x = B (t + tau)
solved for thickness as x = (A/2) [ sqrt(1 + 4 B (t + tau) / A^2) - 1 ]
two limits come out: 
        thin film / short time  x -> (B/A)(t+ tau)  reaction limited
        thick film / long time  x -> sqrt(B t)      diffusion limited'
B is the parabolic rate constant, B/A the linear rate constant. Both are Arrhenius in temp.
Constants are for <100> silicon at 1 atm from Deal & Grove (1965); <111> silicon oxidies 1.68x faster
in the linear reginme
"""

import numpy as np
from procsim.materials import VACUUM, SILICON, SIO2

K_B_EV = 8.617333e-5        #Boltzmann constant, eV/K

#prefactor activation energy in eV. B is in um^2/hr, B/A in um/hr -- converted to nm and minutes below
RATE_CONSTANTS = {
    "dry": {"B": (7.72e2, 1.23), "B_over_A": (3.71e6, 2.00)},
    "wet": {"B": (3.86e2, 0.78), "B_over_A": (9.70e7, 2.05)},
}

#ASSUMPTION: dry oxidation does not extrapolate to zero
#Silicon is already carrying around 25nm of oxide
#Consequence: this model over-predicts very short and dry oxidations. Unreliable below 30nm
X_INITIAL_DRY_NM = 25.0

def rate_constants(temperature_c, ambient="wet"):
    """B in nm^2//min and A in nm at this temp"""
    if ambient not in RATE_CONSTANTS:
        raise ValueError(f"ambient must be 'dry' or 'wet', got {ambient!r}")
    kT = K_B_EV * (temperature_c + 273.15)
    c_b, ea_b = RATE_CONSTANTS[ambient]["B"]
    c_ba, ea_ba = RATE_CONSTANTS[ambient]["B_over_A"]
    b_nm2_min = c_b * np.exp(-ea_b / kT) * 1e6 / 60.0           #um^2/hr -> nm^2/min
    b_over_a_nm_min = c_ba * np.exp(-ea_ba / kT) * 1e3 / 60     #um/hr -> nm/min
    return b_nm2_min, b_nm2_min / b_over_a_nm_min

def oxide_thickness(temperature_c, time_min, ambient="wet", x_initial_nm=0.0):
    """Total oxide thickness in nm after `time_min` at `temperature_c`.
    `x_initial_nm` is oxide already on the wafer, which slows growth."""
    b, a = rate_constants(temperature_c, ambient)
    x_i = x_initial_nm
    if ambient == "dry":
        x_i = np.maximum(x_i, X_INITIAL_DRY_NM)
    tau = (x_i**2 + a * x_i) / b
    return 0.5 * a * (np.sqrt(1.0 + 4.0 * b * (time_min + tau) / a**2) - 1.0)

SI_CONSUMED_FRACTION = 0.44

def oxidize(wafer, *, temperature_c, time_min, ambient="wet"):
    """Grow thermal oxide wherever the oxidant can reach silicon"""
    cols = np.arange(wafer.n_cols)
    surf = wafer.surface_rows()

    has_material = surf < wafer.n_rows
    surface_material = np.full(wafer.n_cols, VACUUM, dtype=wafer.grid.dtype)
    surface_material[has_material] = wafer.grid[surf[has_material], cols[has_material]]
    oxidizable = np.isin(surface_material, [SILICON, SIO2])

    x_i = wafer.thickness_of(SIO2)
    x_f = oxide_thickness(temperature_c, time_min, ambient, x_initial_nm=x_i)
    growth = np.maximum(x_f - x_i, 0.0)
    growth[~oxidizable] = 0.0

    n_total = np.round(growth / wafer.dz).astype(int)
    n_consumed = np.round(SI_CONSUMED_FRACTION * growth / wafer.dz).astype(int)
    n_up = n_total - n_consumed

    if (surf - n_up).min() < 0:
        raise ValueError("not enough headroom to grow this oxide")

    is_si = wafer.grid == SILICON
    si_top = np.where(is_si.any(axis=0), np.argmax(is_si, axis=0), wafer.n_rows)

    rows = np.arange(wafer.n_rows)[:, None]
    consume = (rows >= si_top[None, :]) & (rows < (si_top + n_consumed)[None, :])
    grow_up = (rows >= (surf - n_up)[None, :]) & (rows < surf[None, :])
    wafer.grid[consume | grow_up] = SIO2

    grown = growth[oxidizable]
    wafer.log("oxidation", temperature_c=float(temperature_c),
              time_min=float(time_min), ambient=ambient,
              mean_growth_nm=float(grown.mean()) if grown.size else 0.0)
    return wafer


