"""
Tests for depositions
"""

import numpy as np
import pytest

from procsim.deposition import deposit
from procsim.materials import SILICON, SIO2, VACUUM
from procsim.wafer import Wafer

@pytest.fixture
def w():
    return Wafer()

@pytest.fixture 
def trench ():
    """A wafer with 20nm wide, 300nm deep trench carved by hand"""
    t = Wafer()
    t.grid[500:650, 400:500] = VACUUM
    return t

@pytest.mark.parametrize("conformal", [True, False])
def test_thickness_matches_request(w, conformal):
    deposit(w, SIO2, thickness_nm=200.0, conformal=conformal)
    assert np.allclose(w.thickness_of(SIO2), 200.0)

def test_rate_times_time_sets_thickness(w):
    deposit(w, SIO2, rate_nm_s=2.5, time_s=80.0, conformal=False)
    assert np.allclose(w.thickness_of(SIO2), 200.0)

def test_flat_wafer_cannot_tell_the_two_apart():
    a, b = Wafer(), Wafer()
    deposit(a, SIO2, thickness_nm=100.0, conformal=True)
    deposit(b, SIO2, thickness_nm=100.0, conformal=False)
    assert np.array_equal(a.grid, b.grid)

def test_deposition_does_not_consume_substrate(w):
    deposit(w, SIO2, thickness_nm=200.0)
    assert np.allclose(w.thickness_of(SILICON), w.substrate_thickness_nm)

def test_conformal_coats_sidewalls_and_directional_does_not(trench):
    directional = trench.copy()
    deposit(trench, SIO2, thickness_nm=40.0, conformal=True)
    deposit(directional, SIO2, thickness_nm=40.0, conformal=False)

    wall_col = 402
    assert (trench.grid[:, wall_col] == SIO2).sum() > 100
    assert (directional.grid[:, wall_col] == SIO2).sum() == 20

def test_surface_rises_by_the_film_thickness(w):
    before = w.surface_profile_nm()
    deposit(w, SIO2, thickness_nm=150.0, conformal=False)
    after = w.surface_profile_nm()
    assert np.allclose(after - before, 150.0)

def test_too_much_film_raises(w):
    with pytest.raises(ValueError, match="headroom"):
        deposit(w, SIO2, thickness_nm=2000.0, conformal=False)

def test_missing_rate_or_time_raises(w):
    with pytest.raises(ValueError):
        deposit(w, SIO2, rate_nm_s=2.0)

def test_history_records_the_step(w):
    deposit(w, SIO2, rate_nm_s=2.0, time_s=100.0, conformal=False)
    assert len(w.history) == 1
    entry = w.history[0]
    assert entry["step"] == "deposition"
    assert entry["params"]["rate_nm_s"] == 2.0
    assert entry["params"]["time_s"] == 100.0
