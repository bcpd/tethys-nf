# tethys-nf

Tethys-nf is a Nextflow DSL2 workflow for building a gene catalog from assembled genomes and profiling short-read metagenomes. It clusters input genomes (Skani), calls genes (Pyrodigal), assigns KO annotations (PyKOfamSearch or KOfamScan), optionally runs CheckM2 quality assessment, generates the *tethys* index, and finally performs taxonomic and functional profiling, emitting merged tables and NetCDF summaries.

## Quickstart

- Build database + profile + merge (all):

```
nextflow run . -profile conda,linux -resume \
  --mode all \
  --genomes_dir /path/to/genomes \
  --reads "/path/to/reads/*_{R1,R2}.fastq.gz" \
  --outdir ./results \
  --kofam_db /central/kofam \
  --checkm2_db /central/checkm2 \
  --pathway_db /central/kegg/pathway.pkl.gz
```

- Profile-only with a prebuilt index:
```
nextflow run . -profile conda,linux -resume \
  --mode profile \
  --reads "/path/to/reads/*_{R1,R2}.fastq.gz" \
  --index_dir /central/tethys/<catalog>/index \
  --outdir ./results
```

> On macOS hosts, swap `linux` for `mac` in the profile string.

## Environment Setup

- Recreate the per-process Conda envs (micromamba recommended):

```
micromamba install -f envs/build.yml -y
micromamba install -f envs/tethys.yml -y
micromamba install -f envs/checkm2.yml -y
```

- Lock environments for reproducibility (requires `conda-lock` ≥2.5):

```
conda-lock lock --kind micromamba \
  --file envs/build.yml --file envs/tethys.yml --file envs/checkm2.yml
```

  Commit the generated `.conda-lock/*.yml` files so CI and collaborators share identical dependency stacks.

## Databases

- KOfamScan DB: set `--kofam_db` or conf/local.config; required for KO annotation.
- Annotation backend: PyKOfamSearch runs by default for faster HMM scoring. Pass `--annotation_backend kofamscan` to use the legacy KOfamScan CLI instead.
- CheckM2 DB: set `--checkm2_db` or `$CHECKM2DB`. If missing, the pipeline runs `checkm2 database --download --path <dir>` to fetch it.
- Sylph database: built into the index at `index/database/genomes.syldb`.

## Example Dataset

- Instructions for preparing a minimal validation dataset live in `examples/README.md`. Download or subsample the genomes and reads into `examples/mini/` before running the commands below.
- Run the workflow end-to-end on the example data:

```
nextflow run . -profile conda,linux -resume \
  --mode all \
  --genomes_dir examples/mini/genomes \
  --reads "examples/mini/reads/*_{R1,R2}.fastq.gz" \
  --outdir ./results-mini \
  --skip_checkm2 \
  -with-report examples/mini/report.html
```

- Use the same dataset for CI or regression tests: `nextflow run . -params-file examples/mini/params.json`.

## Outputs

- Sample specific under `${outdir}/profile`:
  - Taxonomy: `taxonomic_abundance.genomes.parquet/tsv.gz`, `taxonomic_abundance.genome_clusters.*`, and corresponding `sequence_abundance.*`.
  - Functional:
    - Feature abundances: `feature_abundances.{genomes,genome_clusters}.{number_of_reads,tpm}.*`
    - Feature prevalence: `feature_prevalence{,-binary,-ratio}.{genomes,genome_clusters}.*`
    - Gene abundances (genomes): `gene_abundances.genomes.{number_of_reads,tpm}.*`
    - Pathway abundances: `pathway_abundances.{genomes,genome_clusters}.{number_of_reads,tpm,coverage}.*`
- Merged NetCDFs under `${outdir}/artifacts`:
  - `taxonomic_abundance.{genomes,genome_clusters}.nc`
  - `feature.{genomes,genome_clusters}.nc`
  - `pathway.{genomes,genome_clusters}.nc`

## Portability

- All local helpers run via `python bin/...` to avoid executable-bit issues.
- Conda envs per phase in `envs/` with `h5netcdf` for NetCDF writing.

## Config

- See `conf/local.config.example` for central DB paths; copy to `conf/local.config` and adjust per machine.
- Troubleshooting highlights:
  - **Database provisioning** – Run `python bin/tethys-download-kofam-db.py` and `checkm2 database --download --path <dir>` ahead of time on shared clusters to avoid repeated downloads inside jobs.
  - **External tools** – `tethys-index`/`profile-*` auto-discover `salmon`, `samtools`, and `sylph` on `PATH`. Override with `--salmon_executable`, `--samtools_executable`, or `--sylph_executable` when needed.
  - **Paired-end validation** – The profilers now error early if R1/R2 inputs are missing or mismatched; double-check glob patterns and filenames before launching large runs.
