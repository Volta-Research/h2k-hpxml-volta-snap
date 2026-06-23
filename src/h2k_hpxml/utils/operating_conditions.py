"""SOC/ROC operating condition parameters for H2K to HPXML translation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from ..core.model import ModelData

OperatingParameters = dict[str, Any]

SOC_HOUSE_PARAMETERS: OperatingParameters = {
    "num_occupants": 3,
    "heating_setpoint": 68,  # 20C equivalent (no setback)
    "cooling_setpoint": 77,  # 25C
    # Electrical base loads (kWh/day)
    "daily_elec_interior_lighting": 2.6,
    "daily_elec_appliances": 6.3,
    "daily_elec_other_electrical": 9.7,  # Includes freezers and microwaves
    "daily_elec_exterior_use": 0.9,
    "daily_elec_common_space": 0.0,
    "daily_elec_total": 19.5,
    # Appliance breakdown (kWh/year)
    "annual_elec_refrigerator": 639,
    "annual_elec_range": 565,
    "annual_elec_clothes_washer": 148,  # 197 * 3/4
    "annual_elec_dishwasher": 260,
    "annual_elec_clothes_dryer": 687,  # 916 * 3/4
}

# Per-unit values for MURB; scaled for whole-building or single-unit simulations.
SOC_MURB_UNIT_PARAMETERS: OperatingParameters = {
    "num_occupants": 2,
    "heating_setpoint": 68,
    "cooling_setpoint": 77,
    "daily_elec_interior_lighting": 1.7,
    "daily_elec_appliances": 5.2,
    "daily_elec_other_electrical": 4.4,
    "daily_elec_exterior_use": 0.4,
    "daily_elec_common_space_per_m2": 0.086,  # kWh/m2/day
    "daily_elec_total": 11.7,
    "annual_elec_refrigerator": 639,
    "annual_elec_range": 565,
    "annual_elec_clothes_washer": 98.5,  # 197 * 2/4
    "annual_elec_dishwasher": 130,
    "annual_elec_clothes_dryer": 458,  # 916 * 2/4
}

# ROC adjustments — placeholders for future implementation.
# Amount of electrical base load if ROC is applied
# All in kWh/day of NEW TOTAL LOAD (not reduction)
ROC_ELECTRICAL_REDUCTION = {
    "interior_lighting_25_75": 1.6,  # kWh/day new total (25%-75% LED)
    "interior_lighting_over_75": 0.6,  # kWh/day new total (>75% LED)
}

# amount of hot water reduction from SOC if ROC is applied
# All in US Gal/day reduction
ROC_HOT_WATER_REDUCTION = {
    "low_flow_showers": 5.0,  # US Gal/day reduction
    "low_flow_bathroom_faucets": 2.6,
    "clothes_washer": 4.8,
    "dishwasher": 0.8,
}

VALID_OPERATING_CONDITIONS = ("SOC", "ROC")


def get_soc_house_parameters() -> OperatingParameters:
    """Return SOC parameters for a single-family house (3 occupants)."""
    return dict(SOC_HOUSE_PARAMETERS)


def get_soc_murb_unit_parameters(
    num_units: int, common_space_area: float = 0.0
) -> OperatingParameters:
    """Return SOC parameters scaled for a MURB simulation."""
    base = SOC_MURB_UNIT_PARAMETERS
    num_units = max(int(num_units), 1)
    common_space_load = common_space_area * base["daily_elec_common_space_per_m2"]
    daily_unit_load = (
        base["daily_elec_interior_lighting"]
        + base["daily_elec_appliances"]
        + base["daily_elec_other_electrical"]
        + base["daily_elec_exterior_use"]
    ) * num_units

    return {
        "num_occupants": num_units * base["num_occupants"],
        "heating_setpoint": base["heating_setpoint"],
        "cooling_setpoint": base["cooling_setpoint"],
        "daily_elec_interior_lighting": base["daily_elec_interior_lighting"] * num_units,
        "daily_elec_appliances": base["daily_elec_appliances"] * num_units,
        "daily_elec_other_electrical": base["daily_elec_other_electrical"] * num_units,
        "daily_elec_exterior_use": base["daily_elec_exterior_use"] * num_units,
        "daily_elec_common_space": common_space_load,
        "daily_elec_total": daily_unit_load + common_space_load,
        "annual_elec_refrigerator": base["annual_elec_refrigerator"] * num_units,
        "annual_elec_range": base["annual_elec_range"] * num_units,
        "annual_elec_clothes_washer": base["annual_elec_clothes_washer"] * num_units,
        "annual_elec_dishwasher": base["annual_elec_dishwasher"] * num_units,
        "annual_elec_clothes_dryer": base["annual_elec_clothes_dryer"] * num_units,
    }


def get_soc_parameters(
    building_type: str, num_units: int = 1, common_space_area: float = 0.0
) -> OperatingParameters:
    """Resolve SOC parameters from building type and unit count."""
    if building_type == "house":
        return get_soc_house_parameters()
    return get_soc_murb_unit_parameters(num_units, common_space_area)


def apply_roc_adjustments(soc_parameters: OperatingParameters) -> OperatingParameters:
    """
    Apply ROC modifications to SOC base parameters.

    Placeholder: returns SOC values unchanged until ROC reduction logic is defined.
    """
    adjusted = dict(soc_parameters)
    # TODO: Apply ROC_ELECTRICAL_REDUCTION to daily lighting loads.
    # TODO: Apply ROC_HOT_WATER_REDUCTION to hot water consumption fields.
    _ = (ROC_ELECTRICAL_REDUCTION, ROC_HOT_WATER_REDUCTION)
    return adjusted


def resolve_operating_parameters(
    operating_condition: str,
    building_type: str,
    num_units: int = 1,
    common_space_area: float = 0.0,
) -> OperatingParameters:
    """Resolve final operating parameters for the requested condition."""
    mode = operating_condition.upper()
    if mode not in VALID_OPERATING_CONDITIONS:
        raise ValueError(
            f"Invalid operating condition: {operating_condition}. "
            f"Must be one of {VALID_OPERATING_CONDITIONS}"
        )

    soc_parameters = get_soc_parameters(building_type, num_units, common_space_area)
    if mode == "ROC":
        return apply_roc_adjustments(soc_parameters)
    return soc_parameters


def _resolve_murb_unit_count(building_type: str, building_details: dict[str, Any]) -> int:
    if building_type == "house":
        return 1
    if building_type == "single-murb":
        return 1
    return int(building_details.get("res_units") or 1)


def apply_operating_conditions(model_data: ModelData, operating_condition: str = "SOC") -> None:
    """
    Populate model_data with operating condition parameters.

    Must be called after building type and MURB unit details are set on model_data.
    """
    building_details = model_data.building_details
    building_type = building_details.get("building_type", "house")
    num_units = _resolve_murb_unit_count(building_type, building_details)
    common_space_area = float(building_details.get("common_space_area") or 0.0) / 10.7639 #This was converted to ft2 in building_details, convert it back

    parameters = resolve_operating_parameters(
        operating_condition,
        building_type,
        num_units,
        common_space_area,
    )

    model_data.set_operating_conditions(operating_condition.upper(), parameters)
    model_data.set_building_details(
        {
            "num_occupants": parameters["num_occupants"],
            "operating_condition": operating_condition.upper(),
            "murb_units": num_units,
        }
    )
