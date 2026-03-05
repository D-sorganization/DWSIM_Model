import logging
from dwsim_model.core import FlowsheetBuilder, get_automation
from dwsim_model.constants import COMPOUNDS_STANDARD, DEFAULT_PROPERTY_PACKAGE

logger = logging.getLogger(__name__)


class GasifierStandaloneFlowsheet:
    """
    Standalone Gasifier unit operation model using Downdraft concept.
    Designed for isolated testing and execution, following DbC and DRY.
    """

    def __init__(self, compound_set: list | None = None):
        self.automation = get_automation()
        self.builder = FlowsheetBuilder()
        self._is_built = False
        # Allow callers to pass a custom compound list; defaults to shared standard
        self._compounds = compound_set or COMPOUNDS_STANDARD

    def setup_thermo(self):
        """Configure standard PR properties and required components."""
        for c in self._compounds:
            self.builder.add_compound(c)
        self.builder.add_property_package(DEFAULT_PROPERTY_PACKAGE)

    def build_flowsheet(self):
        """Constructs an isolated Gasifier block with its immediate streams."""
        b = self.builder
        # Inputs
        feed_biomass = b.add_object("MaterialStream", "Gasifier_Biomass_Feed", 0, 300)
        feed_solids_g = b.add_object("MaterialStream", "Gasifier_Solids_Feed", 0, 350)
        feed_ox_g = b.add_object("MaterialStream", "Gasifier_Oxygen_Feed", 0, 400)
        feed_st_g = b.add_object("MaterialStream", "Gasifier_Steam_Feed", 0, 450)

        gas_in_mixer = b.add_object("Mixer", "Gasifier_Inlet_Mixer", 100, 350)
        gas_mixed_feed = b.add_object("MaterialStream", "Gasifier_Mixed_Feed", 150, 350)

        # Thermal Sequence
        gas_cooler_loss = b.add_object("Cooler", "Gasifier_Heat_Loss_Block", 250, 350)
        gas_feed_2 = b.add_object("MaterialStream", "Gasifier_Feed_PostLoss", 310, 350)
        gas_cooler_jacket = b.add_object("Cooler", "Gasifier_Heat_To_Jacket", 400, 350)
        gas_feed_final = b.add_object("MaterialStream", "Gasifier_Feed_Final", 460, 350)

        # Reactor
        gasifier = b.add_object("RCT_Conversion", "Downdraft_Gasifier", 550, 350)

        # Outputs
        s1 = b.add_object("MaterialStream", "Syngas_Pre_PEM", 650, 350)
        gasifier_glass = b.add_object("MaterialStream", "Gasifier_Glass_Out", 650, 450)

        # Energy / Cooling
        e_gas_loss = b.add_object("EnergyStream", "E_Gasifier_HeatLoss", 250, 250)
        gas_cw_in = b.add_object(
            "MaterialStream", "Gasifier_Cooling_Water_In", 350, 500
        )
        gas_cw_out = b.add_object(
            "MaterialStream", "Gasifier_Cooling_Steam_Out", 500, 500
        )
        gas_cooler = b.add_object("Heater", "Gasifier_Cooling_Jacket", 400, 450)
        e_gas_flux = b.add_object("EnergyStream", "E_Gasifier_Flux_to_CW", 400, 400)

        def safe_connect(src, tgt, p1=0, p2=0):
            try:
                b.connect(src, tgt, p1, p2)
            except Exception as e:
                logger.warning(f"Failed to connect isolated node: {src} -> {tgt} ({e})")

        # Map topology
        safe_connect(feed_biomass, gas_in_mixer, 0, 0)
        safe_connect(feed_solids_g, gas_in_mixer, 0, 1)
        safe_connect(feed_ox_g, gas_in_mixer, 0, 2)
        safe_connect(feed_st_g, gas_in_mixer, 0, 3)
        safe_connect(gas_in_mixer, gas_mixed_feed, 0, 0)

        safe_connect(gas_mixed_feed, gas_cooler_loss, 0, 0)
        safe_connect(gas_cooler_loss, gas_feed_2, 0, 0)
        safe_connect(gas_cooler_loss, e_gas_loss, 0, 0)

        safe_connect(gas_feed_2, gas_cooler_jacket, 0, 0)
        safe_connect(gas_cooler_jacket, gas_feed_final, 0, 0)
        safe_connect(gas_cooler_jacket, e_gas_flux, 0, 0)

        safe_connect(gas_cw_in, gas_cooler, 0, 0)
        safe_connect(gas_cooler, gas_cw_out, 0, 0)
        safe_connect(gas_cooler, e_gas_flux, 0, 0)

        safe_connect(gas_feed_final, gasifier, 0, 0)
        safe_connect(gasifier, s1, 0, 0)
        safe_connect(gasifier, gasifier_glass, 1, 0)

        # Basic reaction property assignment
        ops = self.builder.operations
        if "Downdraft_Gasifier" in ops:
            # DbC Placeholder: Users modify kinetics here.
            pass

        self._is_built = True

    def calculate(self):
        assert self._is_built, "Flowsheet must be built before calculating."
        self.builder.calculate()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Building Standalone Gasifier...")
    m = GasifierStandaloneFlowsheet()
    m.setup_thermo()
    m.build_flowsheet()
    m.calculate()
    m.builder.save("Standalone_Gasifier.dwxml")
