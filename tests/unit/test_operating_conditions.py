"""Tests for operating condition parameter resolution."""

import pytest

from h2k_hpxml.core.model import ModelData
from h2k_hpxml.utils.operating_conditions import apply_operating_conditions
from h2k_hpxml.utils.operating_conditions import get_soc_house_parameters
from h2k_hpxml.utils.operating_conditions import get_soc_murb_unit_parameters
from h2k_hpxml.utils.operating_conditions import resolve_operating_parameters


def test_soc_house_parameters():
    params = get_soc_house_parameters()
    assert params["num_occupants"] == 3
    assert params["daily_elec_total"] == 19.5
    assert params["annual_elec_clothes_dryer"] == 687


def test_soc_murb_parameters_scales_with_units():
    params = get_soc_murb_unit_parameters(num_units=4, common_space_area=100.0)
    assert params["num_occupants"] == 8
    assert params["daily_elec_interior_lighting"] == pytest.approx(6.8)
    assert params["daily_elec_common_space"] == pytest.approx(8.6)
    assert params["annual_elec_clothes_dryer"] == pytest.approx(1832.0)


def test_apply_operating_conditions_house():
    model_data = ModelData()
    model_data.set_building_details({"building_type": "house"})

    apply_operating_conditions(model_data, "SOC")

    assert model_data.get_operating_condition_mode() == "SOC"
    assert model_data.get_operating_condition("num_occupants") == 3
    assert model_data.get_building_detail("num_occupants") == 3


def test_apply_operating_conditions_whole_murb():
    model_data = ModelData()
    model_data.set_building_details(
        {
            "building_type": "whole-murb",
            "res_units": 10,
            "common_space_area": 50.0,
        }
    )

    apply_operating_conditions(model_data, "SOC")

    assert model_data.get_operating_condition("num_occupants") == 20
    assert model_data.get_building_detail("murb_units") == 10


def test_roc_placeholder_returns_soc_values():
    soc = resolve_operating_parameters("SOC", "house")
    roc = resolve_operating_parameters("ROC", "house")
    assert roc == soc


def test_invalid_operating_condition_raises():
    with pytest.raises(ValueError, match="Invalid operating condition"):
        resolve_operating_parameters("HOC", "house")
