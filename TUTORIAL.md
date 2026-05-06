# Tethys-nf linux tutorial: human gut mock community

This tutorial runs `tethys-nf` on a low-complexity human gut mock community. It is intended for Linux users and includes two execution paths:

- Micromamba/Conda: closest to the default development setup.
- Docker: uses local images built from this repository.

The main dataset is NCBI BioProject [PRJNA747117](https://www.ncbi.nlm.nih.gov/bioproject/747117), a synthetic human fecal/gut mock community. It has public reference assemblies and SRA reads. An optional dataset uses [SRR1761666](https://www.ncbi.nlm.nih.gov/sra/?term=SRR1761666), a paired-end human gut metagenome.

## What this tutorial does

The mock run builds a small genome-resolved reference from public mock-community genomes, annotates genes with KOfam, creates a Tethys index, profiles paired-end reads with Sylph and Salmon, and merges sample outputs into NetCDF artifacts.

This is a workflow tutorial, not a complete human stool reference analysis. For real cohorts, replace the mock genomes with an appropriate human gut genome catalog or study-specific MAG catalog, and perform host-read removal before running Tethys-nf.

## 1. Install system prerequisites

Tethys-nf requires Linux, Bash, Git, Java, Nextflow, and either Micromamba or Docker. Nextflow runs on the host even when Docker is used.

On Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y curl wget git unzip pigz default-jre docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in after adding yourself to the `docker` group.

On Fedora, RHEL, or Rocky Linux:

```bash
sudo dnf install -y curl wget git unzip pigz java-17-openjdk docker
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Confirm Java is available:

```bash
java -version
```

Nextflow requires Java 17 or newer for recent releases. Install Nextflow 26.04 or newer:

```bash
export NXF_VER=26.04.0
curl -s https://get.nextflow.io | bash
mkdir -p "$HOME/.local/bin"
mv nextflow "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
nextflow -version
```

Clone the repository, replacing the URL with the location of your fork or upstream repository:

```bash
git clone <tethys-nf-repository-url> tethys-nf
cd tethys-nf
```

If you already cloned the repository, run the remaining commands from the repository root.

## 2. Choose an execution backend

### Option A: Micromamba

Install Micromamba:

```bash
curl -Ls https://micro.mamba.pm/install.sh | bash
source ~/.bashrc
micromamba --version
```

Create a small helper environment for downloading tutorial data:

```bash
micromamba create -y -n tethys-tutorial -c conda-forge -c bioconda \
  python=3.11 sra-tools ncbi-datasets-cli seqtk pigz unzip curl wget
micromamba activate tethys-tutorial
```

Nextflow will use Micromamba to create the pipeline task environments from `envs/build.yml`, `envs/tethys.yml`, and `envs/checkm2.yml`.

### Option B: Docker

Build the local pipeline images:

```bash
docker build -f docker/Dockerfile.build -t tethys-nf-build:latest .
docker build -f docker/Dockerfile.tethys -t tethys-nf-tethys:latest .
docker build -f docker/Dockerfile.checkm2 -t tethys-nf-checkm2:latest .
```

The image tags map to the three dependency groups used by the workflow:

- `tethys-nf-build:latest`: genome clustering, gene calling, KOfam annotation, manifest generation, and KOfam DB checks.
- `tethys-nf-tethys:latest`: preprocessing, indexing, taxonomic profiling, functional profiling, and merge.
- `tethys-nf-checkm2:latest`: optional CheckM2 database verification and genome quality prediction.

For data download commands, use either system packages or the Micromamba helper environment from Option A. Docker is used for the pipeline tasks, not for the host-side download commands in this tutorial.

## 3. Prepare directories

```bash
mkdir -p data/human_gut_mock/{metadata,genomes,reads/raw,reads/subsampled}
mkdir -p databases results-human-mock
```

## 4. Download mock community genomes

Download the genome data package for PRJNA747117 and copy genome FASTA files into one genome directory.

```bash
datasets download genome accession \
  PRJNA747117 \
  --include genome \
  --filename data/human_gut_mock/metadata/prjna747117_genomes.zip

unzip -o data/human_gut_mock/metadata/prjna747117_genomes.zip \
  -d data/human_gut_mock/metadata/prjna747117_genomes

find data/human_gut_mock/metadata/prjna747117_genomes/ncbi_dataset/data \
  -name "*.fna" \
  -exec cp {} data/human_gut_mock/genomes/ \;

find data/human_gut_mock/genomes -name "*.fna" | sort
```

These are the reference genomes used to build the tutorial index. Some mock-community organisms may be absent if they are not represented by assemblies attached to the BioProject. That is acceptable for a workflow tutorial; use a complete curated reference for biological interpretation.

## 5. Download and subsample mock reads

Fetch run metadata for PRJNA747117 from ENA and select the first paired Illumina WGS or metagenomic run.

```bash
curl -L --retry 5 --retry-delay 5 --fail \
  "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=PRJNA747117&result=read_run&fields=run_accession,instrument_platform,library_layout,library_strategy&format=tsv&download=false" \
  -o data/human_gut_mock/metadata/read_runinfo.tsv

python - <<'PY'
from pathlib import Path

runinfo = Path("data/human_gut_mock/metadata/read_runinfo.tsv")
selected = None
with runinfo.open() as handle:
    header = handle.readline().rstrip("\n").split("\t")
    for line in handle:
        if not line.strip():
            continue
        row = dict(zip(header, line.rstrip("\n").split("\t")))
        if (
            row.get("instrument_platform") == "ILLUMINA"
            and row.get("library_layout") == "PAIRED"
            and row.get("library_strategy") in {"WGS", "METAGENOMIC"}
        ):
            selected = row["run_accession"]
            break

if selected is None:
    raise SystemExit("No paired Illumina WGS or metagenomic run found in PRJNA747117 run metadata")

Path("data/human_gut_mock/metadata/selected_run.txt").write_text(selected + "\n")
print(selected)
PY
```

Download the selected run:

```bash
RUN_ID=$(cat data/human_gut_mock/metadata/selected_run.txt)

prefetch "$RUN_ID" --output-directory data/human_gut_mock/reads/raw
fasterq-dump "$RUN_ID" \
  --split-files \
  --threads 8 \
  --outdir data/human_gut_mock/reads/raw

pigz -p 8 data/human_gut_mock/reads/raw/${RUN_ID}_1.fastq
pigz -p 8 data/human_gut_mock/reads/raw/${RUN_ID}_2.fastq
```

Subsample to 500,000 read pairs for a tutorial-sized run:

```bash
seqtk sample -s100 data/human_gut_mock/reads/raw/${RUN_ID}_1.fastq.gz 500000 \
  | pigz -p 4 > data/human_gut_mock/reads/subsampled/${RUN_ID}_R1.fastq.gz

seqtk sample -s100 data/human_gut_mock/reads/raw/${RUN_ID}_2.fastq.gz 500000 \
  | pigz -p 4 > data/human_gut_mock/reads/subsampled/${RUN_ID}_R2.fastq.gz
```

Create the samplesheet:

```bash
cat > data/human_gut_mock/samplesheet.csv <<EOF
sample_id,fastq_1,fastq_2
human_gut_mock,data/human_gut_mock/reads/subsampled/${RUN_ID}_R1.fastq.gz,data/human_gut_mock/reads/subsampled/${RUN_ID}_R2.fastq.gz
EOF

cat data/human_gut_mock/samplesheet.csv
```

## 6. Prepare databases

Download KOfam profiles once and reuse them across runs:

```bash
python bin/tethys-download-kofam-db.py --outdir databases/kofam
```

CheckM2 is optional for this tutorial. The default command below uses `--skip_checkm2` to keep the run smaller. To enable CheckM2 later:

```bash
checkm2 database --download --path databases/checkm2
```

## 7. Run the mock community workflow

With Micromamba:

```bash
nextflow run . -profile conda,linux -resume \
  --mode all \
  --genomes_dir data/human_gut_mock/genomes \
  --samplesheet data/human_gut_mock/samplesheet.csv \
  --outdir results-human-mock \
  --kofam_db databases/kofam \
  --skip_checkm2 \
  --threads 8 \
  -with-report results-human-mock/report.html
```

With Docker:

```bash
nextflow run . -profile docker,linux -resume \
  --mode all \
  --genomes_dir data/human_gut_mock/genomes \
  --samplesheet data/human_gut_mock/samplesheet.csv \
  --outdir results-human-mock \
  --kofam_db databases/kofam \
  --skip_checkm2 \
  --threads 8 \
  -with-report results-human-mock/report.html
```

## 8. Inspect outputs

Genome clusters are ANI-based pangenome units. Tethys-nf reports compatible outputs at both genome and genome-cluster levels when clusters are present.

```bash
find results-human-mock/build -maxdepth 4 -type f | sort
find results-human-mock/profile -maxdepth 5 -type f | sort
find results-human-mock/artifacts -type f | sort
```

Expected merged artifacts include:

```text
results-human-mock/artifacts/taxonomic_abundance.genomes.nc
results-human-mock/artifacts/taxonomic_abundance.genome_clusters.nc
results-human-mock/artifacts/feature.genomes.nc
results-human-mock/artifacts/feature.genome_clusters.nc
results-human-mock/artifacts/pathway.genomes.nc
results-human-mock/artifacts/pathway.genome_clusters.nc
```

Some genome-cluster or pathway artifacts can be absent if the tutorial reference lacks cluster mappings or if pathway database overlap is insufficient. In the default workflow, Skani-derived clusters and KOfam annotations should normally enable both levels.

Preview a NetCDF file:

```bash
python bin/tethys-info.py --netcdf results-human-mock/artifacts/taxonomic_abundance.genomes.nc
```

## 9. Optional: Profile a real human stool sample

This extension uses [SRR1761666](https://www.ncbi.nlm.nih.gov/sra/?term=SRR1761666), a paired-end human gut metagenome with about 1.4 Gbases and a compressed SRA size of about 781 MB. It profiles the sample against the small mock-community index built above, so results are useful for testing the workflow and estimating scale, not for complete biological interpretation.

Download and subsample:

```bash
mkdir -p data/real_stool/reads/{raw,subsampled}

prefetch SRR1761666 --output-directory data/real_stool/reads/raw
fasterq-dump SRR1761666 \
  --split-files \
  --threads 8 \
  --outdir data/real_stool/reads/raw

pigz -p 8 data/real_stool/reads/raw/SRR1761666_1.fastq
pigz -p 8 data/real_stool/reads/raw/SRR1761666_2.fastq

seqtk sample -s100 data/real_stool/reads/raw/SRR1761666_1.fastq.gz 1000000 \
  | pigz -p 4 > data/real_stool/reads/subsampled/SRR1761666_R1.fastq.gz

seqtk sample -s100 data/real_stool/reads/raw/SRR1761666_2.fastq.gz 1000000 \
  | pigz -p 4 > data/real_stool/reads/subsampled/SRR1761666_R2.fastq.gz

cat > data/real_stool/samplesheet.csv <<EOF
sample_id,fastq_1,fastq_2
SRR1761666,data/real_stool/reads/subsampled/SRR1761666_R1.fastq.gz,data/real_stool/reads/subsampled/SRR1761666_R2.fastq.gz
EOF
```

Run profile-only with Micromamba:

```bash
nextflow run . -profile conda,linux -resume \
  --mode profile \
  --samplesheet data/real_stool/samplesheet.csv \
  --index_dir results-human-mock/build/tethys/index \
  --outdir results-real-stool \
  --threads 8
```

Run profile-only with Docker:

```bash
nextflow run . -profile docker,linux -resume \
  --mode profile \
  --samplesheet data/real_stool/samplesheet.csv \
  --index_dir results-human-mock/build/tethys/index \
  --outdir results-real-stool \
  --threads 8
```

Estimated resource use for the real-stool extension:

| Run type | CPU | RAM | Disk | Expected wall time |
| --- | ---: | ---: | ---: | --- |
| 1M read-pair subsample against mock index | 8 | 8-16 GB | 20-40 GB | tens of minutes to a few hours |
| Full SRR1761666 against mock index | 8-16 | 8-16 GB | 40-80 GB | a few hours, storage dependent |
| Full stool sample against a large human gut catalog | 16-32+ | 32-64+ GB | 100s of GB or more | hours to days depending catalog size |

These are planning estimates. KOfam annotation and Salmon indexing dominate build time; read profiling scales with read count and index size. Host-read removal, quality trimming, and cohort-scale orchestration are outside this tutorial.

## Troubleshooting

- `nextflow: command not found`: add `$HOME/.local/bin` to `PATH`.
- `Cannot find Java`: install Java 17 or newer and confirm `java -version`.
- Docker permission denied: log out and back in after `usermod -aG docker "$USER"`.
- KOfam download fails: retry `python bin/tethys-download-kofam-db.py --outdir databases/kofam` on a stable network, or point `--kofam_db` to a shared copy.
- SRA downloads are slow: run `vdb-config --interactive` to configure cache location, and keep the cache on a filesystem with enough free space.
- Human samples: QC and remove host reads before using this workflow.
