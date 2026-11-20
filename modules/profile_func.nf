nextflow.enable.types = true

def shellQuote(value) {
  return "'" + value.toString().replace("'", "'\"'\"'") + "'"
}

process PROFILE_FUNC {
  tag { sample_id }
  label 'PROFILE_FUNC'
  conda "${projectDir}/envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  record(
    sample_id: String,
    fastq_1: Path,
    fastq_2: Path
  )
  index_dir: Path
  index_revision: List<String>

  stage:
  stageAs fastq_1, 'reads_1.fastq.gz'
  stageAs fastq_2, 'reads_2.fastq.gz'
  stageAs index_dir, 'index'

  output:
  tables: Set<Path> = files("profile/func/${sample_id}/output/*")

  script:
  def outdir = "profile/func"
  def stagedFastq1 = 'reads_1.fastq.gz'
  def stagedFastq2 = 'reads_2.fastq.gz'
  """
  set -euo pipefail
  export PYTHONPATH=${shellQuote(projectDir)}:\${PYTHONPATH:-}
  outdir=${shellQuote(outdir)}
  sample=${shellQuote(sample_id)}
  mkdir -p "\$outdir/\$sample"
  python ${shellQuote("${projectDir}/bin/tethys-profile-pathway.py")} \
    -1 ${shellQuote(stagedFastq1)} -2 ${shellQuote(stagedFastq2)} -n sample \
    -d ${shellQuote(index_dir)} -p ${shellQuote(task.cpus)} \
    --salmon_include_mappings --alignment_format sam \
    -o profiling

  mv profiling/sample/output "\$outdir/\$sample/"
  """
}
