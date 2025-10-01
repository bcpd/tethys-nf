process MERGE_ARTIFACTS {
  conda "${projectDir}/envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
    val outdir
    val _barrier

  output:
    path "artifacts/*.nc"

  script:
  """
  set -euo pipefail
  mkdir -p artifacts
  python "${projectDir}/bin/tethys-merge.py" \
    --taxonomic_profiling_directory "${outdir}/profile/tax" \
    --pathway_profiling_directory   "${outdir}/profile/func" \
    --output_directory artifacts \
    -e h5netcdf -c 4
  """
}
