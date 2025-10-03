process KOFAM_SCAN {
  tag "kofam"
  label 'KOFAM_SCAN'
  conda "envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  tuple path(faa), val(kofam_dir)

  output:
  path 'build/kofam/*.kofam.tsv', emit: kofam

  script:
  def outdir = 'build/kofam'
  def threads = task.cpus
  def backend = (params.annotation_backend ?: 'pykofamsearch')
  def shellQuote = { str -> str.replace("'", "'\"'\"'") }
  def kofamDirEsc = shellQuote(kofam_dir.toString())
  def faaPathEsc = shellQuote(faa.toString())
  def sampleId = faa.baseName
  def outdirEsc = shellQuote(outdir)
  def stubMode = new File("${kofam_dir}/.stub").exists()

  if( stubMode ) {
    return """
    set -euo pipefail

    outdir='${outdirEsc}'
    mkdir -p "${outdir}"

    printf "id_gene\tid_feature\n%s\tK00000\n" "${sampleId}" > "${outdir}/${sampleId}.kofam.tsv"
    """
  }

  def pykofam = """
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
  """

  def execAnnotation = """
    exec_annotation \
      --profile '${kofamDirEsc}/profiles' \
      --ko-list '${kofamDirEsc}/ko_list' \
      --cpu ${threads} \
      -f detail-tsv \
      -o '${outdirEsc}/${sampleId}.kofam.tsv' \
      '${faaPathEsc}'
  """

  return """
  set -euo pipefail

  outdir='${outdirEsc}'
  mkdir -p "${outdir}"

  echo "[KOFAM] Using ${backend} backend for ${sampleId}" >&2

  ${backend == 'pykofamsearch' ? pykofam.stripIndent() : execAnnotation.stripIndent()}
  """
}
