import logging
from enum import Enum
from dwsim_model.core import FlowsheetBuilder

logger = logging.getLogger(__name__)


class ReactorMode(str, Enum):
    MIXED = "mixed"  # Gasifier: Conversion, PEM: Equilibrium, TRC: PFR
    KINETIC = "kinetic"  # All: PFR
    EQUILIBRIUM = "equilibrium"  # All: Equilibrium
    CONVERSION = "conversion"  # All: Conversion
    CUSTOM = "custom"  # Defined via a dictionary


class GasificationFlowsheet:
    """
    Constructs the standard Gasification Process model in DWSIM.

    Includes:
    - Downdraft Gasifier (RCT_Conversion)
    - PEM (RCT_Equilibrium)
    - TRC (RCT_PFR)
    - Quench Vessel (Mixer for evaporative cooling via water injection)
    - Baghouse (SolidSeparator)
    - Scrubber (ComponentSeparator)
    - Blower/Compressor (Compressor)
    """

    def __init__(
        self,
        builder: FlowsheetBuilder | None = None,
        mode: ReactorMode | str = ReactorMode.MIXED,
        custom_reactors: dict[str, str] | None = None,
    ):
        self.builder = builder or FlowsheetBuilder()
        self.mode = ReactorMode(mode)
        self.custom_reactors = custom_reactors or {}
        self._is_built = False

    def _get_reactor_types(self) -> dict[str, str]:
        """Returns the DWSIM ObjectType string for each reactor based on mode."""
        if self.mode == ReactorMode.CUSTOM:
            return {
                "gasifier": self.custom_reactors.get("gasifier", "RCT_Conversion"),
                "pem": self.custom_reactors.get("pem", "RCT_Equilibrium"),
                "trc": self.custom_reactors.get("trc", "RCT_PFR"),
            }
        elif self.mode == ReactorMode.KINETIC:
            return {"gasifier": "RCT_PFR", "pem": "RCT_PFR", "trc": "RCT_PFR"}
        elif self.mode == ReactorMode.EQUILIBRIUM:
            return {
                "gasifier": "RCT_Equilibrium",
                "pem": "RCT_Equilibrium",
                "trc": "RCT_Equilibrium",
            }
        elif self.mode == ReactorMode.CONVERSION:
            return {
                "gasifier": "RCT_Conversion",
                "pem": "RCT_Conversion",
                "trc": "RCT_Conversion",
            }
        else:  # MIXED
            return {
                "gasifier": "RCT_Conversion",
                "pem": "RCT_Equilibrium",
                "trc": "RCT_PFR",
            }

    def setup_thermo(self) -> None:
        """Sets up thermodynamics and compounds. DbC: Builder must exist."""
        assert self.builder is not None, "Builder instance required"

        # Adding typical syngas compounds
        compounds = [
            "Carbon monoxide",
            "Hydrogen",
            "Carbon dioxide",
            "Methane",
            "Water",
            "Nitrogen",
            "Oxygen",
            "Helium",  # Using Helium as placeholder for solids (e.g., char/ash)
        ]
        for c in compounds:
            self.builder.add_compound(c)

        self.builder.add_property_package("Peng-Robinson (PR)")

    def build_flowsheet(self) -> None:
        """Constructs the unit operations and streams."""
        if self._is_built:
            return

        b = self.builder
        rtypes = self._get_reactor_types()

        # 1. Downdraft Gasifier
        feed = b.add_object("MaterialStream", "Biomass_Feed")
        gasifier = b.add_object(rtypes["gasifier"], "Downdraft_Gasifier")

        # 2. PEM
        s1 = b.add_object("MaterialStream", "Syngas_Pre_PEM")
        pem = b.add_object(rtypes["pem"], "PEM_Reactor")

        # 3. TRC
        s2 = b.add_object("MaterialStream", "Syngas_Pre_TRC")
        trc = b.add_object(rtypes["trc"], "TRC_Reactor")

        # 4. Quench Vessel (Evaporative Cooling via Mixer)
        s3 = b.add_object("MaterialStream", "Syngas_Pre_Quench")
        water_inj = b.add_object(
            "MaterialStream", "Quench_Water_Injection"
        )  # Water supply
        quench = b.add_object("Mixer", "Quench_Vessel")

        # 5. Baghouse
        s4 = b.add_object("MaterialStream", "Syngas_Pre_Baghouse")
        baghouse = b.add_object("SolidSeparator", "Baghouse")

        # 6. Scrubber
        s5 = b.add_object("MaterialStream", "Clean_Syngas_Pre_Scrub")
        scrubber = b.add_object("ComponentSeparator", "Scrubber")

        # 7. Blower
        s6 = b.add_object("MaterialStream", "Scrubbed_Syngas")
        blower = b.add_object("Compressor", "Blower")

        # Product Stream
        product = b.add_object("MaterialStream", "Final_Syngas")

        # Energy streams
        e_gas = b.add_object("EnergyStream", "E_Gasifier")
        e_pem = b.add_object("EnergyStream", "E_PEM")
        e_trc = b.add_object("EnergyStream", "E_TRC")
        e_blower = b.add_object("EnergyStream", "E_Blower")

        # Connection Mapping
        try:
            b.connect(feed, gasifier, 0, 0)
            b.connect(gasifier, s1, 0, 0)

            b.connect(s1, pem, 0, 0)
            b.connect(pem, s2, 0, 0)

            b.connect(s2, trc, 0, 0)
            b.connect(trc, s3, 0, 0)

            # Quench is a mixer
            b.connect(s3, quench, 0, 0)
            b.connect(water_inj, quench, 0, 1)  # Port 1 is second inlet
            b.connect(quench, s4, 0, 0)

            b.connect(s4, baghouse, 0, 0)
            b.connect(baghouse, s5, 0, 0)

            b.connect(s5, scrubber, 0, 0)
            b.connect(scrubber, s6, 0, 0)

            b.connect(s6, blower, 0, 0)
            b.connect(blower, product, 0, 0)

            # Energy
            b.connect(e_gas, gasifier, 0, 0)
            b.connect(e_pem, pem, 0, 0)
            b.connect(e_trc, trc, 0, 0)
            b.connect(e_blower, blower, 0, 0)
        except Exception as e:
            logger.warning(f"Connection layout partial due to: {e}")

        # Configure detailed models after layout
        self._configure_reactors()

        self._is_built = True

    def _configure_reactors(self) -> None:
        """
        Configures the advanced parameters for the reactor vessels.
        Documentation for Users:
        To modify the reactors, access `builder.operations["ReactorName"]` properties directly.
        """
        ops = self.builder.operations

        # 1. Configure Downdraft Gasifier (RCT_Conversion)
        # Note: In a UI, users should set stoichiometric conversion factors mapping biomass to syngas
        if "Downdraft_Gasifier" in ops:
            ops["Downdraft_Gasifier"]
            # To-Do: Programmatically add specific Conversion Reactions via DWSIM Simulation Data
            # e.g., Biomass -> a*CO + b*H2 + c*CH4 + d*CO2
            pass

        # 2. Configure PEM (RCT_Equilibrium)
        # Note: Operates via Minimization of Gibbs Free Energy or distinct Equilibrium Reactions
        if "PEM_Reactor" in ops:
            ops["PEM_Reactor"]
            # To-Do: Configure isothermal operation and add WGS/Methanation equilibrium reactions.
            pass

        # 3. Configure TRC (RCT_PFR)
        if "TRC_Reactor" in ops:
            ops["TRC_Reactor"]
            # Set default volume/length (requires DWSIM property setters mapped to .NET types)
            # trc.Volume = 2.0  # m3
            # trc.Length = 5.0  # m
            pass

    def run(self):
        """Execute the configured flowsheet."""
        assert self._is_built, "Flowsheet must be built before running"
        self.builder.calculate()
