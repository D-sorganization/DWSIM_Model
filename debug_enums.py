import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dwsim_model.core import FlowsheetBuilder
import clr

def debug_dwsim():
    builder = FlowsheetBuilder()
    sim = builder.sim
    interf = builder.interf
    
    # Print the available property packages from the interface
    pp_list = getattr(interf, 'AvailablePropertyPackages', {})
    for k in pp_list.Keys:
        print("Property Pack:", k)

    # Let's inspect DWSIM.Interfaces.Enums.GraphicObjects.ObjectType if it exists
    from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
    print("Object types available in ObjectType Enum:")
    for ot in dir(ObjectType):
        if not ot.startswith("_"):
            print("  -", ot)

if __name__ == "__main__":
    debug_dwsim()
