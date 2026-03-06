"""
config_loader.py
================
Loads simulation parameters from external config files (YAML or legacy JSON)
so users can adjust feeds, energy values, and reactor settings without editing
Python code.

Upgrade notes vs. original version
-----------------------------------
* BUG FIX: ``apply_to_flowsheet`` now actually applies stream compositions.
* BUG FIX: Path resolution uses ``pathlib`` — no longer breaks when the script
  is run from a directory other than the project root.
* YAML support: reads ``.yaml`` / ``.yml`` files in addition to ``.json``.
* Unit awareness: temperature accepts both ``temperature_C`` and ``temperature_K``.
* Structured error reporting: collects all failures and reports them together.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _find_default_config() -> Path | None:
    """
    Walk up from this file's location looking for a known config file.

    Search order:
    1. ``<project_root>/config/master_config.yaml``
    2. ``<project_root>/config/master_config.yml``
    3. ``<project_root>/config/feed_conditions.json``  (legacy)
    """
    here = Path(__file__).resolve().parent  # .../src/dwsim_model/
    project_root = here.parent.parent  # .../DWSIM_Model/
    config_dir = project_root / "config"

    candidates = [
        config_dir / "master_config.yaml",
        config_dir / "master_config.yml",
        config_dir / "feed_conditions.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_file(path: Path) -> dict:
    """Load a YAML or JSON file and return its contents as a dict."""
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as fh:
        if suffix in {".yaml", ".yml"}:
            import yaml

            return yaml.safe_load(fh) or {}
        elif suffix == ".json":
            return json.load(fh)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")


# ─────────────────────────────────────────────────────────────────────────────
# ConfigLoader
# ─────────────────────────────────────────────────────────────────────────────


class ConfigLoader:
    """
    Parse and apply external configuration files to a DWSIM flowsheet.

    Parameters
    ----------
    config_path:
        Explicit path to the config file.  If None, the loader searches for a
        default config (see :func:`_find_default_config`).
    """

    def __init__(self, config_path: str | Path | None = None):
        if config_path is not None:
            self.config_path: Path | None = Path(config_path)
        else:
            self.config_path = _find_default_config()

        self.config: dict[str, Any] = {}
        self._errors: list[str] = []

    # ─────────────────────────────────────────────────────────────────────────

    def load(self) -> dict:
        """Load and return the configuration dictionary."""
        if self.config_path is None or not self.config_path.exists():
            logger.warning(
                "No config file found — using DWSIM defaults for all streams. "
                "Create config/master_config.yaml to customise the simulation."
            )
            return {}

        logger.info(f"Loading config from: {self.config_path}")
        try:
            raw = _load_file(self.config_path)
        except Exception as exc:
            logger.error(f"Failed to read config file {self.config_path}: {exc}")
            return {}

        self.config = self._resolve_sub_configs(raw)
        logger.info(
            f"Config loaded: "
            f"{len(self.config.get('feeds', {}))} feed streams, "
            f"{len(self.config.get('energy_streams', {}))} energy streams."
        )
        return self.config

    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_sub_configs(self, raw: dict) -> dict:
        """
        If ``raw`` contains file-path references (master_config style), load
        those files and merge them.  If ``raw`` already has a ``feeds`` key
        (legacy JSON style), return it unchanged.
        """
        if "feeds" in raw or "energy_streams" in raw:
            return raw  # already flat

        merged: dict = {
            "feeds": {},
            "energy_streams": {},
            "units": raw.get("units", {}),
        }
        config_dir = self.config_path.parent if self.config_path else Path(".")

        for _section, sub_path in raw.get("feeds", {}).items():
            try:
                sub = _load_file(config_dir / sub_path)
                for stream_name, props in sub.items():
                    if isinstance(props, dict):
                        merged["feeds"][stream_name] = props
            except Exception as exc:
                logger.warning(f"Could not load sub-config '{sub_path}': {exc}")

        energy_ref = raw.get("energy")
        if energy_ref:
            try:
                energy_data = _load_file(config_dir / energy_ref)
                merged["energy_streams"].update(energy_data.get("energy_streams", {}))
            except Exception as exc:
                logger.warning(f"Could not load energy config '{energy_ref}': {exc}")

        return merged

    # ─────────────────────────────────────────────────────────────────────────

    def apply_to_flowsheet(
        self,
        builder,
        materials: dict,
        energy_streams: dict,
    ) -> None:
        """
        Push loaded configuration values into DWSIM stream objects.

        Parameters
        ----------
        builder:
            The FlowsheetBuilder instance.
        materials:
            Dict mapping stream name → DWSIM MaterialStream object.
        energy_streams:
            Dict mapping stream name → DWSIM EnergyStream object.
            NOTE: The original code passed ``b.energies`` here — that attribute
            does not exist.  The correct attribute is ``b.energy_streams``.
        """
        if not self.config:
            logger.debug("apply_to_flowsheet: config is empty, nothing to apply.")
            return

        self._errors = []
        self._apply_material_streams(materials, self.config.get("feeds", {}))
        self._apply_energy_streams(
            energy_streams, self.config.get("energy_streams", {})
        )

        if self._errors:
            logger.warning(
                f"Config application finished with {len(self._errors)} error(s):\n"
                + "\n".join(f"  • {e}" for e in self._errors)
            )
        else:
            logger.info("All config values applied successfully.")

    # ─────────────────────────────────────────────────────────────────────────

    def _apply_material_streams(self, materials: dict, feeds: dict) -> None:
        """Apply T, P, flow, and composition to material streams."""
        for stream_name, props in feeds.items():
            if stream_name not in materials:
                logger.debug(
                    f"Stream '{stream_name}' in config not found in flowsheet — skipped."
                )
                continue

            stream = materials[stream_name]
            try:
                self._set_stream_conditions(stream, stream_name, props)
                self._set_stream_composition(stream, stream_name, props)
            except Exception as exc:
                self._errors.append(f"{stream_name}: {exc}")

    def _set_stream_conditions(self, stream, name: str, props: dict) -> None:
        """Set T, P, and mass-flow on a material stream."""
        if "temperature_C" in props:
            t_k = float(props["temperature_C"]) + 273.15
            stream.SetPropertyValue("Temperature", t_k)
            logger.debug(f"{name}: T = {props['temperature_C']} °C ({t_k:.2f} K)")
        elif "temperature_K" in props:
            stream.SetPropertyValue("Temperature", float(props["temperature_K"]))

        if "pressure_Pa" in props:
            stream.SetPropertyValue("Pressure", float(props["pressure_Pa"]))

        if "mass_flow_kg_s" in props:
            stream.SetPropertyValue("MassFlow", float(props["mass_flow_kg_s"]))

    def _set_stream_composition(self, stream, name: str, props: dict) -> None:
        """
        Apply mole fractions from a ``components`` dict.

        Fractions are normalised if they don't sum to exactly 1.0
        (tolerance ±0.02).
        """
        components: dict = props.get("components", {})
        if not components:
            return

        total = sum(float(v) for v in components.values())
        if total == 0:
            self._errors.append(f"{name}: all component fractions are zero — skipped.")
            return

        if abs(total - 1.0) > 0.02:
            logger.warning(
                f"{name}: component fractions sum to {total:.4f} — normalising."
            )

        for compound, fraction in components.items():
            norm_frac = float(fraction) / total
            try:
                stream.SetPropertyValue(f"MoleFraction.{compound}", norm_frac)
                logger.debug(f"{name}: x({compound}) = {norm_frac:.4f}")
            except Exception as exc:
                logger.warning(
                    f"{name}: could not set fraction for '{compound}': {exc}"
                )

    def _apply_energy_streams(self, energy_streams: dict, energy_config: dict) -> None:
        """Apply power values to energy streams."""
        for e_name, e_val in energy_config.items():
            if e_name not in energy_streams:
                logger.debug(f"Energy stream '{e_name}' not in flowsheet — skipped.")
                continue
            try:
                energy_streams[e_name].SetPropertyValue("EnergyFlow", float(e_val))
                logger.info(f"Applied {e_val} W to energy stream '{e_name}'.")
            except Exception as exc:
                self._errors.append(f"Energy stream {e_name}: {exc}")
