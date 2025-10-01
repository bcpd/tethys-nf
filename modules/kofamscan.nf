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
  def t = task.cpus
  def backend = (params.annotation_backend ?: 'pykofamsearch')
  def shellQuote = { str -> str.replace("'", "'\"'\"'") }
  def kofamDirEsc = shellQuote(kofam_dir.toString())
  def faaPathEsc = shellQuote(faa.toString())
  def faaBase = faa.baseName
  def outdirEsc = shellQuote(outdir)
  """
  set -euo pipefail

  outdir='${outdirEsc}'
  mkdir -p "${outdir}"

  kofam_dir='${kofamDirEsc}'
  backend='${backend}'
  threads=${t}
  faa_file='${faaPathEsc}'
  sample_id='${faaBase}'

  echo "[KOFAM] Using ${backend} backend for ${sample_id}" >&2

  if [ "${backend}" = "pykofamsearch" ]; then
    if command -v pykofamsearch >/dev/null 2>&1; then
      PKS=(pykofamsearch)
    elif python -c "import pykofamsearch" >/dev/null 2>&1; then
      PKS=(python -m pykofamsearch)
    else
      echo "[KOFAM] PyKOfamSearch executable not found in PATH and module import failed" >&2
      exit 1
    fi

    set +e
    "${PKS[@]}" \
      -i "${faa_file}" \
      -o "${outdir}/${sample_id}.kofam.tsv" \
      -d "${kofam_dir}" \
      -p ${threads} \
      --no_header
    rc=$?
    set -e
    if [ ${rc} -ne 0 ]; then
      echo "[KOFAM] PyKOfamSearch failed for ${sample_id} (rc=${rc})" >&2
      exit ${rc}
    fi
  else
    echo "[KOFAM] Running KOfamScan for ${sample_id}" >&2
    set +e
    exec_annotation \
      --profile "${kofam_dir}/profiles" \
      --ko-list "${kofam_dir}/ko_list" \
      --cpu ${threads} \
      -f detail-tsv \
      -o "${outdir}/${sample_id}.kofam.tsv" \
      "${faa_file}"
    rc=$?
    set -e
    if [ ${rc} -ne 0 ]; then
      echo "[KOFAM] exec_annotation failed for ${sample_id} (rc=${rc})" >&2
      exit ${rc}
    fi
  fi
  """
}
