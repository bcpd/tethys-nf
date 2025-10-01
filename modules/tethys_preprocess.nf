process TETHYS_PREPROCESS {
  tag "preprocess"
  label 'TETHYS_PREPROCESS'
  conda "envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  path manifest
  path annotations

  output:
  path 'build/tethys/preprocess', emit: preprocess

  script:
  """
  set -eu
  mkdir -p build/tethys/preprocess
  python "${projectDir}/bin/tethys-preprocess.py" \
    -i ${manifest} \
    -a ${annotations} \
    -o build/tethys/preprocess \
    --annotation_format pykofamsearch
  """
}
