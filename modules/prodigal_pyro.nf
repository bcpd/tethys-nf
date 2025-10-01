process PRODIGAL_PYRO {
  tag { fasta.baseName }
  conda "${projectDir}/envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  path fasta

  output:
  path "build/prodigal/*.faa", emit: faa
  path "build/prodigal/*.ffn", emit: ffn
  path "build/prodigal/*.gff", emit: gff

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

