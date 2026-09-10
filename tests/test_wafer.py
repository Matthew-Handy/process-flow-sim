"""
Tests for the wafer state.
Run from the project root with: pytest
"""

import numpy as np
import pytest

from procsim.materials import SILICON, SIO2, VACUUM
from procsim.wafer import Wafer

@pytest.fixture
def w():
    """A fresh default wafer for each test"""
    return Wafer()

def test_fresh_surface_is_flat_at_zero(w):
    profile = w.surface_profile_nm()
    assert profile.shape == (w.n_cols, )
    assert np.allclose(profile, 0.0, atol=w.dz)

def test_substrate_thickness_matches_request(w):
    assert np.allclose(w.thickness_of(SILICON), w.substrate_thickness_nm)

def test_no_oxide_on_a_fresh_wafer(w):
    assert np.all(w.thickness_of(SIO2) == 0)

@pytest.mark.parametrize("row", [0, 1, 499, 500, 749])
def test_row_z_round_trip(w, row):
    assert w.row_of_z(w.z_of_row(row)) == row

def test_empty_column_reports_no_surface(w):
    w.grid[:, 0] = VACUUM
    assert w.surface_rows()[0] == w.n_rows
    assert w.surface_rows()[1] == int(w.headroom_nm / w.dz)

def test_copy_is_independent(w):
    clone = w.copy()
    clone.grid[:, :] = VACUUM
    clone.log("etch_everything")
    assert np.all(w.thickness_of(SILICON) == w.substrate_thickness_nm)
    assert w.history == []