# MatterGen--PARC A3-v4 Closeout

Status: protocol/environment gate only. No generated candidate pool, no PARC
selection, no DFT job manifest and no DFT outcomes are included.

## Environment checks

- MatterGen: `completed_smoke_import_and_help`. Detail: MODELS_PROJECT_ROOT: <MATTERGEN_ENV>/lib/python3.10/site-packages/mattergen <MATTERGEN_ENV>/lib/python3.10/site-packages/lightning_fabric/__init__.py:36: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.   __import__("pkg_resources").declare_namespace(__name__) INFO: Showing help with the command 'mattergen-generate -- --help'.  NAME     mattergen-generate - Evaluate diffusion model against molecular metrics.  SYNOPSIS     mattergen-generate OUTPUT_PATH <flags>  DESCRIPTION     Evaluate diffusion model against molecular me
- MACE-MP: `completed`. Detail: cuequivariance or cuequivariance_torch is not available. Cuequivariance acceleration will be disabled. Using Materials Project MACE for MACECalculator with <HOME>/.cache/mace/20231210mace128L0_energy_epoch249model Using float32 for MACECalculator, which is faster but less accurate. Recommended for MD. Use float64 for geometry optimization. mace_smoke_energy -3.2848479747772217 torch_cuda True <HOME>/miniconda3/lib/python3.12/site-packages/e3nn/o3/_wigner.py:10: UserWarning: Environment variable TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD detected, since the`weights_only` argument was not explicitly passed to `torch.load`, forcing weights_only=False.   _Jd, _W3j_flat, _W3j_indices = torch.load(os.path.join(os.path.dirname(__file__), 'constants.pt')) <HOME>/miniconda3/lib/python3.12/site-packages/mace/cal

## Interpretation

A3-v2 and A3-v3 showed that the PGCGM and near-hull substitution candidate
universes did not provide enough evidence mass for a prospective strict DFT
arm. A3-v4 therefore changes the candidate-generator protocol before DFT
outcome access: MatterGen-generated candidates, strict public-label exclusion
and CHGNet + MACE-MP conservative consensus scoring.

This milestone must not be cited as a completed positive result. It becomes a
prospective computational trial only after a real MatterGen pool is generated,
public-label-free candidates are frozen, consensus scores are computed, and a
nonempty PARC release arm is committed before any DFT outcomes.
