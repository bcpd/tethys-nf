nextflow.enable.types = true

process TETHYS_INDEX {
  tag "index"
  label 'TETHYS_INDEX'
  conda "envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  preprocess_dir: Path
  pathway_db: String?

  output:
  index: Path = file('build/tethys/index')

  script:
  def f = "build/tethys/preprocess/cds.fasta.gz"
  def m = "build/tethys/preprocess/feature_mapping.tsv.gz"
  def g = "build/tethys/preprocess/genomes.tsv.gz"
  def pdb = pathway_db ? "--pathway_database ${pathway_db}" : ''
  """
  set -eu
  mkdir -p build/tethys/index
  python "${projectDir}/bin/tethys-index.py" \
    -f ${f} \
    -m ${m} \
    -g ${g} \
    -d build/tethys/index \
    -p ${task.cpus} \
    ${pdb}
  """
}
