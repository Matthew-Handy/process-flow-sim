"""Tests for thermal oxidation."""

import numpy as np
import pytest

from procsim.materials import SI3N4, SILICON, SIO2
from procsim.oxidation import (
    SI_CONSUMED_FRACTION,
    oxide_thickness,
    oxidize,
    rate_constants,
)
from procsim.wafer import Wafer


@pytest.fixture
def w():
    return Wafer()


#the model against published data

@pytest.mark.parametrize(
    "ambient, temperature_c, time_min, expected_nm",
    [
        ("wet", 1000, 60, 390.0),
        ("dry", 1000, 60, 58.0),
    ],
)
def test_matches_published_deal_grove(ambient, temperature_c, time_min, expected_nm):
    x = oxide_thickness(temperature_c, time_min, ambient)
    assert x == pytest.approx(expected_nm, rel=0.05)


def test_thin_oxide_is_linear_in_time():
    b, a = rate_constants(1000, "wet")
    t = 0.1
    assert oxide_thickness(1000, t, "wet") == pytest.approx((b / a) * t, rel=0.01)


def test_thick_oxide_is_parabolic_in_time():
    b, _ = rate_constants(1000, "wet")
    t = 1e6
    assert oxide_thickness(1000, t, "wet") == pytest.approx(np.sqrt(b * t), rel=0.01)


def test_wet_is_faster_than_dry():
    assert oxide_thickness(1000, 60, "wet") > 5 * oxide_thickness(1000, 60, "dry")


def test_hotter_grows_more():
    assert oxide_thickness(1100, 60, "wet") > oxide_thickness(1000, 60, "wet")


def test_existing_oxide_slows_growth():
    bare = oxide_thickness(1000, 60, "wet", x_initial_nm=0.0)
    coated = oxide_thickness(1000, 60, "wet", x_initial_nm=300.0)
    assert coated - 300.0 < bare


def test_unknown_ambient_raises():
    with pytest.raises(ValueError, match="dry.*wet"):
        oxide_thickness(1000, 60, "plasma")


#the model on the grid

def test_grid_growth_matches_the_model(w):
    predicted = oxide_thickness(1000, 60, "wet")
    oxidize(w, temperature_c=1000, time_min=60, ambient="wet")
    assert np.allclose(w.thickness_of(SIO2), predicted, atol=w.dz)


def test_silicon_is_consumed_at_the_right_ratio(w):
    before = w.thickness_of(SILICON)[0]
    oxidize(w, temperature_c=1000, time_min=60, ambient="wet")
    grown = w.thickness_of(SIO2)[0]
    consumed = before - w.thickness_of(SILICON)[0]
    assert consumed / grown == pytest.approx(SI_CONSUMED_FRACTION, abs=0.02)


def test_surface_rises_by_the_unconsumed_fraction(w):
    before = w.surface_profile_nm()[0]
    oxidize(w, temperature_c=1000, time_min=60, ambient="wet")
    grown = w.thickness_of(SIO2)[0]
    risen = w.surface_profile_nm()[0] - before
    assert risen / grown == pytest.approx(1.0 - SI_CONSUMED_FRACTION, abs=0.02)


def test_nitride_masks_oxidation(w):
    w.grid[480:500, 400:600] = SI3N4
    oxidize(w, temperature_c=1000, time_min=60, ambient="wet")
    assert w.thickness_of(SIO2)[500] == 0.0
    assert w.thickness_of(SIO2)[100] > 300.0


def test_second_oxidation_grows_less(w):
    oxidize(w, temperature_c=1000, time_min=60, ambient="wet")
    first = w.thickness_of(SIO2)[0]
    oxidize(w, temperature_c=1000, time_min=60, ambient="wet")
    second = w.thickness_of(SIO2)[0] - first
    assert second < first


def test_history_records_the_step(w):
    oxidize(w, temperature_c=1000, time_min=60, ambient="wet")
    entry = w.history[-1]
    assert entry["step"] == "oxidation"
    assert entry["params"]["temperature_c"] == 1000.0
    assert entry["params"]["ambient"] == "wet"