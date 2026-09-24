"""Chemical-mechanical polishing.

CMP is the only step in this simulator whose purpose is not to add or
remove a particular material, but to remove *topography*. Every other
process broadly follows the surface it is given; CMP flattens it, which
is what makes it possible to stack a dozen patterned layers without the
lithography going out of focus on the hills.

The mechanism is abrasive slurry under a polishing pad. Preston's
equation gives the local removal rate as

    MRR = K_p * P * v

with P the local pressure and v the pad-wafer relative velocity. The
planarising behaviour comes straight out of the P: the pad presses
hardest on whatever sticks up, so high features are removed faster than
low ones, and the surface converges toward flat.

Rather than simulate pad mechanics, this module exposes that outcome as
a single `planarity` knob:

    planarity = 1   perfect levelling. Material is removed down to one
                    flat plane, no matter what the topography was.
    planarity = 0   no levelling at all. Every column loses the same
                    thickness and the topography survives untouched --
                    a blanket etch-back, not a polish.

Real CMP lands in between, typically 0.6 to 0.9 over micron-scale
features, and degrades as features get wider.

Not modelled: pressure-driven dishing (wide soft regions polishing
below the plane because the pad flexes into them), erosion (dense
arrays thinning faster than isolated ones), and any dependence on
pattern density. Those are the reasons real CMP needs
dummy fill structures, and they are the natural next thing to add.
"""

import numpy as np

from procsim.materials import VACUUM


def degree_of_planarization(before_profile_nm, after_profile_nm):
    """How much of the original topography a polish removed, 0 to 1.

    Defined as 1 - (step remaining) / (step before), the standard
    figure of merit for a planarising process.
    """
    before_step = float(np.ptp(before_profile_nm))
    if before_step == 0.0:
        return 1.0
    return 1.0 - float(np.ptp(after_profile_nm)) / before_step


def polish(wafer, *, removal_nm=None, target_z_nm=None, planarity=1.0,
           stop_on=None):
    """Polish the wafer. Modifies it in place.

    Give either `removal_nm`, the amount taken off the highest point of
    the wafer, or `target_z_nm`, an absolute height to polish down to.

    `stop_on` names a material that the slurry will not cut through --
    a polish stop. Columns that reach it stop there while the rest keep
    going, which is how STI oxide fill is planarised against a nitride
    pad.
    """
    if (removal_nm is None) == (target_z_nm is None):
        raise ValueError("give exactly one of removal_nm or target_z_nm")
    if not 0.0 <= planarity <= 1.0:
        raise ValueError(f"planarity must be in [0, 1], got {planarity}")

    surface_z = wafer.surface_profile_nm()
    highest = float(surface_z.max())

    if target_z_nm is not None:
        removal_nm = highest - float(target_z_nm)
        if removal_nm < 0.0:
            raise ValueError(
                f"target_z_nm={target_z_nm} is above the current surface "
                f"at {highest} nm; polishing cannot add material"
            )
    if removal_nm < 0.0:
        raise ValueError(f"removal must not be negative, got {removal_nm}")

    # The two limiting behaviours, blended by `planarity`.
    levelled_z = np.full(wafer.n_cols, highest - removal_nm)   # one flat plane
    followed_z = surface_z - removal_nm                        # topography kept
    new_z = planarity * levelled_z + (1.0 - planarity) * followed_z

    # Polishing removes; it never deposits. A column already below the
    # target plane is simply left alone.
    new_z = np.minimum(new_z, surface_z)

    # A polish stop halts the whole polish, not one column. The pad is
    # rigid across many features, so once it rides on the stop layer
    # anywhere, removal everywhere else stops too. This is what lets STI
    # oxide fill land flush with a nitride pad instead of over-polishing
    # into the trench.
    if stop_on is not None:
        is_stop = wafer.grid == stop_on
        has_stop = is_stop.any(axis=0)
        if has_stop.any():
            stop_z = wafer.z_of_row(np.argmax(is_stop, axis=0) - 0.5)
            new_z = np.maximum(new_z, float(np.max(stop_z[has_stop])))

    cut_row = wafer.row_of_z(new_z)
    rows = np.arange(wafer.n_rows)[:, None]
    wafer.grid[rows < cut_row[None, :]] = VACUUM

    wafer.log(
        "cmp",
        removal_nm=float(removal_nm),
        planarity=float(planarity),
        stop_on=None if stop_on is None else int(stop_on),
        planarization_achieved=float(
            degree_of_planarization(surface_z, wafer.surface_profile_nm())
        ),
    )
    return wafer
