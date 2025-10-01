process CLUSTER_SKANI {
  tag "skani"
  label 'CLUSTER_SKANI'
  conda "envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  path fasta

  output:
  path 'build/clusters/genome_clusters.tsv', emit: clusters
  path 'build/clusters/representatives.tsv', emit: representatives

  script:
  def outdir = 'build/clusters'
  def flist = "genomes.list"
  def ids   = "genome_ids.tsv"
  def min_af = 15
  def s = 80
  def c = 125
  def m = 1000
  def t = task.cpus
  def prefix = 'PSLC-'
  """
  set -euo pipefail
  mkdir -p ${outdir}

  python <<'PY'
from pathlib import Path

inputs = []
for entry in Path('.').iterdir():
    if entry.is_file() and entry.suffix.lower() in {'.fna', '.fa', '.fasta'}:
        inputs.append(entry.resolve())

inputs.sort()

with open('${flist}', 'w') as fh:
    for path in inputs:
        fh.write(f"{path}\n")

with open('${ids}', 'w') as fh:
    for path in inputs:
        fh.write(f"{path.name}\t{path}\n")
PY

  skani triangle --sparse -t ${t} -o skani_output.tsv -l ${flist} \
    --min-af ${min_af} -s ${s} -c ${c} -m ${m} --ci \
    || { echo "[CLUSTER_SKANI] skani produced no sketches; continuing with empty edge list" >&2; \
         printf "q\ts\tani\taf\trest\n" > skani_output.tsv; }

  python "${projectDir}/bin/edgelist_to_clusters.py" --basename -t 95 -a 50 --af_mode relaxed \
      --cluster_prefix ${prefix} \
      -o ${outdir}/genome_clusters.tsv \
      --identifiers ${ids} \
      --export_graph ${outdir}/networkx_graph.pkl \
      --export_dict  ${outdir}/dict.pkl \
      --export_representatives ${outdir}/representatives.tsv < <(cut -f1-5 skani_output.tsv | tail -n +2)
  """
}
