"""Tests for lithography: coat, expose, develop."""

import numpy as np
import pytest

from procsim.lithography import develop, expose, resist_remaining, spin_coat
from procsim.materials import PHOTORESIST, VACUUM
from procsim.wafer import Wafer


@pytest.fixture
def w():
    return Wafer()


@pytest.fixture
def stepped():
    """A wafer with a 200 nm deep trench across the left half."""
    s = Wafer()
    s.grid[500:600, 0:500] = VACUUM
    return s


#coating 

def test_coat_thickness_on_a_flat_wafer(w):
    spin_coat(w, thickness_nm=400.0)
    assert np.allclose(w.thickness_of(PHOTORESIST), 400.0)


def test_coating_planarises(stepped):
    spin_coat(stepped, thickness_nm=400.0)
    profile = stepped.surface_profile_nm()
    assert np.ptp(profile) == 0.0
    assert stepped.thickness_of(PHOTORESIST)[100] > stepped.thickness_of(PHOTORESIST)[900]


def test_non_planarising_coat_follows_topography(stepped):
    spin_coat(stepped, thickness_nm=400.0, planarize=False)
    assert np.ptp(stepped.surface_profile_nm()) > 0.0


def test_zero_thickness_coat_raises(w):
    with pytest.raises(ValueError, match="positive"):
        spin_coat(w, thickness_nm=0.0)


#exposure 

def test_mask_produces_the_right_dose_pattern(w):
    spin_coat(w, thickness_nm=400.0)
    expose(w, dose_mj_cm2=120.0, clear_regions=[(0.0, 1000.0)])
    assert np.array_equal(np.unique(w.latent_image), [0.0, 120.0])
    assert w.latent_image[:500].max() == 120.0
    assert w.latent_image[500:].max() == 0.0


def test_aerial_image_is_scaled_by_dose(w):
    spin_coat(w, thickness_nm=400.0)
    aerial = np.linspace(0.0, 1.0, w.n_cols)
    expose(w, dose_mj_cm2=100.0, aerial_image=aerial)
    assert np.allclose(w.latent_image, aerial * 100.0)


def test_both_or_neither_input_raises(w):
    with pytest.raises(ValueError, match="exactly one"):
        expose(w, dose_mj_cm2=100.0)
    with pytest.raises(ValueError, match="exactly one"):
        expose(w, dose_mj_cm2=100.0, clear_regions=[(0, 100)],
               aerial_image=np.ones(w.n_cols))


def test_wrong_length_aerial_image_raises(w):
    with pytest.raises(ValueError, match="must have"):
        expose(w, dose_mj_cm2=100.0, aerial_image=np.ones(10))


#contrast model 

def test_dose_to_clear_removes_everything():
    # Exactly at D0 the log10 lands on 1.0 only to within float precision,
    # so compare with a tolerance rather than ==.
    r = resist_remaining(50.0, dose_to_clear=50.0, contrast=3.0)
    assert r == pytest.approx(0.0, abs=1e-9)


def test_zero_dose_removes_nothing():
    assert resist_remaining(0.0, dose_to_clear=50.0, contrast=3.0) == 1.0


def test_remaining_is_monotonic_in_dose():
    doses = np.linspace(0.0, 80.0, 50)
    r = resist_remaining(doses, dose_to_clear=50.0, contrast=3.0)
    assert np.all(np.diff(r) <= 0.0)


def test_negative_tone_is_the_complement():
    doses = np.linspace(0.0, 80.0, 50)
    pos = resist_remaining(doses, dose_to_clear=50.0, contrast=3.0, tone="positive")
    neg = resist_remaining(doses, dose_to_clear=50.0, contrast=3.0, tone="negative")
    assert np.allclose(pos + neg, 1.0)


def test_higher_contrast_narrows_the_transition():
    doses = np.linspace(0.0, 80.0, 2000)
    widths = []
    for gamma in (1.5, 3.0, 10.0):
        r = resist_remaining(doses, dose_to_clear=50.0, contrast=gamma)
        widths.append(np.sum((r > 0.01) & (r < 0.99)))
    assert widths[0] > widths[1] > widths[2]


def test_bad_contrast_or_tone_raises():
    with pytest.raises(ValueError, match="contrast"):
        resist_remaining(10.0, dose_to_clear=50.0, contrast=0.0)
    with pytest.raises(ValueError, match="tone"):
        resist_remaining(10.0, dose_to_clear=50.0, contrast=3.0, tone="sideways")


#development

def test_develop_without_exposure_raises(w):
    spin_coat(w, thickness_nm=400.0)
    with pytest.raises(ValueError, match="expose"):
        develop(w)


def test_positive_tone_clears_the_exposed_regions(w):
    spin_coat(w, thickness_nm=400.0)
    expose(w, dose_mj_cm2=120.0, clear_regions=[(0.0, 1000.0)])
    develop(w, dose_to_clear=50.0, contrast=3.0, tone="positive")
    t = w.thickness_of(PHOTORESIST)
    assert np.all(t[:500] == 0.0)
    assert np.all(t[500:] == 400.0)


def test_negative_tone_inverts_the_pattern(w):
    spin_coat(w, thickness_nm=400.0)
    expose(w, dose_mj_cm2=120.0, clear_regions=[(0.0, 1000.0)])
    develop(w, dose_to_clear=50.0, contrast=3.0, tone="negative")
    t = w.thickness_of(PHOTORESIST)
    assert np.all(t[:500] == 400.0)
    assert np.all(t[500:] == 0.0)


def test_partial_dose_leaves_partial_resist(w):
    spin_coat(w, thickness_nm=400.0)
    expose(w, dose_mj_cm2=35.0, clear_regions=[(0.0, 1000.0)])
    develop(w, dose_to_clear=50.0, contrast=3.0, tone="positive")
    t = w.thickness_of(PHOTORESIST)[0]
    assert 0.0 < t < 400.0


def test_develop_consumes_the_latent_image(w):
    spin_coat(w, thickness_nm=400.0)
    expose(w, dose_mj_cm2=120.0, clear_regions=[(0.0, 1000.0)])
    develop(w)
    assert w.latent_image is None


def test_history_records_all_three_steps(w):
    spin_coat(w, thickness_nm=400.0)
    expose(w, dose_mj_cm2=120.0, clear_regions=[(0.0, 1000.0)])
    develop(w, dose_to_clear=50.0, contrast=3.0)
    assert [e["step"] for e in w.history] == ["spin_coat", "expose", "develop"]
    assert w.history[1]["params"]["dose_mj_cm2"] == 120.0
    assert w.history[2]["params"]["tone"] == "positive"