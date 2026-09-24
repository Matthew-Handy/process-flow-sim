"""Tests for chemical-mechanical polishing."""

import numpy as np
import pytest

from procsim.cmp import degree_of_planarization, polish
from procsim.deposition import deposit
from procsim.materials import SI3N4, SILICON, SIO2, VACUUM
from procsim.wafer import Wafer


@pytest.fixture
def flat():
    w = Wafer()
    deposit(w, SIO2, thickness_nm=400.0)
    return w


@pytest.fixture
def stepped():
    """A 300 nm step: conformal oxide over a trench in the substrate."""
    w = Wafer()
    w.grid[500:650, 300:700] = VACUUM
    deposit(w, SIO2, thickness_nm=400.0, conformal=True)
    return w


# --- removal ----------------------------------------------------------

def test_flat_wafer_loses_exactly_the_removal(flat):
    before = flat.surface_profile_nm()[0]
    polish(flat, removal_nm=150.0)
    assert flat.surface_profile_nm()[0] == pytest.approx(before - 150.0,
                                                         abs=flat.dz)


def test_target_height_and_removal_agree(stepped):
    twin = stepped.copy()
    polish(stepped, removal_nm=300.0, planarity=1.0)
    polish(twin, target_z_nm=stepped.surface_profile_nm().max(), planarity=1.0)
    assert np.array_equal(stepped.grid, twin.grid)


def test_polishing_never_adds_material(stepped):
    before = (stepped.grid != VACUUM).sum()
    polish(stepped, removal_nm=100.0, planarity=1.0)
    assert (stepped.grid != VACUUM).sum() <= before


def test_zero_removal_changes_nothing(stepped):
    before = stepped.grid.copy()
    polish(stepped, removal_nm=0.0, planarity=1.0)
    assert np.array_equal(stepped.grid, before)


# --- planarisation ----------------------------------------------------

def test_full_planarity_flattens_when_removal_exceeds_the_step(stepped):
    polish(stepped, removal_nm=350.0, planarity=1.0)
    assert np.ptp(stepped.surface_profile_nm()) == 0.0


def test_zero_planarity_preserves_topography(stepped):
    before = np.ptp(stepped.surface_profile_nm())
    polish(stepped, removal_nm=150.0, planarity=0.0)
    assert np.ptp(stepped.surface_profile_nm()) == pytest.approx(
        before, abs=stepped.dz
    )


def test_partial_planarity_halves_the_step(stepped):
    before = np.ptp(stepped.surface_profile_nm())
    polish(stepped, removal_nm=150.0, planarity=0.5)
    assert np.ptp(stepped.surface_profile_nm()) == pytest.approx(
        before / 2.0, abs=2 * stepped.dz
    )


def test_planarisation_is_limited_by_how_much_you_remove(stepped):
    """You cannot planarise a 300 nm step by removing only 100 nm."""
    before = stepped.surface_profile_nm()
    polish(stepped, removal_nm=100.0, planarity=1.0)
    after = stepped.surface_profile_nm()
    assert degree_of_planarization(before, after) == pytest.approx(1 / 3,
                                                                   abs=0.02)


def test_dop_of_an_already_flat_wafer_is_one(flat):
    before = flat.surface_profile_nm()
    polish(flat, removal_nm=100.0)
    assert degree_of_planarization(before, flat.surface_profile_nm()) == 1.0


# --- polish stop ------------------------------------------------------

def test_stop_layer_survives_a_long_polish():
    w = Wafer()
    w.grid[480:500, :] = SI3N4
    deposit(w, SIO2, thickness_nm=500.0, conformal=True)
    polish(w, removal_nm=2000.0, planarity=1.0, stop_on=SI3N4)
    assert w.thickness_of(SI3N4).max() == 40.0
    assert w.thickness_of(SIO2).max() == 0.0


def test_sti_fill_lands_flush_with_the_nitride_pad():
    w = Wafer()
    w.grid[500:650, 300:700] = VACUUM       # trench
    w.grid[480:500, :] = SI3N4              # pad on the field
    w.grid[480:500, 300:700] = VACUUM       # open over the trench
    deposit(w, SIO2, thickness_nm=500.0, conformal=True)
    polish(w, removal_nm=600.0, planarity=1.0, stop_on=SI3N4)

    assert w.thickness_of(SI3N4).max() == 40.0
    assert w.thickness_of(SIO2)[50] == 0.0        # field cleared
    assert w.thickness_of(SIO2)[500] > 300.0      # trench still full
    assert np.ptp(w.surface_profile_nm()) == 0.0  # and it is flat


def test_stop_material_that_is_absent_is_ignored(flat):
    polish(flat, removal_nm=100.0, planarity=1.0, stop_on=SI3N4)
    assert flat.thickness_of(SIO2)[0] == pytest.approx(300.0, abs=flat.dz)


# --- interface --------------------------------------------------------

def test_both_or_neither_target_raises(flat):
    with pytest.raises(ValueError, match="exactly one"):
        polish(flat)
    with pytest.raises(ValueError, match="exactly one"):
        polish(flat, removal_nm=10.0, target_z_nm=0.0)


def test_target_above_the_surface_raises(flat):
    with pytest.raises(ValueError, match="above the current surface"):
        polish(flat, target_z_nm=10_000.0)


def test_planarity_out_of_range_raises(flat):
    with pytest.raises(ValueError, match="planarity"):
        polish(flat, removal_nm=10.0, planarity=2.0)


def test_negative_removal_raises(flat):
    with pytest.raises(ValueError, match="negative"):
        polish(flat, removal_nm=-10.0)


def test_history_records_what_was_achieved(stepped):
    polish(stepped, removal_nm=350.0, planarity=1.0)
    entry = stepped.history[-1]
    assert entry["step"] == "cmp"
    assert entry["params"]["removal_nm"] == 350.0
    assert entry["params"]["planarization_achieved"] == pytest.approx(1.0)
