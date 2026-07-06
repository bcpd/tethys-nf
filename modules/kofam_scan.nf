nextflow.enable.types = true

def shellQuote(value) {
  return value.toString().replace("'", "'\"'\"'")
}

process KOFAM_SCAN {
  tag "kofam"
  label 'KOFAM_SCAN'
  conda "envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  tuple(faa: Path, kofam_dir: String, annotation_backend: String)

  output:
  kofam: Path = file("build/kofam/${faa.baseName}.kofam.tsv")

  script:
  def outdir = 'build/kofam'
  def threads = task.cpus
  def backend = (annotation_backend ?: 'kofamscan')
  def kofamDirEsc = shellQuote(kofam_dir.toString())
  def faaPathEsc = shellQuote(faa.toString())
  def sampleId = faa.baseName
  def outdirEsc = shellQuote(outdir)
  def stubFlag = new File("${kofam_dir}/.stub").exists()

  if( stubFlag ) {
    return """
    set -euo pipefail

    mkdir -p '${outdirEsc}'
    printf "id_gene\tid_feature\n%s\tK00000\n" '${sampleId}' > '${outdirEsc}/${sampleId}.kofam.tsv'
    """.stripIndent()
  }

  def runPyKofam = """
    if command -v pykofamsearch >/dev/null 2>&1; then
      pykofamsearch \
        -i '${faaPathEsc}' \
        -o '${outdirEsc}/${sampleId}.kofam.tsv' \
        -d '${kofamDirEsc}' \
        -p ${threads} \
        --no_header
    elif python -c "import pykofamsearch" >/dev/null 2>&1; then
      python -m pykofamsearch \
        -i '${faaPathEsc}' \
        -o '${outdirEsc}/${sampleId}.kofam.tsv' \
        -d '${kofamDirEsc}' \
        -p ${threads} \
        --no_header
    else
      echo "[KOFAM] PyKOfamSearch executable not found" >&2
      exit 1
    fi
  """.stripIndent()

  def runExecAnnotation = """
    exec_annotation \
      --profile '${kofamDirEsc}/profiles' \
      --ko-list '${kofamDirEsc}/ko_list' \
      --cpu ${threads} \
      -f detail-tsv \
      -o '${outdirEsc}/${sampleId}.kofam.tsv' \
      '${faaPathEsc}'
  """.stripIndent()

  return """
  set -euo pipefail

  mkdir -p '${outdirEsc}'

  echo "[KOFAM] Using ${backend} backend for ${sampleId}" >&2

  ${backend == 'pykofamsearch' ? runPyKofam : runExecAnnotation}
  """.stripIndent()
}
