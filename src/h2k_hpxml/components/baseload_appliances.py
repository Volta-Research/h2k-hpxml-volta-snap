from ..core import h2k_parser as h2k

# ANSI/RESNET 301-2019 operational constants (match OS-HPXML hotwater_appliances.rb)
GAL_PER_L = 3.785411784
CW_LITERS_PER_CYCLE = 54
DW_LITERS_PER_CYCLE = 19


def get_appliances(h2k_dict, model_data=None):
    res_facility_type = model_data.get_building_detail("res_facility_type")

    num_occupants = model_data.get_operating_condition("num_occupants")

    annual_elec_refrigerator = model_data.get_operating_condition("annual_elec_refrigerator")

    try:
        dryer_exhaust = h2k.get_number_field(h2k_dict, "dryer_exhaust_flowrate")
    except (KeyError, TypeError, ValueError):
        dryer_exhaust = 0


    (
        cw_label_energy_rating,
        cw_label_cycles_year,
        cw_capacity,
        cw_ghwc,
        cw_elec_rate,
        cw_gas_rate,
        cw_imef,
    ) = calc_required_clothes_washer_specs(h2k_dict, num_occupants, model_data)

    (
        dw_label_energy_rating,
        dw_label_cycles_year,
        dw_capacity,
        dw_ghwc,
    ) = calc_required_dishwasher_specs(h2k_dict, num_occupants, model_data)

    dryer_combined_energy_factor = calc_required_dryer_specs(
        res_facility_type,
        num_occupants,
        model_data,
        cw_label_energy_rating,
        cw_capacity,
        cw_imef,
    )

    range_usage_multiplier = calc_required_range_specs(res_facility_type, num_occupants, model_data)

    # TODO: Other hot water consumption: 2.92 L/week
    # TODO: Shower/Bathroom faucet consumption

    hpxml_appliances = {
        "ClothesWasher": {
            "SystemIdentifier": {"@id": "ClothesWasher1"},
            "Location": "conditioned space",
            "IntegratedModifiedEnergyFactor": cw_imef,
            "RatedAnnualkWh": cw_label_energy_rating,
            "LabelElectricRate": cw_elec_rate,
            "LabelGasRate": cw_gas_rate,
            "LabelAnnualGasCost": cw_ghwc,
            "LabelUsage": cw_label_cycles_year / 52,
            "Capacity": cw_capacity,
        },
        "ClothesDryer": {
            "SystemIdentifier": {"@id": "ClothesDryer1"},
            "Location": "conditioned space",
            "FuelType": "electricity",
            "CombinedEnergyFactor": dryer_combined_energy_factor,
            "Vented": True,
            "VentedFlowRate": dryer_exhaust or 80.52,  # default
        },
        "Dishwasher": {
            "SystemIdentifier": {"@id": "Dishwasher1"},
            "Location": "conditioned space",
            "RatedAnnualkWh": dw_label_energy_rating,
            "PlaceSettingCapacity": dw_capacity,
            "LabelElectricRate": 0.12,  # Defaults used
            "LabelGasRate": 1.09,  # Defaults used
            "LabelAnnualGasCost": dw_ghwc,
            "LabelUsage": dw_label_cycles_year / 52,
        },
        "Refrigerator": {
            "SystemIdentifier": {"@id": "Refrigerator1"},
            "Location": "conditioned space",
            "RatedAnnualkWh": annual_elec_refrigerator,
            "PrimaryIndicator": True,
        },
        "CookingRange": {
            "SystemIdentifier": {"@id": "CookingRange1"},
            "Location": "conditioned space",
            "FuelType": "electricity",
            "IsInduction": False,
            "extension": {"UsageMultiplier": range_usage_multiplier},
        },
        "Oven": {"SystemIdentifier": {"@id": "Oven1"}, "IsConvection": False},
    }

    return hpxml_appliances


# from HPXML-OS workflow
# Defaults.rb in HPXML-OS workflow
# def self.get_equivalent_nbeds_for_operational_calculation(hpxml_bldg)
#     n_occs = hpxml_bldg.building_occupancy.number_of_residents
#     unit_type = hpxml_bldg.building_construction.residential_facility_type
#     # Relations below come from 2020 RECS weighted regressions between NBEDS and NHSHLDMEM (sample weights = NWEIGHT)
#     case unit_type
#     when HPXML::ResidentialTypeApartment
#       return -1.36 + 1.49 * n_occs
#     when HPXML::ResidentialTypeSFA
#       return -1.98 + 1.89 * n_occs
#     when HPXML::ResidentialTypeSFD
#       return -2.19 + 2.08 * n_occs
#     when HPXML::ResidentialTypeManufactured
#       return -1.26 + 1.61 * n_occs
#     else
#       fail "Unexpected residential facility type: #{unit_type}."
#     end
#   end

