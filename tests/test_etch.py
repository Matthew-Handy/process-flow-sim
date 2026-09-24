"""Tests for etching."""

import numpy as np
import pytest

from procsim.deposition import deposit
from procsim.etch import CHEMISTRIES, etch, selectivity
from procsim.lithography import develop, expose, spin_coat
from procsim.materials import PHOTORESIST, SILICON, SIO2, VACUUM
from procsim.wafer import Wafer


@pytest.fixture
def blanket():
    """200 nm of unmasked oxide on silicon."""
    w = Wafer()
    deposit(w, SIO2, thickness_nm=200.0)
    return w


@pytest.fixture
def masked():
    """200 nm oxide, half of it covered by developed resist."""
    w = Wafer()
    deposit(w, SIO2, thickness_nm=200.0)
    spin_coat(w, thickness_nm=300.0)
    expose(w, dose_mj_cm2=120.0, clear_regions=[(0.0, 1000.0)])
    develop(w, dose_to_clear=50.0, contrast=3.0)
    return w


def width_nm(wafer, material, row):
    """Total width of `material` in one row."""
    return float((wafer.grid[row] == material).sum()) * wafer.dx


# --- selectivity ------------------------------------------------------

def test_selectivity_ratio_matches_the_rate_table():
    assert selectivity("CHF3_O2", SIO2, SILICON) == pytest.approx(10.0)


def test_selectivity_is_infinite_when_the_other_is_untouched():
    assert selectivity("BOE", SIO2, SILICON) == np.inf


def test_selectivity_is_zero_when_the_target_is_untouched():
    assert selectivity("O2_ash", SIO2, SILICON) == 0.0


# --- vertical removal -------------------------------------------------

def test_removal_depth_is_rate_times_time(blanket):
    etch(blanket, rates_nm_min={SIO2: 20.0}, time_min=5.0, anisotropy=1.0)
    assert np.allclose(blanket.thickness_of(SIO2), 100.0, atol=blanket.dz)


def test_zero_time_changes_nothing(blanket):
    before = blanket.grid.copy()
    etch(blanket, chemistry="CHF3_O2", time_min=0.0)
    assert np.array_equal(blanket.grid, before)


def test_unlisted_material_is_an_etch_stop(blanket):
    """BOE clears the oxide and then stops dead on the silicon."""
    silicon_before = blanket.thickness_of(SILICON)[0]
    etch(blanket, chemistry="BOE", time_min=60.0)
    assert blanket.thickness_of(SIO2)[0] == 0.0
    assert blanket.thickness_of(SILICON)[0] == silicon_before


def test_a_slow_material_brakes_the_etch():
    """Silicon under oxide slows a chemistry that prefers oxide 10:1."""
    w = Wafer()
    deposit(w, SIO2, thickness_nm=200.0)
    etch(w, chemistry="CHF3_O2", time_min=10.0, anisotropy=1.0)
    assert w.thickness_of(SIO2)[0] == 0.0
    # 200 nm of oxide takes 4.4 min; the remaining 5.6 min attacks silicon
    # at 4.5 nm/min, so roughly 25 nm of it goes.
    lost = w.substrate_thickness_nm - w.thickness_of(SILICON)[0]
    assert 10.0 < lost < 45.0


def test_resist_masks_the_film_underneath(masked):
    etch(masked, chemistry="CHF3_O2", time_min=5.0, anisotropy=1.0)
    assert masked.thickness_of(SIO2)[:500].max() == 0.0     # opened
    assert masked.thickness_of(SIO2)[600:].min() == 200.0   # protected


def test_the_mask_is_itself_consumed(masked):
    before = masked.thickness_of(PHOTORESIST).max()
    etch(masked, chemistry="CHF3_O2", time_min=5.0, anisotropy=1.0)
    after = masked.thickness_of(PHOTORESIST).max()
    assert 0.0 < after < before


# --- directionality ---------------------------------------------------

def test_fully_directional_etch_transfers_the_mask_width(masked):
    """At anisotropy 1 the oxide line comes out the width of the mask."""
    mask_width = width_nm(masked, PHOTORESIST, masked.row_of_z(350.0))
    etch(masked, chemistry="CHF3_O2", time_min=5.0, anisotropy=1.0)
    oxide_width = width_nm(masked, SIO2, masked.row_of_z(20.0))
    assert oxide_width == pytest.approx(mask_width, abs=4 * masked.dx)


def test_isotropic_etch_undercuts_the_mask(masked):
    """At anisotropy 0 the line comes out narrower than the mask that made it."""
    mask_width = width_nm(masked, PHOTORESIST, masked.row_of_z(350.0))
    etch(masked, chemistry="CHF3_O2", time_min=5.0, anisotropy=0.0)
    oxide_width = width_nm(masked, SIO2, masked.row_of_z(20.0))
    assert oxide_width < mask_width - 50.0


def test_undercut_grows_as_anisotropy_falls():
    """Less directional etching leaves less material behind, monotonically."""
    remaining = []
    for anisotropy in (1.0, 0.7, 0.3):
        w = Wafer()
        deposit(w, SIO2, thickness_nm=200.0)
        spin_coat(w, thickness_nm=300.0)
        expose(w, dose_mj_cm2=120.0, clear_regions=[(0.0, 1000.0)])
        develop(w, dose_to_clear=50.0, contrast=3.0)
        etch(w, chemistry="CHF3_O2", time_min=5.0, anisotropy=anisotropy)
        remaining.append(int((w.grid == SIO2).sum()))
    assert remaining[0] > remaining[1] > remaining[2]


# --- interface --------------------------------------------------------

def test_both_or_neither_input_raises(blanket):
    with pytest.raises(ValueError, match="exactly one"):
        etch(blanket, time_min=1.0)
    with pytest.raises(ValueError, match="exactly one"):
        etch(blanket, time_min=1.0, chemistry="BOE", rates_nm_min={SIO2: 1.0})


def test_anisotropy_out_of_range_raises(blanket):
    with pytest.raises(ValueError, match="anisotropy"):
        etch(blanket, chemistry="BOE", time_min=1.0, anisotropy=1.5)


def test_negative_rate_raises(blanket):
    with pytest.raises(ValueError, match="negative"):
        etch(blanket, rates_nm_min={SIO2: -5.0}, time_min=1.0)


def test_resist_strip_leaves_everything_else(masked):
    oxide_before = masked.thickness_of(SIO2).copy()
    etch(masked, chemistry="O2_ash", time_min=5.0)
    assert masked.thickness_of(PHOTORESIST).max() == 0.0
    assert np.array_equal(masked.thickness_of(SIO2), oxide_before)


def test_history_records_the_chemistry(blanket):
    etch(blanket, chemistry="CHF3_O2", time_min=2.0)
    entry = blanket.history[-1]
    assert entry["step"] == "etch"
    assert entry["params"]["chemistry"] == "CHF3/O2"
    assert entry["params"]["time_min"] == 2.0
    assert entry["params"]["anisotropy"] == pytest.approx(0.95)
