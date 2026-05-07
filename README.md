# tethys-nf

Tethys-nf is a Nextflow workflow for building gene catalogues from assembled genomes and profiling short-read metagenomes. It clusters input genomes (Skani), calls genes (Pyrodigal), assigns KO annotations (PyKOfamSearch or KOfamScan), optionally runs CheckM2 quality assessment, generates the *tethys* index, and finally performs taxonomic and functional profiling, emitting merged tables and NetCDF summaries.

## Installation

Tethys-nf requires Linux, Java 17 or newer, and Nextflow `26.04.0` or newer. Pipeline tasks can run either in Micromamba-managed Conda environments or in local Docker images.

Install system packages on Ubuntu or Debian:

```
sudo apt-get update
sudo apt-get install -y curl wget git unzip pigz default-jre docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Install system packages on Fedora, RHEL, or Rocky Linux:

```
sudo dnf install -y curl wget git unzip pigz java-17-openjdk docker
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in after adding yourself to the `docker` group.

Install Nextflow:

```
export NXF_VER=26.04.0
curl -s https://get.nextflow.io | bash
mkdir -p "$HOME/.local/bin"
mv nextflow "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
nextflow -version
```

Clone this repository:

```
git clone <tethys-nf-repository-url> tethys-nf
cd tethys-nf
```

For Micromamba/Conda execution, install Micromamba:

```
curl -Ls https://micro.mamba.pm/install.sh | bash
source ~/.bashrc
micromamba --version
```

Run with `-profile conda,linux`. Nextflow creates per-process environments from `envs/build.yml`, `envs/tethys.yml`, and `envs/checkm2.yml`.

For Docker execution, build the local images:

```
docker build -f docker/Dockerfile.build -t tethys-nf-build:latest .
docker build -f docker/Dockerfile.tethys -t tethys-nf-tethys:latest .
docker build -f docker/Dockerfile.checkm2 -t tethys-nf-checkm2:latest .
```

Run with `-profile docker,linux`.

The full tutorial repeats these installation steps and then walks through a human gut mock community dataset.

## Quickstart

- Build database + profile + merge (all):

```
nextflow run . -profile conda,linux -resume \
  --mode all \
  --genomes_dir /path/to/genomes \
  --samplesheet /path/to/samplesheet.csv \
  --outdir ./results \
  --kofam_db /central/kofam \
  --checkm2_db /central/checkm2 \
  --pathway_db /central/kegg/pathway.pkl.gz
```

- Profile-only with a prebuilt index:
```
nextflow run . -profile conda,linux -resume \
  --mode profile \
  --samplesheet /path/to/samplesheet.csv \
  --index_dir /central/tethys/<catalog>/index \
  --outdir ./results
```

> On macOS hosts, swap `linux` for `mac` in the profile string.

> Requires Nextflow `26.04.0` or newer (the pipeline uses static typing).

The recommended read input is a CSV samplesheet with columns `sample_id,fastq_1,fastq_2`. The legacy `--reads "/path/*_{R1,R2}.fastq.gz"` glob remains available for compatibility, but is deprecated.

## Tutorial

For a full Linux walkthrough using a human gut mock community, including installation, data download, Micromamba and Docker execution, and an optional real-stool extension, see [TUTORIAL.md](TUTORIAL.md).

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

- KOfamScan DB: set `--kofam_db` or auto-loaded `conf/local.config`; required for KO annotation.
- Annotation backend: KOfamScan runs by default for compatibility with current KOfam metadata. Pass `--annotation_backend pykofamsearch` only if your installed PyKOfamSearch version supports your KOfam database.
- CheckM2 DB: set `--checkm2_db` or `$CHECKM2DB`. If missing, the pipeline runs `checkm2 database --download --path <dir>` to fetch it.
- Sylph database: built into the index at `index/database/genomes.syldb`.

## Example Dataset

- Instructions for preparing a minimal validation dataset live in `examples/README.md`. Download or subsample the genomes and reads into `examples/mini/` before running the commands below.
- Run the workflow end-to-end on the example data:

```
nextflow run . -profile conda,linux -resume \
  --mode all \
  --genomes_dir examples/mini/genomes \
  --samplesheet examples/mini/samplesheet.csv \
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

- For machine-local defaults, copy `conf/local.config.example` to `conf/local.config` and adjust paths. The file is optional and is auto-loaded when present.
- Troubleshooting highlights:
  - **Database provisioning** – Run `python bin/tethys-download-kofam-db.py` and `checkm2 database --download --path <dir>` ahead of time on shared clusters to avoid repeated downloads inside jobs.
  - **External tools** – `tethys-index`/`profile-*` auto-discover `salmon`, `samtools`, and `sylph` on `PATH`. Override with `--salmon_executable`, `--samtools_executable`, or `--sylph_executable` when needed.
  - **Paired-end validation** – The profilers now error early if R1/R2 inputs are missing or mismatched; double-check glob patterns and filenames before launching large runs.
