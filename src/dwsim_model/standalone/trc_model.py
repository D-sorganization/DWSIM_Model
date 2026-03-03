import logging
from dwsim_model.core import FlowsheetBuilder, get_automation

logger = logging.getLogger(__name__)


class TRCStandaloneFlowsheet:
    """
    Standalone Thermal Reduction Chamber (TRC) model.
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
        """Constructs an isolated TRC block."""
        b = self.builder
        # Inputs
        feed_syngas = b.add_object("MaterialStream", "TRC_Syngas_Inlet", 1450, 150)
        feed_solids = b.add_object("MaterialStream", "TRC_Solids_Feed", 1450, 200)
        feed_ox = b.add_object("MaterialStream", "TRC_Oxygen_Feed", 1450, 250)
        feed_st = b.add_object("MaterialStream", "TRC_Steam_Feed", 1450, 300)

        in_mixer = b.add_object("Mixer", "TRC_Inlet_Mixer", 1550, 350)
        mixed_feed = b.add_object("MaterialStream", "TRC_Mixed_Feed", 1600, 350)

        # Thermal Stages
        cooler_loss = b.add_object("Cooler", "TRC_Heat_Loss_Block", 1700, 350)
        feed_final = b.add_object("MaterialStream", "TRC_Feed_Final", 1760, 350)

        # Reactor
        trc = b.add_object("RCT_PFR", "TRC_Reactor", 1850, 350)

        # Outputs
        s3 = b.add_object("MaterialStream", "Syngas_Pre_Quench", 1950, 350)

        # Energy
        e_loss = b.add_object("EnergyStream", "E_TRC_HeatLoss", 1700, 250)

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

        safe_connect(mixed_feed, cooler_loss, 0, 0)
        safe_connect(cooler_loss, feed_final, 0, 0)
        safe_connect(cooler_loss, e_loss, 0, 0)

        safe_connect(feed_final, trc, 0, 0)
        safe_connect(trc, s3, 0, 0)

        self._is_built = True

    def calculate(self):
        assert self._is_built, "Flowsheet must be built before calculating."
        self.builder.calculate()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Building Standalone TRC...")
    m = TRCStandaloneFlowsheet()
    m.setup_thermo()
    m.build_flowsheet()
    m.calculate()
    m.builder.save("Standalone_TRC.dwxml")
