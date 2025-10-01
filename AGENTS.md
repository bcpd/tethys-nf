# Repository Guidelines

## Project Structure & Module Organization
- Nextflow DSL2 entrypoint: `main.nf`; config in `nextflow.config` and `conf/*.config` (profiles: `conda`, `mac`, `docker`).
- Pipeline modules: `modules/*.nf` (one process per file). Keep process labels and names consistent with existing ones (e.g., `CLUSTER_SKANI`).
- Helper scripts: `bin/*.py` (invoked via `python bin/...`).
- Environments: `envs/*.yml` (per-phase Conda specs; micromamba enabled).
- Data and outputs: inputs under your paths; outputs in `results/`; transient data in `work/`; local/central DBs in `databases/`.

## Build, Test, and Development Commands
- Configure local paths: copy `conf/local.config.example` to `conf/local.config` and edit DB locations.
- Full run (build → profile → merge):
  - `nextflow run . -profile conda,mac -resume --mode all --genomes_dir /path/to/genomes --reads "/data/*_{R1,R2}.fastq.gz" --outdir ./results --kofam_db /central/kofam --checkm2_db /central/checkm2 --pathway_db /central/kegg/pathway.pkl.gz`
- Profile only with existing index:
  - `nextflow run . -profile conda,mac -resume --mode profile --reads "/data/*_{R1,R2}.fastq.gz" --index_dir /central/tethys/<catalog>/index --outdir ./results`
- Artifacts merge only: `nextflow run . -profile conda,mac -resume --mode merge --outdir ./results`

## Coding Style & Naming Conventions
- Nextflow: DSL2 modules in `modules/` named `lower_snake.nf`; process labels `UPPER_SNAKE`. Prefer small, composable processes with explicit `emit:` names.
- Python (bin/): PEP8, 4‑space indent, `snake_case` for files and functions; argparse CLIs with clear `--help`. Prefer pure functions and type hints where practical. Scripts are run as `python bin/<tool>.py` to avoid executable-bit issues.

## Testing Guidelines
- No formal unit tests yet. Validate changes with small fixtures and `-resume` for quick iterations. Favor incremental runs: `--mode build`, then `--mode profile` with `--index_dir`.
- Optional: exercise modules individually by narrowing inputs (e.g., a subset of genomes/reads) and inspecting outputs under `results/`.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise scope prefixes when helpful (e.g., `nf:`, `bin:`, `conf:`). One logical change per commit.
- PRs: include a summary, rationale, sample `nextflow run` command used for validation, notable outputs (paths), and any config changes. Link related issues and update `README.md` when flags or outputs change.

## Security & Configuration Tips
- Do not commit large data or secrets. The repo already ignores `work/`, `results*/`, `.nextflow*`, `.conda/`, `databases/`.
- Prefer central, read-only database paths set via `conf/local.config` or CLI flags; document machine-specific paths in that local file only.

