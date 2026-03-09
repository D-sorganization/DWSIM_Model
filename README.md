# DWSIM Gasification Train Model

`DWSIM_Model` is a Python-driven simulation project for a combined gasification train:

- Downdraft gasifier
- Plasma Entrained Melter (PEM)
- Thermal Reduction Chamber (TRC)
- Quench
- Baghouse
- Scrubber
- Blower

The repository combines:

- A headless Python runtime under `src/dwsim_model/`
- Structured YAML configuration under `config/`
- A checked-in DWSIM GUI artifact in `Gasification_Model_GUI.dwxml`
- A growing automated test suite under `tests/`

The project is still in early development. The current priority is to turn it into a professional-grade simulation codebase that is test-driven, DRY, design-by-contract oriented, reusable, and straightforward to change.

## Current Intent

This repo is intended to become the authoritative simulation package for the combined gasification train, not just a storage location for a manually edited DWSIM file.

That means the codebase should support:

- Reproducible model construction from versioned config
- Repeatable KPI calculation from extracted results
- Parameter sweeps and scenario overrides that actually exercise the runtime model
- Clear engineering contracts around configuration, topology, and metrics
- Fast unit tests plus meaningful higher-level validation

## Current State

Recent work has already improved some critical foundations:

- Master config resolution is now authoritative instead of being silently skipped
- Critical flowsheet build failures now fail fast instead of logging and continuing
- Parameter sweeps now run through the real runtime-config path
- KPI calculations now use a defensible carbon-conversion basis contract

The model is still not fully validated as an engineering tool. There are open issues for reactor contracts, test-pyramid maturity, duplicated topology builders, and broader documentation.

## Repository Layout

```text
DWSIM_Model/
|-- config/
|   |-- master_config.yaml
|   |-- feeds/
|   |-- reactors/
|   |-- energy/
|   |-- equipment/
|   `-- scenarios/
|-- docs/
|-- src/dwsim_model/
|   |-- __main__.py
|   |-- analysis/
|   |-- chemistry/
|   |-- config/
|   |-- results/
|   `-- standalone/
|-- tests/
|-- Gasification_Model_GUI.dwxml
`-- launch_gui.py
```

## Core Runtime Pieces

- `src/dwsim_model/gasification.py`
  Builds the combined train, wires topology, configures reactors, and applies external config.

- `src/dwsim_model/config_loader.py`
  Resolves master config references, validates config payloads, and applies feed and energy settings to the flowsheet.

- `src/dwsim_model/results/extractor.py`
  Extracts solved DWSIM results into Python dataclasses so downstream logic does not depend on live DWSIM objects.

- `src/dwsim_model/results/metrics.py`
  Computes KPIs such as cold gas efficiency, carbon conversion, H2/CO ratio, SEC, tar loading, and balance closure.

- `src/dwsim_model/analysis/sweep.py`
  Runs 1-D and 2-D parameter sweeps by patching runtime config and executing the model repeatedly.

## Configuration Model

The entry point for most runs is [`config/master_config.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\master_config.yaml).

It references sub-configs for:

- Feed definitions
- Reactor definitions
- Energy inputs
- Equipment configuration
- Scenario overrides

The active baseline files today are:

