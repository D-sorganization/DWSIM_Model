from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import dwsim_model.core

# Only mock if clr cannot be imported or runtime fails (e.g. non-Windows or mono not installed)
try:
    import clr
except (ModuleNotFoundError, RuntimeError):
    # Mock get_automation directly to return MagicMocks
    def mock_get_automation(dwsim_path=""):
        interf = MagicMock()
        sim = MagicMock()
        interf.CreateFlowsheet.return_value = sim

        interf.AvailablePropertyPackages = {"Peng-Robinson (PR)": MagicMock()}

        sim.SelectedCompounds.Values = []

        def add_compound(name):
            mock_c = MagicMock()
            mock_c.Name = name
            sim.SelectedCompounds.Values.append(mock_c)
            return mock_c

        sim.AddCompound.side_effect = add_compound

        sim.PropertyPackages = MagicMock()
        sim.PropertyPackages.__len__.return_value = 1
        sim.PropertyPackages.Values = []

        def add_property_package(pack):
            sim.PropertyPackages.Values.append(pack)
            return pack

        sim.AddPropertyPackage.side_effect = add_property_package

        # ObjectType mock
        class ObjectType:
            MaterialStream = "MaterialStream"
            EnergyStream = "EnergyStream"
            RCT_Conversion = "RCT_Conversion"
            RCT_Equilibrium = "RCT_Equilibrium"
            RCT_PFR = "RCT_PFR"
            Vessel = "Vessel"
            Mixer = "Mixer"
            SolidSeparator = "SolidSeparator"
            ComponentSeparator = "ComponentSeparator"
            Compressor = "Compressor"

        return interf, ObjectType

    dwsim_model.core.get_automation = mock_get_automation
