nextflow.enable.types = true

def shellQuote(value) {
  return "'" + value.toString().replace("'", "'\"'\"'") + "'"
}

process PROFILE_TAX {
  tag { sample_id }
  label 'PROFILE_TAX'
  conda "${projectDir}/envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  record(
    sample_id: String,
    fastq_1: Path,
    fastq_2: Path
  )
  index_dir: String

  output:
  record(
    sample_id: sample_id,
    outputs: files("profile/tax/sample=${sample_id}/output/*"),
    done: file(".done")
  )
  
  script:
  if( fastq_1.toString() == fastq_2.toString() ) {
    throw new IllegalArgumentException("R1 and R2 resolved to the same staged path for sample '${sample_id}': ${fastq_1}")
  }
  def outdir = "profile/tax/sample=${sample_id}"
  """
  set -euo pipefail
  export PYTHONPATH=${shellQuote(projectDir)}:\${PYTHONPATH:-}
  outdir=${shellQuote(outdir)}
  mkdir -p "\$outdir"

  python ${shellQuote("${projectDir}/bin/tethys-profile-taxonomy.py")} \
    -1 ${shellQuote(fastq_1)} -2 ${shellQuote(fastq_2)} -n ${shellQuote(sample_id)} \
    -d ${shellQuote(index_dir)} -p ${shellQuote(task.cpus)} \
    -o "\$outdir"

  touch .done
  """
}
