"""
chemistry/reactions.py
=======================
DWSIM reaction configuration for the three reactor vessels.

This module is called by GasificationFlowsheet._configure_reactors().
Each function receives the DWSIM reactor object and the simulation, then
attempts to set up the appropriate reaction set via the DWSIM API.

Why a separate module?
    Separating reaction chemistry from flowsheet topology makes it much
    easier to:
    - Swap reaction sets without touching flowsheet code
    - Test reactions independently
    - Read parameters from config files rather than hard-coding

DWSIM Reaction API notes (for future reference)
------------------------------------------------
The DWSIM Automation3 API provides:
    sim.Reactions                           → reaction dictionary
    sim.AddReaction(reaction_object)        → adds to simulation
    reactor.Reactions                       → list of reactions on this unit
    reactor.ReactionsConversionSeparated    → conversion reactor specifics

Creating a conversion reaction object (pseudo-code):
    from DWSIM.Thermodynamics.BaseClasses import Reaction
    rxn = Reaction()
    rxn.Name = "Water Gas Reaction"
    rxn.ReactionType = "Conversion"
    rxn.BaseReactant = "Water"
    rxn.BaseReactantStoichiometry = -1.0
    rxn.ComponentStoichiometries = {"Water": -1.0, "CO": +1.0, "H2": +1.0}
    rxn.Conversions.Add(component, conversion_value)

NOTE: The exact API calls depend on the installed DWSIM version.
The functions below include try/except blocks so the flowsheet builds
even if the API calls fail (e.g., in mock/test environments).
The reaction configurations are also stored in the YAML config files —
if DWSIM API changes, only this module needs updating.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Path to reactor config files
_CONFIG_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "reactors"
)


def _load_reactor_config(filename: str) -> dict:
    """Load a reactor YAML config, return empty dict if not found."""
    path = _CONFIG_DIR / filename
    if not path.exists():
        logger.warning(f"Reactor config not found: {path}")
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# ─────────────────────────────────────────────────────────────────────────────
# Gasifier (RCT_Conversion)
# ─────────────────────────────────────────────────────────────────────────────


def configure_gasifier(gasifier_obj, sim) -> None:
    """
    Configure the Downdraft Gasifier with conversion reactions.

    In DWSIM, an RCT_Conversion reactor computes outlet compositions
    using user-specified fractional conversions for each reaction.
    This is the simplest model and a good starting point.

    Parameters
    ----------
    gasifier_obj:
        DWSIM reactor object (from builder.operations["Downdraft_Gasifier"])
    sim:
        DWSIM simulation object (from builder.sim)
    """
    config = _load_reactor_config("gasifier_reactions.yaml")
    if not config:
        logger.warning("No gasifier reaction config found — using DWSIM defaults.")
        return

    reactor_params = config.get("reactor", {})
    reactions = config.get("reactions", [])

    if not reactions:
        logger.warning("No reactions defined in gasifier_reactions.yaml")
        return

    try:
        _set_reactor_conditions(gasifier_obj, reactor_params)
        _add_conversion_reactions(gasifier_obj, sim, reactions)
        logger.info(f"Gasifier configured with {len(reactions)} conversion reactions.")
    except Exception as exc:
        logger.error(f"Gasifier configuration failed: {exc}")
        raise


def _set_reactor_conditions(reactor_obj, params: dict) -> None:
    """Set temperature, pressure, and operation mode on a reactor."""
    if "temperature_C" in params:
        t_k = float(params["temperature_C"]) + 273.15
        try:
            reactor_obj.OutletTemperature = t_k
        except AttributeError:
            try:
                reactor_obj.SetPropertyValue("OutletTemperature", t_k)
            except Exception as exc:
                logger.debug(f"Could not set reactor temperature: {exc}")

    if "pressure_Pa" in params:
        try:
            reactor_obj.OutletPressure = float(params["pressure_Pa"])
        except AttributeError:
            try:
                reactor_obj.SetPropertyValue(
                    "OutletPressure", float(params["pressure_Pa"])
                )
            except Exception as exc:
                logger.debug(f"Could not set reactor pressure: {exc}")


def _add_conversion_reactions(reactor_obj, sim, reactions: list[dict]) -> None:
    """
    Add conversion reactions to an RCT_Conversion reactor.

    This attempts to use the DWSIM Automation3 API to create Reaction
    objects and attach them to the reactor.  If the API calls are not
    available in the current environment, reactions are logged for
    manual entry in the DWSIM GUI.
    """
    for rxn_def in reactions:
        name = rxn_def.get("name", "Unnamed Reaction")
        base_comp = rxn_def.get("base_component", "")
        conversion = float(rxn_def.get("conversion", 0.5))

        try:
            # DWSIM Automation3 API — creates a Reaction in the simulation
            # Note: API subject to change between DWSIM versions
            rxn_obj = sim.AddReaction(
                name,
                "Conversion",
                base_comp,
                conversion,
            )
            if rxn_obj is not None:
                # Attach to reactor
                reactor_obj.Reactions.Add(rxn_obj.ID)
                logger.debug(
                    f"Added reaction '{name}' to gasifier "
                    f"(base={base_comp}, X={conversion:.2f})"
                )
        except AttributeError:
            # AddReaction may not exist in all API versions
            logger.info(
                f"Manual GUI setup required: '{name}' "
                f"(base={base_comp}, X={conversion:.2f})"
            )
        except Exception as exc:
            logger.warning(f"Could not add reaction '{name}': {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# PEM (RCT_Equilibrium)
# ─────────────────────────────────────────────────────────────────────────────


def configure_pem(pem_obj, sim) -> None:
    """
    Configure the PEM as an equilibrium (Gibbs minimisation) reactor.

    At plasma temperatures (1200–1600°C), most reactions reach equilibrium
    rapidly.  DWSIM's RCT_Equilibrium uses Gibbs energy minimisation,
    which is the most physically accurate approach at these conditions.

    Parameters
    ----------
    pem_obj:
        DWSIM reactor object (from builder.operations["PEM_Reactor"])
    sim:
        DWSIM simulation object
    """
    config = _load_reactor_config("pem_reactions.yaml")
    if not config:
        logger.warning("No PEM reaction config found — using DWSIM defaults.")
        return

    reactor_params = config.get("reactor", {})
    reactions = config.get("reactions", [])

    try:
        _set_reactor_conditions(pem_obj, reactor_params)

        # For RCT_Equilibrium, set isothermal mode so DWSIM holds the set temperature
        try:
            pem_obj.ReactorOperationMode = 0  # 0 = Isothermal in most DWSIM versions
        except AttributeError as exc:
            logger.debug(f"AttributeError setting ReactorOperationMode: {exc}")  # AUTO-FIXED, Not critical — DWSIM will use default mode

        # Add equilibrium reactions as constraints
        for rxn_def in reactions:
            name = rxn_def.get("name", "Unnamed")
            try:
                rxn_obj = sim.AddReaction(name, "Equilibrium", "", 0)
                if rxn_obj is not None:
                    pem_obj.Reactions.Add(rxn_obj.ID)
                    logger.debug(f"Added equilibrium reaction '{name}' to PEM")
            except Exception as exc:
                logger.info(
                    f"Manual GUI setup required for PEM reaction '{name}': {exc}"
                )

        logger.info(
            f"PEM configured at {reactor_params.get('temperature_C', 'N/A')}°C "
            f"with {len(reactions)} equilibrium reactions."
        )
    except Exception as exc:
        logger.error(f"PEM configuration failed: {exc}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# TRC (RCT_PFR)
# ─────────────────────────────────────────────────────────────────────────────


def configure_trc(trc_obj, sim) -> None:
    """
    Configure the TRC as a plug-flow reactor with tar cracking kinetics.

    The TRC is modelled as an adiabatic PFR.  Key parameters are the
    reactor volume/length and Arrhenius kinetic expressions for tar
    cracking reactions.

    Parameters
    ----------
    trc_obj:
        DWSIM reactor object (from builder.operations["TRC_Reactor"])
    sim:
        DWSIM simulation object
    """
    config = _load_reactor_config("trc_reactions.yaml")
    if not config:
        logger.warning("No TRC reaction config found — using DWSIM defaults.")
        return

    reactor_params = config.get("reactor", {})
    reactions = config.get("reactions", [])

    try:
        _set_reactor_conditions(trc_obj, reactor_params)

        # Set reactor geometry
        volume = float(reactor_params.get("volume_m3", 2.0))
        length = float(reactor_params.get("length_m", 3.0))
        diameter = float(reactor_params.get("diameter_m", 0.92))

        try:
            trc_obj.Volume = volume
            trc_obj.Length = length
            trc_obj.Diameter = diameter
            logger.debug(f"TRC geometry: V={volume} m³, L={length} m, D={diameter} m")
        except AttributeError:
            # Try via SetPropertyValue
            for prop, val in [
                ("Volume", volume),
                ("Length", length),
                ("Diameter", diameter),
            ]:
                try:
                    trc_obj.SetPropertyValue(prop, val)
                except Exception as exc:
                    logger.debug(f"Exception setting property {prop}: {exc}")  # AUTO-FIXED

        # Set adiabatic operation
        try:
            trc_obj.ReactorOperationMode = 1  # 1 = Adiabatic in most DWSIM versions
        except AttributeError:
            pass

        # Add kinetic reactions
        for rxn_def in reactions:
            name = rxn_def.get("name", "Unnamed")
            base_comp = rxn_def.get("base_component", "")
            kinetics = rxn_def.get("kinetics", {})

            A = float(kinetics.get("pre_exponential_A", 1e6))
            Ea = float(kinetics.get("activation_energy_J_mol", 1e5))
            n = float(kinetics.get("reaction_order_n", 1.0))

            try:
                rxn_obj = sim.AddReaction(name, "Kinetic", base_comp, 0)
                if rxn_obj is not None:
                    # Attempt to set Arrhenius parameters
                    try:
                        rxn_obj.PreExponentialFactor = A
                        rxn_obj.ActivationEnergy = Ea
                        rxn_obj.ReactionOrder = n
                    except AttributeError as exc:
                        logger.debug(f"AttributeError setting Arrhenius parameters: {exc}")  # AUTO-FIXED
                    trc_obj.Reactions.Add(rxn_obj.ID)
                    logger.debug(
                        f"Added kinetic reaction '{name}': A={A:.2e}, Ea={Ea:.0f} J/mol"
                    )
            except Exception as exc:
                logger.info(
                    f"Manual GUI setup required for TRC kinetic reaction '{name}': {exc}"
                )

        logger.info(
            f"TRC configured: V={volume} m³, {len(reactions)} kinetic reactions."
        )
    except Exception as exc:
        logger.error(f"TRC configuration failed: {exc}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Summary printer (useful for debugging)
# ─────────────────────────────────────────────────────────────────────────────


def print_reaction_summary() -> None:
    """Print a human-readable summary of all configured reactions."""
    for name, filename in [
        ("Gasifier", "gasifier_reactions.yaml"),
        ("PEM", "pem_reactions.yaml"),
        ("TRC", "trc_reactions.yaml"),
    ]:
        cfg = _load_reactor_config(filename)
        rxns = cfg.get("reactions", [])
        print(f"\n{name} ({cfg.get('reactor', {}).get('type', 'unknown')}):")
        print(f"  Temperature: {cfg.get('reactor', {}).get('temperature_C', 'N/A')} °C")
        for r in rxns:
            conv = r.get("conversion", "")
            conv_str = f"  X={conv:.0%}" if isinstance(conv, float) else ""
            print(f"  • {r.get('name', '?')}{conv_str}")


if __name__ == "__main__":
    print_reaction_summary()
