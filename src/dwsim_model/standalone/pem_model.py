import logging
from dwsim_model.core import FlowsheetBuilder, get_automation

logger = logging.getLogger(__name__)


class PEMStandaloneFlowsheet:
    """
    Standalone Plasma Entrained Melting (PEM) model.
    Designed for isolated testing and configuration (DbC, DRY).
    """

    def __init__(self):
        self.automation = get_automation()
        self.builder = FlowsheetBuilder()
        self._is_built = False

    def setup_thermo(self):
        """Configure standard PR properties and required components."""
        compounds = [
            "Carbon monoxide",
            "Hydrogen",
            "Carbon dioxide",
            "Methane",
            "Water",
            "Nitrogen",
            "Oxygen",
            "Helium",
        ]
        for c in compounds:
            self.builder.add_compound(c)
        self.builder.add_property_package("Peng-Robinson (PR)")

    def build_flowsheet(self):
        """Constructs an isolated PEM block."""
        b = self.builder
        # Inputs
        feed_syngas = b.add_object("MaterialStream", "PEM_Syngas_Inlet", 650, 150)
        feed_solids = b.add_object("MaterialStream", "PEM_Solids_Feed", 650, 200)
        feed_ox = b.add_object("MaterialStream", "PEM_Oxygen_Feed", 650, 250)
        feed_st = b.add_object("MaterialStream", "PEM_Steam_Feed", 650, 300)

        in_mixer = b.add_object("Mixer", "PEM_Inlet_Mixer", 750, 350)
        mixed_feed = b.add_object("MaterialStream", "PEM_Mixed_Feed", 800, 350)

        # Thermal Stages
        heater_ac = b.add_object("Heater", "PEM_AC_Block", 900, 350)
        feed_2 = b.add_object("MaterialStream", "PEM_Feed_PostAC", 960, 350)
        heater_dc = b.add_object("Heater", "PEM_DC_Block", 1050, 350)
        feed_3 = b.add_object("MaterialStream", "PEM_Feed_PostDC", 1110, 350)
        cooler_loss = b.add_object("Cooler", "PEM_Heat_Loss_Block", 1200, 350)
        feed_final = b.add_object("MaterialStream", "PEM_Feed_Final", 1260, 350)

        # Reactor
        pem = b.add_object("RCT_Equilibrium", "PEM_Reactor", 1350, 350)

        # Outputs
        s2 = b.add_object("MaterialStream", "Syngas_Pre_TRC", 1450, 350)
        pem_glass = b.add_object("MaterialStream", "PEM_Glass_Out", 1450, 450)

        # Energy
        e_ac = b.add_object("EnergyStream", "E_PEM_AC_Power", 900, 250)
        e_dc = b.add_object("EnergyStream", "E_PEM_DC_Power", 1050, 250)
        e_loss = b.add_object("EnergyStream", "E_PEM_HeatLoss", 1200, 250)

        def safe_connect(src, tgt, p1=0, p2=0):
            try:
                b.connect(src, tgt, p1, p2)
            except Exception as e:
                logger.warning(f"Failed to connect isolated node: {src} -> {tgt} ({e})")

        # Map topology
        safe_connect(feed_syngas, in_mixer, 0, 0)
        safe_connect(feed_solids, in_mixer, 0, 1)
        safe_connect(feed_ox, in_mixer, 0, 2)
        safe_connect(feed_st, in_mixer, 0, 3)
        safe_connect(in_mixer, mixed_feed, 0, 0)

        safe_connect(mixed_feed, heater_ac, 0, 0)
        safe_connect(heater_ac, feed_2, 0, 0)
        safe_connect(heater_ac, e_ac, 0, 0)

        safe_connect(feed_2, heater_dc, 0, 0)
        safe_connect(heater_dc, feed_3, 0, 0)
        safe_connect(heater_dc, e_dc, 0, 0)

        safe_connect(feed_3, cooler_loss, 0, 0)
        safe_connect(cooler_loss, feed_final, 0, 0)
        safe_connect(cooler_loss, e_loss, 0, 0)

        safe_connect(feed_final, pem, 0, 0)
        safe_connect(pem, s2, 0, 0)
        safe_connect(pem, pem_glass, 1, 0)

        self._is_built = True

    def calculate(self):
        # AUTO-FIXED: Replaced assert with if-raise to prevent byte-code optimization removal
        if not self._is_built:
            raise RuntimeError("Flowsheet must be built before calculating.")
        self.builder.calculate()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Building Standalone PEM...")
    m = PEMStandaloneFlowsheet()
    m.setup_thermo()
    m.build_flowsheet()
    m.calculate()
    m.builder.save("Standalone_PEM.dwxml")
