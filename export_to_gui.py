import logging
from dwsim_model.gasification import GasificationFlowsheet, ReactorMode

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("Building flowsheet...")
    # Instantiate the flowsheet
    model = GasificationFlowsheet(mode=ReactorMode.MIXED)
    
    # Build
    model.setup_thermo()
    model.build_flowsheet()
    
    # Calculate initial values
    print("Calculating initial state...")
    model.run()
    
    # Save to GUI format
    output_filename = "Gasification_Model_GUI.dwxml"
    print(f"Exporting to {output_filename}...")
    model.builder.save(output_filename)
    print("Done! Open this file in the DWSIM GUI.")
