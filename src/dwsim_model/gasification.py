from dwsim_model.core import FlowsheetBuilder

class GasificationFlowsheet:
    """
    Constructs the standard Gasification Process model in DWSIM.
    
    Includes:
    - Downdraft Gasifier (RCT_Conversion)
    - PEM (RCT_Equilibrium) 
    - TRC (RCT_PFR)
    - Quench Vessel (Mixer/Cooler)
    - Baghouse (SolidSeparator)
    - Scrubber (ComponentSeparator)
    - Blower/Compressor (Compressor)
    """

    def __init__(self, builder: FlowsheetBuilder | None = None):
        self.builder = builder or FlowsheetBuilder()
        self._is_built = False

    def setup_thermo(self) -> None:
        """Sets up thermodynamics and compounds. DbC: Builder must exist."""
        assert self.builder is not None, "Builder instance required"
        
        # Adding typical syngas compounds
        compounds = [
            "Carbon monoxide", "Hydrogen", "Carbon dioxide", 
            "Methane", "Water", "Nitrogen", "Oxygen", 
            "Helium" # Using Helium as placeholder for solids if not using SolidOps yet
        ]
        for c in compounds:
            self.builder.add_compound(c)
            
        self.builder.add_property_package("Peng-Robinson (PR)")

    def build_flowsheet(self) -> None:
        """Constructs the unit operations and streams."""
        if self._is_built:
            return
            
        b = self.builder
        
        # 1. Downdraft Gasifier
        feed = b.add_object("MaterialStream", "Biomass_Feed")
        gasifier = b.add_object("RCT_Conversion", "Downdraft_Gasifier")
        
        # 2. PEM 
        s1 = b.add_object("MaterialStream", "Syngas_Pre_PEM")
        pem = b.add_object("RCT_Equilibrium", "PEM_Reactor")
        
        # 3. TRC
        s2 = b.add_object("MaterialStream", "Syngas_Pre_TRC")
        trc = b.add_object("RCT_PFR", "TRC_Reactor")
        
        # 4. Quench Vessel
        s3 = b.add_object("MaterialStream", "Syngas_Pre_Quench")
        quench = b.add_object("Cooler", "Quench_Vessel")
        
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
        e_quench = b.add_object("EnergyStream", "E_Quench")
        e_blower = b.add_object("EnergyStream", "E_Blower")

        # Connections (Assuming straightforward port mapping for testing)
        try:
            b.connect(feed, gasifier, 0, 0)
            b.connect(gasifier, s1, 0, 0)
            
            b.connect(s1, pem, 0, 0)
            b.connect(pem, s2, 0, 0)
            
            b.connect(s2, trc, 0, 0)
            b.connect(trc, s3, 0, 0)
            
            b.connect(s3, quench, 0, 0)
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
            b.connect(e_quench, quench, 0, 0)
            b.connect(e_blower, blower, 0, 0)
        except Exception as e:
            print(f"Warning: Connection layout partial due to: {e}")
            
        self._is_built = True

    def run(self):
        """Execute the configured flowsheet."""
        assert self._is_built, "Flowsheet must be built before running"
        self.builder.calculate()

