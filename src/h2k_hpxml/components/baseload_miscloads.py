def get_plug_loads(h2k_dict, model_data):
    daily_elec_other_electrical = model_data.get_operating_condition("daily_elec_other_electrical")
    daily_elec_common_space = model_data.get_operating_condition("daily_elec_common_space")
    hpxml_plug_loads = {
        "PlugLoad": [
            {
                "SystemIdentifier": {"@id": "PlugLoad1"},
                "PlugLoadType": "other",
                "Load": {
                    "Units": "kWh/year",
                    "Value": daily_elec_other_electrical * 365,
                },
            },
        ]
    }

    if daily_elec_common_space > 0:
        hpxml_plug_loads["PlugLoad"].append(
            {
                "SystemIdentifier": {"@id": "PlugLoad2"},
                "PlugLoadType": "other",
                "Load": {
                    "Units": "kWh/year",
                    "Value": daily_elec_common_space * 365,
                },
            }
        )

    return hpxml_plug_loads


def get_fuel_loads(h2k_dict, model_data):
    return {
        "FuelLoad": [
            {
                # "SystemIdentifier": {"@id": "PlugLoad1"},
                # "PlugLoadType": "TV other",
                # "Load": {"Units": "kWh/year", "Value": "620.0"},
            },
        ]
    }
