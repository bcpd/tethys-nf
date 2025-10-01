# tethys-nf

A Nextflow DSL2 pipeline for scalable taxonomic and functional profiling using Tethys modules + upstream steps (Skani clustering, Pyrodigal gene prediction, KOfamScan, optional CheckM2 QA), with merged Parquet and NetCDF artifacts.

## Quickstart

- Build DB + profile + merge (all):

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

## Databases

- KOfamScan DB: set `--kofam_db` or conf/local.config; required for KO annotation.
- Annotation backend: PyKOfamSearch runs by default for faster HMM scoring. Pass `--annotation_backend kofamscan` to use the legacy KOfamScan CLI instead.
- CheckM2 DB: set `--checkm2_db` or `$CHECKM2DB`. If missing, the pipeline runs `checkm2 database --download --path <dir>` to fetch it.
- Sylph "DB": built into the index at `index/database/genomes.syldb`.

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
