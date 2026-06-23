"""Unit tests for operational clothes washer / dishwasher label derivation."""

from pathlib import Path

import pytest

from h2k_hpxml.components.baseload_appliances import (
    CW_LITERS_PER_CYCLE,
    DW_LITERS_PER_CYCLE,
    GAL_PER_L,
    calc_actual_clothes_washer_usgpd,
    calc_actual_dishwasher_usgpd,
    calc_required_clothes_washer_specs,
    calc_required_dishwasher_specs,
)
from h2k_hpxml.core import h2k_parser as h2k
from h2k_hpxml.core.model import ModelData
from h2k_hpxml.core.processors.building import process_building_details
from h2k_hpxml.core.template_loader import load_and_parse_templates


class _OperatingModelData(ModelData):
    def __init__(self, parameters):
        super().__init__()
        self._parameters = parameters

    def get_operating_condition(self, key, default=None):
        return self._parameters.get(key, default)

    def set_building_details(self, details):
        self.building_details.update(details)


@pytest.mark.parametrize(
    ("num_occupants", "cw_cycles", "dw_cycles", "cw_energy", "dw_energy"),
    [
        (3, 1.9, 1.37, 148, 260),
        (4, 1.88, 1.03, 197, 260),
    ],
)
def test_operational_label_derivation_matches_volume_and_energy_targets(
    num_occupants, cw_cycles, dw_cycles, cw_energy, dw_energy
):
    h2k_dict = {
        "HouseFile": {
            "House": {
                "BaseLoads": {
                    "WaterUsage": {
                        "ClothesWasher": {"@numberPerOccupantPerWeek": cw_cycles},
                        "DishWasher": {"@numberPerOccupantPerWeek": dw_cycles},
                    }
                }
            }
        }
    }
    model_data = _OperatingModelData(
        {
            "annual_elec_clothes_washer": cw_energy,
            "annual_elec_dishwasher": dw_energy,
        }
    )

    cw_target = (CW_LITERS_PER_CYCLE / GAL_PER_L) * cw_cycles * num_occupants / 7
    dw_target = (DW_LITERS_PER_CYCLE / GAL_PER_L) * dw_cycles * num_occupants / 7

    cw_specs = calc_required_clothes_washer_specs(h2k_dict, num_occupants, model_data)
    dw_specs = calc_required_dishwasher_specs(h2k_dict, num_occupants, model_data)

    cw_gpd = model_data.get_building_detail("clothes_washer_usgpd")
    dw_gpd = model_data.get_building_detail("dishwasher_usgpd")

    assert cw_gpd == pytest.approx(cw_target, rel=1e-9)
    assert dw_gpd == pytest.approx(dw_target, rel=1e-9)

    cw_label_kwh, cw_label_cycles, cw_capacity, cw_ghwc, cw_elec_rate, cw_gas_rate, _ = cw_specs
    dw_label_kwh, dw_label_cycles, dw_capacity, dw_ghwc = dw_specs

    assert calc_actual_clothes_washer_usgpd(
        num_occupants,
        cw_label_cycles / 52,
        cw_ghwc,
        cw_gas_rate,
        cw_elec_rate,
        cw_capacity,
        cw_label_kwh,
    ) == pytest.approx(cw_target, rel=1e-9)

    assert calc_actual_dishwasher_usgpd(
        num_occupants,
        dw_label_cycles / 52,
        dw_ghwc,
        1.09,
        dw_label_kwh,
        0.12,
        dw_capacity,
    ) == pytest.approx(dw_target, rel=1e-9)


def test_example_h2k_files_set_numberof_residents_for_operational_path():
    example = Path(__file__).resolve().parents[2] / "src" / "h2k_hpxml" / "examples" / "WizardHouse.h2k"
    h2k_str = example.read_text(encoding="utf-8")
    h2k_dict, hpxml_dict = load_and_parse_templates(h2k_str)
    model_data = ModelData()
    process_building_details(h2k_dict, hpxml_dict, model_data, "SOC")

    occupancy = hpxml_dict["HPXML"]["Building"]["BuildingDetails"]["BuildingSummary"][
        "BuildingOccupancy"
    ]
    assert "NumberofResidents" in occupancy
    assert occupancy["NumberofResidents"] == model_data.get_operating_condition("num_occupants")

    cw_cycles = h2k.get_number_field(h2k_dict, "clothes_washer_cycles_per_occ_week")
    calc_required_clothes_washer_specs(h2k_dict, occupancy["NumberofResidents"], model_data)
    assert model_data.get_building_detail("clothes_washer_usgpd") > 0
