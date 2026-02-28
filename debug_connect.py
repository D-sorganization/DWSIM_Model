import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dwsim_model.core import FlowsheetBuilder

def debug_connection_methods():
    builder = FlowsheetBuilder()
    sim = builder.sim
    print(sim.ConnectObjects.__doc__)
            
if __name__ == "__main__":
    debug_connection_methods()
