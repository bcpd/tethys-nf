nextflow.enable.types = true

process TETHYS_PREPROCESS {
  tag "preprocess"
  label 'TETHYS_PREPROCESS'
  conda "envs/tethys.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  manifest: Path
  annotations: Path

  output:
  preprocess: Path = file('build/tethys/preprocess')

  script:
  """
  set -eu
  export PYTHONPATH="${projectDir}:\${PYTHONPATH:-}"
  mkdir -p build/tethys/preprocess
  python "${projectDir}/bin/tethys-preprocess.py" \
    -i ${manifest} \
    -a ${annotations} \
    -o build/tethys/preprocess \
    --annotation_format pykofamsearch
  """
}