- [`config/feeds/gasifier_feeds.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\feeds\gasifier_feeds.yaml)
- [`config/feeds/pem_feeds.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\feeds\pem_feeds.yaml)
- [`config/feeds/trc_feeds.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\feeds\trc_feeds.yaml)
- [`config/feeds/quench_feeds.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\feeds\quench_feeds.yaml)
- [`config/reactors/gasifier_reactions.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\reactors\gasifier_reactions.yaml)
- [`config/reactors/pem_reactions.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\reactors\pem_reactions.yaml)
- [`config/reactors/trc_reactions.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\reactors\trc_reactions.yaml)
- [`config/energy/energy_inputs.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\energy\energy_inputs.yaml)
- [`config/equipment/gas_cleanup.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\equipment\gas_cleanup.yaml)
- [`config/scenarios/baseline.yaml`](C:\Users\diete\Repositories\DWSIM_Model\config\scenarios\baseline.yaml)

## Running The Model

The CLI lives in [`src/dwsim_model/__main__.py`](C:\Users\diete\Repositories\DWSIM_Model\src\dwsim_model\__main__.py).

Typical commands:

```powershell
python -m dwsim_model run --config config/master_config.yaml
python -m dwsim_model sweep --config config/master_config.yaml --param feeds.Gasifier_Biomass_Feed.mass_flow_kg_s --min 8 --max 12 --steps 5
python -m dwsim_model validate --config config/master_config.yaml
python -m dwsim_model summary
```

Notes:

- `run` builds the flowsheet, executes it, extracts results, and writes reports
- `sweep` performs repeated runs against patched runtime config
- `validate` checks YAML structure and referenced files
- `summary` prints reaction configuration information

## Environment And Dependencies

Minimum Python requirements currently tracked in [`requirements.txt`](C:\Users\diete\Repositories\DWSIM_Model\requirements.txt):

- `pythonnet`
- `pytest`

In practice, local development also uses:

- `ruff`
- `black`
- `mypy`
- `pytest`

DWSIM must be installed and reachable for full runtime execution. Many tests run without DWSIM by mocking the simulation boundary, but those tests do not replace full engineering validation.

## Validation Workflow

Before opening a PR, run:

```powershell
ruff check .
black --check .
mypy .
pytest -q
```

The repo CI currently expects the same basic quality gates plus GitHub-side PR checks.

## Testing Strategy

The target test pyramid for this repo is:

1. Unit tests
   Pure Python tests for config parsing, chemistry helpers, KPI math, and utility logic.
2. Contract tests
   Tests that verify runtime boundaries: config resolution, fail-fast behavior, extractor expectations, and stable CLI contracts.
3. Integration tests
   Tests that exercise `config -> build -> extract -> KPI` with controlled fixtures.
4. Acceptance tests
   Baseline and scenario cases for the combined train with explicit engineering expectations.

The suite is improving, but it is not yet complete enough to claim full model validation.

## Engineering Rules For This Repo

Going forward, repository work should follow these rules:

- TDD first when practical
  Write a failing test for new behavior before implementing it.
- DRY by default
  Avoid duplicating topology definitions, species properties, config rules, and KPI basis logic.
- DbC at engineering boundaries
  Missing required streams, invalid config, or broken topology should fail loudly instead of being logged and ignored.
- Reuse over one-off scripting
  Prefer explicit runtime contracts and small reusable functions over ad hoc patches.

## KPI Definitions

Current KPI implementations live in [`src/dwsim_model/results/metrics.py`](C:\Users\diete\Repositories\DWSIM_Model\src\dwsim_model\results\metrics.py).

The intended KPI set includes:

- Cold gas efficiency
- Carbon conversion efficiency
- H2/CO ratio
- Specific energy consumption
- Tar loading
- Mass balance closure
- Energy balance closure

Important current behavior:

- Carbon conversion can use an explicit biomass carbon mass fraction when validated feed data is available
- If that explicit basis is absent, the calculator falls back to known carbon-bearing surrogate species in the biomass feed stream
- If no defensible carbon basis exists, the metric warns and returns zero rather than silently publishing a fabricated value

## Known Limitations

- Reactor automation still needs stronger, versioned contracts
- The test suite still leans heavily on mocks for higher-level paths
- The `.dwxml` artifact and Python-generated runtime are not yet fully reconciled as a single authoritative source of truth
- Some local hooks and console output paths are Unix-biased and have Windows-specific defects
- The model has not yet been calibrated and regression-locked against production plant or design data

## Roadmap

The active engineering roadmap is tracked in GitHub Issues. The main gaps identified so far are:

- `#58` reactor contracts and chemistry automation
- `#59` removal of duplicated topology builders
- `#60` engineering-grade test pyramid
- `#61` documentation and onboarding maturity

Recently closed work:

- `#54` authoritative config resolution
- `#55` fail-fast topology/config behavior
- `#56` real runtime-config sweeps
- `#57` defensible KPI carbon basis

## Related Artifacts

- GUI model: [`Gasification_Model_GUI.dwxml`](C:\Users\diete\Repositories\DWSIM_Model\Gasification_Model_GUI.dwxml)
- Review memo: [`Gasification_Model_Review_and_Upgrade_Proposal.md`](C:\Users\diete\Repositories\DWSIM_Model\Gasification_Model_Review_and_Upgrade_Proposal.md)
- Launch helper: [`launch_gui.py`](C:\Users\diete\Repositories\DWSIM_Model\launch_gui.py)

## Contributing

When changing model behavior:

1. Start from a GitHub issue or create one.
2. Add or update tests first when feasible.
3. Keep configuration and runtime contracts explicit.
4. Run the local validation commands.
5. Open a PR with a narrow scope and clear engineering rationale.
