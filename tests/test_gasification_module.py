import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dwsim_model.gasification import GasificationFlowsheet
from dwsim_model.core import FlowsheetBuilder

@pytest.fixture(scope="module")
def flowsheet():
    """Module-scoped flowsheet instance to prevent multiple Initialization issues"""
    b = FlowsheetBuilder()
    gf = GasificationFlowsheet(builder=b)
    return gf

def test_thermodynamics_setup(flowsheet):
    """Test correctly configuring property packages and compounds."""
    flowsheet.setup_thermo()
    compounds = {c.Name for c in flowsheet.builder.sim.SelectedCompounds.Values}
    assert "Carbon monoxide" in compounds
    assert "Methane" in compounds

def test_flowsheet_builder(flowsheet):
    """Test all required gasification operations are built"""
    flowsheet.build_flowsheet()
    
    ops = flowsheet.builder.operations
    assert "Downdraft_Gasifier" in ops
    assert "PEM_Reactor" in ops
    assert "TRC_Reactor" in ops
    assert "Quench_Vessel" in ops
    assert "Baghouse" in ops
    assert "Scrubber" in ops
    assert "Blower" in ops

def test_flowsheet_run_does_not_crash(flowsheet):
    """Test running the sequence executes safely (calculations will be incomplete)."""
    # Simply assert run completes without fatal program error. 
    # Calculations will throw errors on UI or quietly fail due to no specs, which is fine for Phase 1 construction
    flowsheet.run()
    assert flowsheet._is_built

