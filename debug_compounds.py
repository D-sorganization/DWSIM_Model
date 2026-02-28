import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dwsim_model.core import FlowsheetBuilder

def dump_compounds():
    b = FlowsheetBuilder()
    
    interf = b.interf
    try:
        if hasattr(interf, 'AvailableCompounds'):
            print("Found via AvailableCompounds property")
            for c in interf.AvailableCompounds.Values:
                print(f"Name: {c.Name}, Formula: {c.Formula}, CAS: {c.CAS_Number}")
            return
            
        print("Couldn't find compounds list directly.")
    except Exception as e:
        print(f"Error accessing compounds: {e}")

if __name__ == "__main__":
    dump_compounds()
