# Fix Pairing, IDs, Paths, Merge Failures, and Regression Coverage

## Summary
Implement the seven review fixes as one focused hardening pass. Preserve current public output layout where possible, but make failures explicit when pairing, genome ID mapping, path metadata, clustering flags, or merge inputs are inconsistent.

## Key Changes
- **Read pairing and shell safety**
  - In both profiling modules, replace loose `/R1/` and `/R2/` matching with one shared suffix-aware helper that accepts documented paired names such as `*_R1.fastq.gz` and `*_R2.fastq.gz`.
  - Fail before launching Python if exactly one R1 and one R2 cannot be identified, or if both mates resolve to the same staged path.
  - Quote all shell interpolations in `PROFILE_TAX` and `PROFILE_FUNC`, including `outdir`, read paths, `sample_id`, and `index_dir`.

- **Genome manifest and path provenance**
  - Change manifest generation to use extension-aware stems matching Nextflow `baseName`, so `sample.v1.fna` maps to `sample.v1.ffn`.
  - Stop rediscovering genomes from `Path('.')` in `BUILD_MANIFEST`; pass original genome paths from the workflow as explicit metadata.
  - Add Prodigal `.ffn` outputs as an explicit `BUILD_MANIFEST` input so the manifest only includes genomes with staged CDS files that actually exist in that task.

- **Cluster metadata correctness**
  - Keep cluster member lookup keyed by original genome filename, matching `CLUSTER_SKANI` output.
  - Set `contains_genome_cluster_mapping=false` for 3-column feature mappings and `true` only for 4-column mappings.
  - Ensure downstream genome-cluster functional outputs are attempted only when the index config truthfully reports cluster mappings.

- **Merge behavior and sample labels**
  - Normalize merged sample labels by stripping a leading `sample=` directory prefix in both taxonomy and pathway merge helpers.
  - Detect duplicate normalized sample IDs and fail with a clear error.
  - Replace blanket merge exception swallowing with explicit optional-output handling: warn only for genuinely absent optional artifact groups, and fail for corrupt files, schema/key errors, write failures, and unexpected exceptions.

## Test Plan
- Add lightweight Python tests using the standard library or existing test tooling if already available at implementation time.
- Cover:
  - dotted genome names such as `sample.v1.fna` remain `sample.v1` and find `sample.v1.ffn`;
  - duplicate basenames in nested genome directories fail clearly rather than silently collapsing;
  - sample IDs containing `R1`/`R2` do not confuse mate detection;
  - paths with spaces are rendered safely in profiling scripts;
  - 3-column feature mappings keep `contains_genome_cluster_mapping=false`;
  - merged samples are `foo`, not `sample=foo`;
  - duplicate normalized sample labels fail;
  - corrupt or schema-invalid parquet files cause merge failure, not a successful partial merge.
- Run `nextflow config .` and, if local dependencies are available, a mini `nextflow run` using the example dataset.

## Assumptions
- Keep the documented read naming convention as the supported default: `*_R1.fastq.gz` / `*_R2.fastq.gz`.
- Store original absolute genome input paths in the index metadata, not task work-directory paths.
- Treat merge omissions as errors unless the artifact group is explicitly optional because the index lacks pathways or cluster mappings.
- Do not introduce a large test framework unless the implementation discovers one already configured.