def get_adjusted_num_bedrooms(res_facility_type, num_occupants):
    if res_facility_type == "single-family detached":
        return -2.19 + 2.08 * num_occupants
    elif res_facility_type == "single-family attached":
        return -1.98 + 1.89 * num_occupants
    elif res_facility_type == "manufactured home":
        return -1.26 + 1.61 * num_occupants
    elif res_facility_type == "apartment unit":
        return -1.36 + 1.49 * num_occupants
    else:
        print("Unexpected residential facility type: ", res_facility_type)
        return num_occupants


def _warn_invalid_appliance_label(model_data, appliance_name, message):
    model_data.add_warning_message(
        {
            "message": (
                f"{appliance_name} label inputs could not be derived analytically: {message}. "
                "HPXML appliance hot water or energy use may not match H2K targets."
            )
        }
    )


def calc_required_clothes_washer_specs(h2k_dict, num_occupants, model_data):
    """Derive ENERGY GUIDE label fields for the OS-HPXML operational (n_occ) clothes washer path."""
    annual_elec_clothes_washer = model_data.get_operating_condition("annual_elec_clothes_washer")
    clothes_washer_cycles_per_occ_week = h2k.get_number_field(
        h2k_dict, "clothes_washer_cycles_per_occ_week"
    )

    volume_target = (
        (CW_LITERS_PER_CYCLE / GAL_PER_L)
        * clothes_washer_cycles_per_occ_week
        * num_occupants
        / 7
    )
    energy_target = annual_elec_clothes_washer

    washer_capacity = 3
    ghwc = 60
    cw_imef = 0.9
    elec_rate = 0.3
    gas_rate = 1.09
    gas_h2o = 0.3914
    elec_h2o = 0.0178

    scy = 123.0 + 61.0 * num_occupants
    acy = scy * ((3.0 * 2.08 + 1.59) / (washer_capacity * 2.08 + 1.59))

    denom = elec_rate * gas_h2o / gas_rate - elec_h2o
    c0 = ghwc * gas_h2o / gas_rate / denom
    c1 = elec_h2o / denom

    k_volume = volume_target * 365.0 / (elec_h2o * acy)
    label_energy_rating = (k_volume + c0) / (1.0 + c1)

    cw_appl = c0 - c1 * label_energy_rating
    if label_energy_rating < 0 or energy_target <= 0 or cw_appl <= 0:
        _warn_invalid_appliance_label(
            model_data,
            "Clothes washer",
            "non-positive rated kWh, energy target, or label cycle energy",
        )
        label_cycles_year = clothes_washer_cycles_per_occ_week * 52.0 * num_occupants
    else:
        label_cycles_year = cw_appl * acy / energy_target

    actual_clothes_washer_gpd = calc_actual_clothes_washer_usgpd(
        num_occupants,
        label_cycles_year / 52,
        ghwc,
        gas_rate,
        elec_rate,
        washer_capacity,
        label_energy_rating,
    )

    model_data.set_building_details(
        {
            "clothes_washer_usgpd": actual_clothes_washer_gpd,
        }
    )

    return (
        label_energy_rating,
        label_cycles_year,
        washer_capacity,
        ghwc,
        elec_rate,
        gas_rate,
        cw_imef,
    )


def calc_actual_clothes_washer_usgpd(
    num_occupants,
    label_usage,
    label_annual_gas_cost,
    label_gas_rate,
    label_electric_rate,
    capacity,
    rated_annual_kwh,
):
    gas_h20 = 0.3914  # (gal/cyc) per (therm/y)
    elec_h20 = 0.0178  # (gal/cyc) per (kWh/y)

    scy = 123.0 + 61.0 * num_occupants
    acy = scy * ((3.0 * 2.08 + 1.59) / (capacity * 2.08 + 1.59))
    cw_appl = (
        label_annual_gas_cost * gas_h20 / label_gas_rate
        - (rated_annual_kwh * label_electric_rate) * elec_h20 / label_electric_rate
    ) / (label_electric_rate * gas_h20 / label_gas_rate - elec_h20)

    gpd = (rated_annual_kwh - cw_appl) * elec_h20 * acy / 365.0

    return gpd


