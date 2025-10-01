process BUILD_MANIFEST {
  tag "manifest"
  label 'BUILD_MANIFEST'
  conda "envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  path genomes
  path clusters

  output:
  path 'build/tethys/manifest.tsv', emit: manifest

  script:
  def cl = clusters
  def shellQuote = { str -> str.replace("'", "'\"'\"'") }
  def clusterPathEsc = shellQuote(cl.toString())
  """
  set -euo pipefail
  mkdir -p build/tethys

  python <<'PY'
from pathlib import Path

inputs = []
for entry in Path('.').iterdir():
    if entry.is_file() and entry.suffix.lower() in {'.fna', '.fa', '.fasta'}:
        inputs.append(entry.resolve())

inputs.sort()

with open('genome_paths.list', 'w') as fh:
    for path in inputs:
        fh.write(f"{path}\n")
PY

  python "${projectDir}/bin/tethys-build-manifest.py" \
    --genomes_list genome_paths.list \
    --clusters '${clusterPathEsc}' \
    --prodigal_dir build/prodigal \
    -o build/tethys/manifest.tsv
  """
}
