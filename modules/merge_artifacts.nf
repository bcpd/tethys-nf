nextflow.enable.types = true

process MERGE_ARTIFACTS {
  conda "${projectDir}/envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  outdir: String
  done_files: List<Path>
  index_dir: String

  output:
  artifacts: Set<Path> = files("artifacts/*.nc")

  script:
  """
  set -euo pipefail
  export PYTHONPATH="${projectDir}:\${PYTHONPATH:-}"
  mkdir -p artifacts
  python "${projectDir}/bin/tethys-merge.py" \
    --taxonomic_profiling_directory "${outdir}/profile/tax" \
    --pathway_profiling_directory   "${outdir}/profile/func" \
    --index_directory "${index_dir}" \
    --output_directory artifacts \
    -e h5netcdf -c 4
  """
}
