import logging
from enum import Enum
from dwsim_model.core import FlowsheetBuilder
from dwsim_model.config_loader import ConfigLoader

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

        # ==========================================
        # 1. Downdraft / Pre-Gasifier
        # ==========================================
        feed_biomass = b.add_object("MaterialStream", "Gasifier_Biomass_Feed", 0, 300)
        feed_solids_g = b.add_object("MaterialStream", "Gasifier_Solids_Feed", 0, 350)
        feed_ox_g = b.add_object("MaterialStream", "Gasifier_Oxygen_Feed", 0, 400)
        feed_st_g = b.add_object("MaterialStream", "Gasifier_Steam_Feed", 0, 450)

        gas_in_mixer = b.add_object("Mixer", "Gasifier_Inlet_Mixer", 100, 350)
        gas_mixed_feed = b.add_object("MaterialStream", "Gasifier_Mixed_Feed", 150, 350)

        # Sequential Thermal Stages (Replaces Energy Mixer)
        gas_cooler_loss = b.add_object("Cooler", "Gasifier_Heat_Loss_Block", 250, 350)
        gas_feed_2 = b.add_object("MaterialStream", "Gasifier_Feed_PostLoss", 310, 350)

        gas_cooler_jacket = b.add_object("Cooler", "Gasifier_Heat_To_Jacket", 400, 350)
        gas_feed_final = b.add_object("MaterialStream", "Gasifier_Feed_Final", 460, 350)

        gasifier = b.add_object(rtypes["gasifier"], "Downdraft_Gasifier", 550, 350)

        s1 = b.add_object("MaterialStream", "Syngas_Pre_PEM", 650, 350)
        gasifier_glass = b.add_object("MaterialStream", "Gasifier_Glass_Out", 650, 450)

        # Gasifier Energy / Cooling Jacket
        e_gas_loss = b.add_object("EnergyStream", "E_Gasifier_HeatLoss", 250, 250)

        # Cooling Jacket simulated by a heater
        gas_cw_in = b.add_object(
            "MaterialStream", "Gasifier_Cooling_Water_In", 350, 500
        )
        gas_cw_out = b.add_object(
            "MaterialStream", "Gasifier_Cooling_Steam_Out", 500, 500
        )
        gas_cooler = b.add_object("Heater", "Gasifier_Cooling_Jacket", 400, 450)
        e_gas_flux = b.add_object(
            "EnergyStream", "E_Gasifier_Flux_to_CW", 400, 400
        )  # Bridge

        # ==========================================
        # 2. PEM
        # ==========================================
        feed_solids_p = b.add_object("MaterialStream", "PEM_Solids_Feed", 650, 200)
        feed_ox_p = b.add_object("MaterialStream", "PEM_Oxygen_Feed", 650, 250)
        feed_st_p = b.add_object("MaterialStream", "PEM_Steam_Feed", 650, 300)

        pem_in_mixer = b.add_object("Mixer", "PEM_Inlet_Mixer", 750, 350)
        pem_mixed_feed = b.add_object("MaterialStream", "PEM_Mixed_Feed", 800, 350)

        # Sequential Thermal Stages (Replaces Energy Mixer)
        pem_heater_ac = b.add_object("Heater", "PEM_AC_Block", 900, 350)
        pem_feed_2 = b.add_object("MaterialStream", "PEM_Feed_PostAC", 960, 350)

        pem_heater_dc = b.add_object("Heater", "PEM_DC_Block", 1050, 350)
        pem_feed_3 = b.add_object("MaterialStream", "PEM_Feed_PostDC", 1110, 350)

        pem_cooler_loss = b.add_object("Cooler", "PEM_Heat_Loss_Block", 1200, 350)
        pem_feed_final = b.add_object("MaterialStream", "PEM_Feed_Final", 1260, 350)

        pem = b.add_object(rtypes["pem"], "PEM_Reactor", 1350, 350)

        s2 = b.add_object("MaterialStream", "Syngas_Pre_TRC", 1450, 350)
        pem_glass = b.add_object("MaterialStream", "PEM_Glass_Out", 1450, 450)

        # PEM Energy
        e_pem_ac = b.add_object("EnergyStream", "E_PEM_AC_Power", 900, 250)
        e_pem_dc = b.add_object("EnergyStream", "E_PEM_DC_Power", 1050, 250)
        e_pem_loss = b.add_object("EnergyStream", "E_PEM_HeatLoss", 1200, 250)

        # ==========================================
        # 3. TRC
        # ==========================================
        feed_solids_t = b.add_object("MaterialStream", "TRC_Solids_Feed", 1450, 200)
        feed_ox_t = b.add_object("MaterialStream", "TRC_Oxygen_Feed", 1450, 250)
        feed_st_t = b.add_object("MaterialStream", "TRC_Steam_Feed", 1450, 300)

        trc_in_mixer = b.add_object("Mixer", "TRC_Inlet_Mixer", 1550, 350)
        trc_mixed_feed = b.add_object("MaterialStream", "TRC_Mixed_Feed", 1600, 350)

        # Sequential Thermal Stages (Replaces Energy Mixer)
        trc_cooler_loss = b.add_object("Cooler", "TRC_Heat_Loss_Block", 1700, 350)
        trc_feed_final = b.add_object("MaterialStream", "TRC_Feed_Final", 1760, 350)

        trc = b.add_object(rtypes["trc"], "TRC_Reactor", 1850, 350)

        s3 = b.add_object("MaterialStream", "Syngas_Pre_Quench", 1950, 350)

        # TRC Energy
        e_trc_loss = b.add_object("EnergyStream", "E_TRC_HeatLoss", 1700, 250)

        # ==========================================
        # 4. Quench Vessel
        # ==========================================
        water_inj = b.add_object("MaterialStream", "Quench_Water_Injection", 1950, 200)
        n2_inj = b.add_object("MaterialStream", "Quench_Nitrogen", 1950, 250)
        stm_inj = b.add_object("MaterialStream", "Quench_Steam", 1950, 300)

        quench = b.add_object("Mixer", "Quench_Vessel", 2100, 350)
        s4 = b.add_object("MaterialStream", "Syngas_Pre_Baghouse", 2200, 350)

        # ==========================================
        # 5. Baghouse
        # ==========================================
        baghouse = b.add_object("SolidSeparator", "Baghouse", 2350, 350)
        s5 = b.add_object("MaterialStream", "Clean_Syngas_Pre_Scrub", 2450, 350)
        baghouse_solids = b.add_object(
            "MaterialStream", "Baghouse_Solids_Out", 2450, 450
        )

        # ==========================================
        # 6. Scrubber
        # ==========================================
        scrubber = b.add_object("ComponentSeparator", "Scrubber", 2600, 350)
        s6 = b.add_object("MaterialStream", "Scrubbed_Syngas", 2700, 350)
        scrubber_blowdown = b.add_object(
            "MaterialStream", "Scrubber_Blowdown", 2700, 450
        )

        # ==========================================
        # 7. Blower
        # ==========================================
        blower = b.add_object("Compressor", "Blower", 2850, 350)
        product = b.add_object("MaterialStream", "Final_Syngas", 2950, 350)
        e_blower = b.add_object("EnergyStream", "E_Blower", 2850, 250)

        def safe_connect(src, tgt, p1=0, p2=0):
            try:
                b.connect(src, tgt, p1, p2)
            except Exception as e:
                src_name = getattr(src, "Name", str(src))
                tgt_name = getattr(tgt, "Name", str(tgt))
                logger.warning(
                    f"Failed to connect {src_name} to {tgt_name} (ports {p1}->{p2}): {e}"
                )

        # Connection Mapping
        # Gasifier Mixing
        safe_connect(feed_biomass, gas_in_mixer, 0, 0)
        safe_connect(feed_solids_g, gas_in_mixer, 0, 1)
        safe_connect(feed_ox_g, gas_in_mixer, 0, 2)
        safe_connect(feed_st_g, gas_in_mixer, 0, 3)
        safe_connect(gas_in_mixer, gas_mixed_feed, 0, 0)

        # Gasifier Thermal Sequence
        safe_connect(gas_mixed_feed, gas_cooler_loss, 0, 0)
        safe_connect(gas_cooler_loss, gas_feed_2, 0, 0)
        safe_connect(gas_cooler_loss, e_gas_loss, 0, 0)  # Cooler outputs loss energy

        safe_connect(gas_feed_2, gas_cooler_jacket, 0, 0)
        safe_connect(gas_cooler_jacket, gas_feed_final, 0, 0)
        safe_connect(gas_cooler_jacket, e_gas_flux, 0, 0)  # Cooler outputs flux

        # Cooling Jacket Water Heater (receives flux from cooler above)
        safe_connect(gas_cw_in, gas_cooler, 0, 0)
        safe_connect(gas_cooler, gas_cw_out, 0, 0)
        safe_connect(
            gas_cooler, e_gas_flux, 0, 0
        )  # Energy connects FROM unit TO stream

        # Gasifier Reactor
        safe_connect(gas_feed_final, gasifier, 0, 0)
        safe_connect(gasifier, s1, 0, 0)  # Vapor / Syngas
        safe_connect(gasifier, gasifier_glass, 1, 0)  # Liquid / Glass

        # PEM Mixing
        safe_connect(s1, pem_in_mixer, 0, 0)
        safe_connect(feed_solids_p, pem_in_mixer, 0, 1)
        safe_connect(feed_ox_p, pem_in_mixer, 0, 2)
        safe_connect(feed_st_p, pem_in_mixer, 0, 3)
        safe_connect(pem_in_mixer, pem_mixed_feed, 0, 0)

        # PEM Thermal Sequence
        safe_connect(pem_mixed_feed, pem_heater_ac, 0, 0)
        safe_connect(pem_heater_ac, pem_feed_2, 0, 0)
        safe_connect(pem_heater_ac, e_pem_ac, 0, 0)

        safe_connect(pem_feed_2, pem_heater_dc, 0, 0)
        safe_connect(pem_heater_dc, pem_feed_3, 0, 0)
        safe_connect(pem_heater_dc, e_pem_dc, 0, 0)

        safe_connect(pem_feed_3, pem_cooler_loss, 0, 0)
        safe_connect(pem_cooler_loss, pem_feed_final, 0, 0)
        safe_connect(pem_cooler_loss, e_pem_loss, 0, 0)

        # PEM Reactor
        safe_connect(pem_feed_final, pem, 0, 0)
        safe_connect(pem, s2, 0, 0)  # Vapor
        safe_connect(pem, pem_glass, 1, 0)  # Liquid / Glass

        # TRC Mixing
        safe_connect(s2, trc_in_mixer, 0, 0)
        safe_connect(feed_solids_t, trc_in_mixer, 0, 1)
        safe_connect(feed_ox_t, trc_in_mixer, 0, 2)
        safe_connect(feed_st_t, trc_in_mixer, 0, 3)
        safe_connect(trc_in_mixer, trc_mixed_feed, 0, 0)

        # TRC Thermal Sequence
        safe_connect(trc_mixed_feed, trc_cooler_loss, 0, 0)
        safe_connect(trc_cooler_loss, trc_feed_final, 0, 0)
        safe_connect(trc_cooler_loss, e_trc_loss, 0, 0)

        # TRC Reactor
        safe_connect(trc_feed_final, trc, 0, 0)
        safe_connect(trc, s3, 0, 0)  # Vapor
        # Note: A PFR only possesses 1 output port representing mixed/vapors so glass stream is not attached.

        # Quench
        safe_connect(s3, quench, 0, 0)
        safe_connect(water_inj, quench, 0, 1)
        safe_connect(n2_inj, quench, 0, 2)
        safe_connect(stm_inj, quench, 0, 3)
        safe_connect(quench, s4, 0, 0)

        # Baghouse
        safe_connect(s4, baghouse, 0, 0)
        safe_connect(baghouse, s5, 0, 0)  # Clean Vapor
        safe_connect(baghouse, baghouse_solids, 1, 0)  # Solids

        # Scrubber
        safe_connect(s5, scrubber, 0, 0)
        safe_connect(scrubber, s6, 0, 0)  # Scrubbed Vapor
        safe_connect(scrubber, scrubber_blowdown, 1, 0)  # Liquid Blowdown

        # Blower
        safe_connect(s6, blower, 0, 0)
        safe_connect(blower, product, 0, 0)
        safe_connect(e_blower, blower, 0, 1)

        # Configure detailed models after layout
        self._configure_reactors()

        # Configuration Load
        # Allows researchers to specify thermodynamic data outside of pure python
        try:
            loader = ConfigLoader()
            loader.load()
            loader.apply_to_flowsheet(self.builder, b.materials, b.energies)
        except Exception as e:
            logger.error(f"Failed to load user configuration: {e}")

        self._is_built = True

    def _configure_reactors(self) -> None:
        """
        Configures the advanced parameters for the reactor vessels.
        Documentation for Users:
        To modify the reactors, access `builder.operations["ReactorName"]` properties directly.
        """
        ops = self.builder.operations

        # Note: Energy tracking
        # Each reactor now utilizes sequential thermal operations (Heaters/Coolers)
        # to inject or remove energy from the syngas stream BEFORE it enters the reactor block.
        # This completely resolves the need to manually mux Energy Streams while making
        # all components accessible individually via isolated Streams in the UI.

        # 1. Configure Downdraft Gasifier (RCT_Conversion)
        if "Downdraft_Gasifier" in ops:
            _gasifier = ops["Downdraft_Gasifier"]
            # To-Do: Programmatically add specific Conversion Reactions via DWSIM Simulation Data
            pass

        # 2. Configure PEM (RCT_Equilibrium)
        if "PEM_Reactor" in ops:
            _pem = ops["PEM_Reactor"]
            # To-Do: Configure isothermal operation and add WGS/Methanation equilibrium reactions.
            pass

        # 3. Configure TRC (RCT_PFR)
        if "TRC_Reactor" in ops:
            _trc = ops["TRC_Reactor"]
            # Set default volume/length
            pass

    def run(self):
        """Execute the configured flowsheet."""
        assert self._is_built, "Flowsheet must be built before running"
        self.builder.calculate()
