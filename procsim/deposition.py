"""
Deposition: adding materials onto the wafer
Thickness is set by rate x time. two limiting cases are modelled:
    conformal: CVD/ALD-like. The film grows to the same thickness on every exposed surface 
               including vertical sidewalls
    directional: PVD/evaporation-like. Material arrives from straight above, so upward-facing
                 surfaces are coated and sidewalls are not
Real processes fall between the two; the parameter describing where is step coverage, 
sidewall thickness divided by field thickness
"""

import numpy as np
from scipy.ndimage import distance_transform_edt
from procsim.materials import VACUUM

def deposit(wafer, material, *, thickness_nm=None, rate_nm_s=None, time_s=None, conformal=True):
    """Deposit 'material' onto 'wafer'. modifies the wafer in place"""
    if thickness_nm is None:
        if rate_nm_s is None or time_s is None:
            raise ValueError("give thickness_nm or both rate_nm_s and time_s")
        thickness_nm = rate_nm_s * time_s

    if thickness_nm <= 0:
        raise ValueError(f"thickness must be positive, got {thickness_nm}")

    if conformal:
        _deposit_conformal(wafer, material, thickness_nm)
    else:
        _deposit_directional(wafer, material, thickness_nm)

    wafer.log("deposition", material=int(material), thickness_nm=float(thickness_nm), rate_nm_s=rate_nm_s, time_s=time_s, conformal=conformal,)
    return wafer

def _deposit_directional(wafer, material, thickness_nm):
    """LOS deposition: fill straight down from above"""
    n_add = wafer.n_rows_for(thickness_nm)
    if n_add == 0:
        return

    surf = wafer.surface_rows()
    if (surf - n_add).min() < 0:
        raise ValueError("not enough headroom for this deposition; "
                         "increase headroom_nm when building the wafer")

    rows = np.arange(wafer.n_rows)[:, None]
    top = (surf - n_add)[None, :]
    mask = (rows >= top) & (rows < surf[None, :])
    wafer.grid[mask] = material

def _deposit_conformal(wafer, material, thickness_nm):
    """
    Isotropic growth: every exposed surface advances by thickness_nm. 
    assuming the film reaches *every* open cell within range
    """
    occupied = wafer.grid !=VACUUM
    if not occupied.any():
        return
    dist = distance_transform_edt(~occupied, sampling=(wafer.dz, wafer.dx))

    new_film = (dist > 0) & (dist <= thickness_nm)
    if new_film[0, :].any():
        raise ValueError("not enough headroom for this deposition; "
                         "increase headroom_nm when building the wafer")
    wafer.grid[new_film] = material