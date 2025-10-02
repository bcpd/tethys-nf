# Example Dataset

This directory documents how to prepare a small validation dataset. No files are committed here by default; download or subsample the assets described below (each is ≲1 MB) before running the workflow.

## Download

1. Create local folders:
   ```
   mkdir -p examples/mini/genomes examples/mini/reads
   ```
2. Fetch two GTDB reference genomes (FASTA) and place them under `examples/mini/genomes/`. Any small bacterial assemblies will work; for reproducibility we suggest:
   - `GCF_000005845.2_ASM584v2_genomic.fna`
   - `GCF_000006945.2_ASM694v2_genomic.fna`
   (download the `*.fna.gz` from NCBI and decompress them if needed).

3. Prepare paired-end reads by subsampling public data (e.g., with `seqtk sample`) into:
   - `examples/mini/reads/sampleA_R1.fastq.gz`
   - `examples/mini/reads/sampleA_R2.fastq.gz`

   Ensure the filenames follow the `*_R1.fastq.gz` / `*_R2.fastq.gz` convention so the pipeline detects them automatically.

4. Optional: pre-download databases to avoid online fetches during tests:
   ```
   python bin/tethys-download-kofam-db.py -o databases/kofam
   checkm2 database --download --path databases/checkm2
   ```

## Running the Example Workflow

With the fixtures in place, run:

```
nextflow run . -profile conda,linux -resume \
  --mode all \
  --genomes_dir examples/mini/genomes \
  --reads "examples/mini/reads/*_{R1,R2}.fastq.gz" \
  --outdir ./results-mini \
  --skip_checkm2 \
  -with-report examples/mini/report.html
```

Expect the run to finish in a few minutes and populate `results-mini/` with clustering, annotation, profiling, and merged NetCDF outputs.
