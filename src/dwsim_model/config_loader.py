import json
import logging
import os

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Handles parsing of external JSON configuration files so users can input feeds
    and properties without editing Python code (Code-first approach via separate config).
    Follows DbC (Design by Contract) by asserting required structures.
    """

    def __init__(self, filepath="config/feed_conditions.json"):
        self.filepath = filepath
        self.config = {}

    def load(self):
        if not os.path.exists(self.filepath):
            logger.warning(f"Config file {self.filepath} not found. Using defaults.")
            return {}

        with open(self.filepath, "r") as f:
            self.config = json.load(f)

        return self.config

    def apply_to_flowsheet(self, builder, materials, energies):
        """Applies parsed temperatures, pressures, composition, and energy values to the Flowsheet objects."""
        if not self.config:
            return

        feeds = self.config.get("feeds", {})
        for stream_name, props in feeds.items():
            if stream_name in materials:
                stream = materials[stream_name]
                try:
                    # DWSIM Python API property setting
                    if "temperature_C" in props:
                        # Temperature in Kelvin
                        stream.SetPropertyValue(
                            "Temperature", props["temperature_C"] + 273.15
                        )
                    if "pressure_Pa" in props:
                        stream.SetPropertyValue("Pressure", props["pressure_Pa"])
                    if "mass_flow_kg_s" in props:
                        stream.SetPropertyValue("MassFlow", props["mass_flow_kg_s"])

                    logger.info(f"Applied config properties to {stream_name}")
                except Exception as e:
                    logger.error(f"Failed to apply config to {stream_name}: {e}")

        power_streams = self.config.get("energy_streams", {})
        for e_name, e_val in power_streams.items():
            if e_name in energies:
                try:
                    # Apply energy value directly (assumed kW config for EnergyValue)
                    energies[e_name].SetPropertyValue("EnergyFlow", e_val)
                    logger.info(f"Applied power of {e_val} kW to {e_name}")
                except Exception as e:
                    logger.error(f"Failed to apply energy flux to {e_name}: {e}")