def calc_required_dishwasher_specs(h2k_dict, num_occupants, model_data):
    """Derive ENERGY GUIDE label fields for the OS-HPXML operational (n_occ) dishwasher path."""
    annual_elec_dishwasher = model_data.get_operating_condition("annual_elec_dishwasher")
    dishwasher_cycles_per_occ_week = h2k.get_number_field(
        h2k_dict, "dishwasher_cycles_per_occ_week"
    )

    volume_target = (
        (DW_LITERS_PER_CYCLE / GAL_PER_L)
        * dishwasher_cycles_per_occ_week
        * num_occupants
        / 7
    )
    energy_target = annual_elec_dishwasher

    dishwasher_capacity = 12
    ghwc = 22.23
    elec_price = 0.12
    gas_price = 1.09

    scy = 91.0 + 30.0 * num_occupants
    dwcpy = scy * (12.0 / dishwasher_capacity)

    a_denom = elec_price * 0.5497 / gas_price - 0.02504
    c0 = ghwc * 0.5497 / gas_price / a_denom
    c1 = 0.02504 / a_denom

    k_volume = volume_target * 365.0 / (0.02504 * dwcpy)
    label_energy_rating = (k_volume + c0) / (1.0 + c1)

    kwh_label = c0 - c1 * label_energy_rating
    if label_energy_rating < 0 or energy_target <= 0 or kwh_label <= 0:
        _warn_invalid_appliance_label(
            model_data,
            "Dishwasher",
            "non-positive rated kWh, energy target, or label cycle energy",
        )
        label_cycles_year = dishwasher_cycles_per_occ_week * 52.0 * num_occupants
    else:
        label_cycles_year = kwh_label * dwcpy / energy_target

    actual_dishwasher_usgpd = calc_actual_dishwasher_usgpd(
        num_occupants,
        label_cycles_year / 52,
        ghwc,
        gas_price,  # Default from above
        label_energy_rating,
        elec_price,  # Default from above
        dishwasher_capacity,
    )

    model_data.set_building_details(
        {
            "dishwasher_usgpd": actual_dishwasher_usgpd,
        }
    )

    return label_energy_rating, label_cycles_year, dishwasher_capacity, ghwc


def calc_actual_dishwasher_usgpd(
    num_occupants,
    label_usage,
    label_annual_gas_cost,
    label_gas_rate,
    rated_annual_kwh,
    label_electric_rate,
    place_setting_capacity,
):
    lcy = label_usage * 52.0
    kwh_per_cyc = (
        (
            label_annual_gas_cost * 0.5497 / label_gas_rate
            - rated_annual_kwh * label_electric_rate * 0.02504 / label_electric_rate
        )
        / (label_electric_rate * 0.5497 / label_gas_rate - 0.02504)
    ) / lcy

    scy = 91.0 + 30.0 * num_occupants
    dwcpy = scy * (12.0 / place_setting_capacity)

    gpd = (rated_annual_kwh - kwh_per_cyc * lcy) * 0.02504 * dwcpy / 365.0

    return gpd


def calc_required_dryer_specs(
    res_facility_type,
    num_occupants,
    model_data,
    cw_label_energy_rating,
    cw_capacity,
    cw_imef,
):
    adjusted_bedrooms = get_adjusted_num_bedrooms(res_facility_type, num_occupants)
    annual_elec_clothes_dryer = model_data.get_operating_condition("annual_elec_clothes_dryer")

    energy_target = annual_elec_clothes_dryer

    rmc = (0.97 * (cw_capacity / cw_imef) - cw_label_energy_rating / 312.0) / (
        (2.0104 * cw_capacity + 1.4242) * 0.455
    ) + 0.04
    acy = (164.0 + 46.5 * adjusted_bedrooms) * ((3.0 * 2.08 + 1.59) / (cw_capacity * 2.08 + 1.59))

    dryer_combined_energy_factor = ((100 * (rmc - 0.04)) / 55.5) * (8.45 / energy_target) * acy

    return dryer_combined_energy_factor


def calc_required_range_specs(res_facility_type, num_occupants, model_data):
    adjusted_bedrooms = get_adjusted_num_bedrooms(res_facility_type, num_occupants)
    annual_elec_range = model_data.get_operating_condition("annual_elec_range")

    target_energy = annual_elec_range

    usage_multiplier = target_energy / (331 + 39.0 * adjusted_bedrooms)

    return usage_multiplier
