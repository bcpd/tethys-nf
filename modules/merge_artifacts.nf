nextflow.enable.types = true

process MERGE_ARTIFACTS {
  conda "${projectDir}/envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true
  // Published tables can change without changing the parent directory's cache key.
  cache (params.mode != 'merge')

  input:
  tax_profiles: List<Path>
  func_profiles: List<Path>
  index_dir: Path?

  stage:
  stageAs tax_profiles, 'tax/*'
  stageAs func_profiles, 'func/*'
  stageAs index_dir, 'index'

  output:
  artifacts: Set<Path> = files("artifacts/*.nc")

  script:
  def index_arg = index_dir ? '--index_directory index' : ''
  """
  set -euo pipefail
  export PYTHONPATH="${projectDir}:\${PYTHONPATH:-}"
  mkdir -p artifacts
  python "${projectDir}/bin/tethys-merge.py" \
    --taxonomic_profiling_directory tax \
    --pathway_profiling_directory func \
    ${index_arg} \
    --output_directory artifacts \
    -e h5netcdf -c 4
  """
}
