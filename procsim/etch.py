"""Etching: removing material.

Removal is modelled as two components blended by an `anisotropy`
parameter, which is the fraction of the process time that behaves
directionally:

  anisotropy -> 1   ions arrive vertically. Walls stay vertical and a
                    mask edge transfers into the film faithfully. This
                    is reactive ion etching.
  anisotropy -> 0   removal proceeds equally in every direction, so the
                    etch front advances sideways under a mask as fast as
                    it advances down. This is wet chemical etching, and
                    the sideways part is called undercut.

Selectivity is not a property of a material. Silicon does not have "an
etch rate" -- it has an etch rate in a given chemistry. SF6 plasma tears
through silicon and barely marks oxide; CHF3 does the reverse. So rates
live with the chemistry, not in the material registry.

Any material absent from the rate table etches at zero rate, which makes
it a mask (if it is on top) or an etch stop (if it is underneath). That
single convention covers both roles, because physically they are the
same thing.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import distance_transform_edt

from procsim.materials import (
    PHOTORESIST,
    SI3N4,
    SILICON,
    SIO2,
    VACUUM,
    name_of,
)


@dataclass(frozen=True)
class Chemistry:
    """An etch chemistry: what it removes, how fast, and how directionally."""

    name: str
    rates_nm_min: dict
    anisotropy: float
    note: str = ""


# Representative rates. Real numbers depend on tool, pressure, power and
# gas ratios, so treat these as plausible rather than authoritative --
# the selectivity ratios matter more here than the absolute rates.
CHEMISTRIES = {
    "CHF3_O2": Chemistry(
        "CHF3/O2",
        {SIO2: 45.0, SI3N4: 20.0, SILICON: 4.5, PHOTORESIST: 25.0},
        anisotropy=0.95,
        note="oxide RIE, about 10:1 over silicon",
    ),
    "SF6_C4F8": Chemistry(
        "SF6/C4F8",
        {SILICON: 300.0, SIO2: 3.0, SI3N4: 20.0, PHOTORESIST: 60.0},
        anisotropy=0.92,
        note="deep silicon RIE, about 100:1 over oxide",
    ),
    "CF4_O2": Chemistry(
        "CF4/O2",
        {SI3N4: 60.0, SIO2: 12.0, SILICON: 25.0, PHOTORESIST: 40.0},
        anisotropy=0.90,
        note="nitride RIE",
    ),
    "BOE": Chemistry(
        "buffered HF",
        {SIO2: 100.0},
        anisotropy=0.0,
        note="wet oxide etch, fully isotropic, stops dead on silicon",
    ),
    "O2_ash": Chemistry(
        "O2 plasma ash",
        {PHOTORESIST: 300.0},
        anisotropy=1.0,
        note="resist strip, touches nothing else",
    ),
}


def selectivity(chemistry, target, against):
    """Etch rate ratio of `target` over `against` for this chemistry.

    Infinite when the chemistry does not attack `against` at all.
    """
    chem = CHEMISTRIES[chemistry] if isinstance(chemistry, str) else chemistry
    numerator = chem.rates_nm_min.get(target, 0.0)
    denominator = chem.rates_nm_min.get(against, 0.0)
    if denominator == 0.0:
        return np.inf if numerator > 0.0 else 0.0
    return numerator / denominator


def _rate_grid(wafer, rates_nm_min):
    """Per-cell etch rate in nm/min. Unlisted materials get zero."""
    rates = np.zeros(wafer.grid.shape, dtype=float)
    for material_id, rate in rates_nm_min.items():
        if rate < 0.0:
            raise ValueError(
                f"etch rate for {name_of(material_id)} must not be negative"
            )
        rates[wafer.grid == material_id] = float(rate)
    return rates


def etch(wafer, *, time_min, chemistry=None, rates_nm_min=None,
         anisotropy=None):
    """Etch the wafer for `time_min`. Modifies the wafer in place.

    Give either a `chemistry` (a key of CHEMISTRIES, or a Chemistry) or
    an explicit `rates_nm_min` mapping of material id to nm/min.
    `anisotropy` overrides the chemistry's own value when supplied.
    """
    if (chemistry is None) == (rates_nm_min is None):
        raise ValueError("give exactly one of chemistry or rates_nm_min")
    if time_min < 0.0:
        raise ValueError(f"time must not be negative, got {time_min}")

    if chemistry is not None:
        chem = CHEMISTRIES[chemistry] if isinstance(chemistry, str) else chemistry
        rates_nm_min = chem.rates_nm_min
        chemistry_name = chem.name
        if anisotropy is None:
            anisotropy = chem.anisotropy
    else:
        chemistry_name = "custom"
        if anisotropy is None:
            anisotropy = 1.0

    if not 0.0 <= anisotropy <= 1.0:
        raise ValueError(f"anisotropy must be in [0, 1], got {anisotropy}")

    rates = _rate_grid(wafer, rates_nm_min)

    # --- directional component ---------------------------------------
    # Walk down each column spending a time budget. A cell costs
    # dz / rate minutes to clear, and cells the chemistry does not
    # attack cost infinity, which halts that column for good. The
    # cumulative sum down the column is therefore the time at which
    # each cell would be reached, and selectivity and etch stops both
    # fall out of it without a special case.
    solid = wafer.grid != VACUUM
    with np.errstate(divide="ignore"):
        cost = np.where(solid,
                        np.where(rates > 0.0, wafer.dz / rates, np.inf),
                        0.0)
    reached_at = np.cumsum(cost, axis=0)
    wafer.grid[solid & (reached_at <= anisotropy * time_min)] = VACUUM

    # --- isotropic component ------------------------------------------
    # Whatever time was not directional removes material equally in all
    # directions. A solid cell goes if it lies within its own removal
    # depth of any open space -- the mirror image of conformal
    # deposition, which fills every empty cell within reach of a solid.
    isotropic_time = (1.0 - anisotropy) * time_min
    if isotropic_time > 0.0:
        still_solid = wafer.grid != VACUUM
        if still_solid.any() and not still_solid.all():
            distance = distance_transform_edt(
                still_solid, sampling=(wafer.dz, wafer.dx)
            )
            depth = rates * isotropic_time
            wafer.grid[still_solid & (depth > 0.0) & (distance <= depth)] = VACUUM

    wafer.log(
        "etch",
        chemistry=chemistry_name,
        time_min=float(time_min),
        anisotropy=float(anisotropy),
        rates_nm_min={int(k): float(v) for k, v in rates_nm_min.items()},
    )
    return wafer
