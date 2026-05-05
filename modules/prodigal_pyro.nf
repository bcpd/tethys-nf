nextflow.enable.types = true

process PRODIGAL_PYRO {
  tag { fasta.baseName }
  conda "${projectDir}/envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  fasta: Path

  output:
  record(
    genome_id: fasta.baseName,
    faa: file("build/prodigal/${fasta.baseName}.faa"),
    ffn: file("build/prodigal/${fasta.baseName}.ffn"),
    gff: file("build/prodigal/${fasta.baseName}.gff")
  )

  script:
  def id = fasta.baseName
  """
  set -euo pipefail
  mkdir -p build/prodigal

  PYRO=pyrodigal
  command -v "\$PYRO" >/dev/null 2>&1 || PYRO="python -m pyrodigal.cli"

  "\$PYRO" \
    -i "${fasta}" \
    -a "build/prodigal/${id}.faa" \
    -d "build/prodigal/${id}.ffn" \
    -j ${task.cpus} \
    -p meta \
    | python "${projectDir}/bin/append_geneid_to_prodigal_gff.py" > "build/prodigal/${id}.gff"
  """
}
