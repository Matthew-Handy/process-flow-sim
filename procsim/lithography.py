"""
Lithography: coat, expose, develop
3 seperate operations because they are 3 separate tools: a coat track, a scanner, a develop track.
"""

import numpy as np

from procsim.deposition import deposit
from procsim.materials import PHOTORESIST, VACUUM

def spin_coat(wafer, *, thickness_nm, material=PHOTORESIST, planarize=True):
    """Apply resist. Liquid resist flows, so by default it planarises"""
    if thickness_nm <= 0:
        raise ValueError(f"thickness must be positive, got {thickness_nm}")

    if not planarize:
        deposit(wafer, material, thickness_nm=thickness_nm, conformal=True)
        wafer.history[-1]["step"] = "spin_coat"
        return wafer

    surf = wafer.surface_rows()
    top_z = wafer.surface_profile_nm().max() + thickness_nm
    target_row = int(wafer.row_of_z(top_z))

    if target_row <= 0:
        raise ValueError("not enough headroom to coat this thickness")

    rows = np.arange(wafer.n_rows)[:, None]
    mask = (rows >= target_row) & (rows < surf[None, :])
    wafer.grid[mask] = material

    wafer.log("spin_coat", material=int(material), thickness_nm=float(thickness_nm), planarize = True)
    return wafer

def expose(wafer, *, dose_mj_cm2, clear_regions=None, aerial_image=None):
    """Project an image into the resist, storing the latent image"""
    if (clear_regions is None) == (aerial_image is None):
        raise ValueError("give exactly one of clear_regions or aerial_image")

    if aerial_image is not None:
        intensity = np.asarray(aerial_image, dtype=float)
        if intensity.shape != (wafer.n_cols,):
            raise ValueError(f"aerial_image must have {wafer.n_cols} points, "
                             f"got {intensity.shape}")

    else:
        x_nm = (np.arange(wafer.n_cols) + 0.5) * wafer.dx
        intensity = np.zeros(wafer.n_cols)
        for x0, x1 in clear_regions:
            intensity[(x_nm >= x0) & (x_nm < x1)] = 1.0

    wafer.latent_image = intensity * float(dose_mj_cm2)
    wafer.log("expose", dose_mj_cm2=float(dose_mj_cm2), clear_regions=clear_regions, from_aerial_image=aerial_image is not None)

    return wafer

def resist_remaining(dose, *, dose_to_clear, contrast, tone="positive"):
    """
    Fraction of resist thickness surviving development.
    Standard contrast model: a log-linear ramp between the dose where thinning starts(D1) and the
    dose to clear (D0), with 
    gamma = 1 / log10(D0 / D1)
    so as gamma approaches infinity is an ideal step function resist
    """
    if contrast <= 0:
        raise ValueError(f"contrast must be positive, got {contrast}")
    if tone not in ("positive", "negative"):
        raise ValueError(f"tone must be 'positive' or 'negative', got {tone!r}")

    d1 = dose_to_clear * 10.0 ** (-1.0 / contrast)
    safe = np.clip(np.asarray(dose, dtype=float), 1e-12, None)
    removed = np.clip(contrast * np.log10(safe / d1), 0.0, 1.0)

    return 1.0 - removed if tone == "positive" else removed

def develop(wafer, *, dose_to_clear=50.0, contrast=3.0, tone="positive"):
    """
    Dissolve resist according to the latent image
    """
    if getattr(wafer, "latent_image", None) is None:
        raise ValueError("nothing to develop: expose the wafer first")

    remaining = resist_remaining(
        wafer.latent_image, dose_to_clear=dose_to_clear, contrast=contrast, tone=tone, 
    )

    resist_thickness = wafer.thickness_of(PHOTORESIST)
    remove_nm = (1.0 - remaining) * resist_thickness
    n_remove = np.round(remove_nm / wafer.dz).astype(int)

    is_resist = wafer.grid == PHOTORESIST
    r_top = np.where(is_resist.any(axis=0), np.argmax(is_resist, axis=0), wafer.n_rows)

    rows = np.arange(wafer.n_rows)[:, None]
    strip = (rows >= r_top[None, :]) & (rows < (r_top + n_remove)[None, :])
    wafer.grid[strip] = VACUUM

    wafer.latent_image = None
    wafer.log("develop", dose_to_clear=float(dose_to_clear), contrast=float(contrast), tone=tone)

    return wafer
