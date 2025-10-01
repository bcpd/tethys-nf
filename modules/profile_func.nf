process PROFILE_FUNC {
  tag { sample_id }
  label 'PROFILE_FUNC'
  conda "${projectDir}/envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  tuple val(sample_id), path(reads)
  val index_dir

  output:
  path "profile/func/sample=${sample_id}/output/*"
  path ".done", emit: done

  script:
  def r1 = reads.find{ it.name =~ /R1/ }
  def r2 = reads.find{ it.name =~ /R2/ }
  """
  set -euo pipefail
  outdir=profile/func/sample=${sample_id}
  mkdir -p "$outdir"
  python "${projectDir}/bin/tethys-profile-pathway.py" \
    -1 ${r1} -2 ${r2} -n ${sample_id} \
    -d ${index_dir} -p ${task.cpus} \
    --salmon_include_mappings --alignment_format sam \
    -o "$outdir"
  touch .done
  """
}
