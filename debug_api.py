import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dwsim_model.core import FlowsheetBuilder

def debug_dwsim():
    builder = FlowsheetBuilder()
    interf = builder.interf
    
    # Print the available property packages from the interface
    pp_list = getattr(interf, 'AvailablePropertyPackages', None)
    if pp_list:
        print("Available Property Packages:", list((k, v) for k, v in pp_list.items()))
    else:
        print("No AvailablePropertyPackages property")
        
    print("Methods in Automation3:")
    for method in dir(interf):
        if not method.startswith("_"):
            print("  -", method)

if __name__ == "__main__":
    debug_dwsim()
