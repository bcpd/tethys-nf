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
  def stubMode = new File("${kofam_dir}/.stub").exists() ? '1' : '0'
  """
  set -euo pipefail

  outdir='${outdirEsc}'
  mkdir -p "${outdir}"

  kofam_dir='${kofamDirEsc}'
  backend='${backend}'
  threads=${threads}
  faa_file='${faaPathEsc}'
  sample_id='${sampleId}'
  stub_mode='${stubMode}'

  if [ "${'$'}{stub_mode}" = "1" ]; then
    printf "id_gene\tid_feature\n%s\tK00000\n" "${'$'}{sample_id}" > "${'$'}{outdir}/${'$'}{sample_id}.kofam.tsv"
    exit 0
  fi

  echo "[KOFAM] Using ${backend} backend for ${sampleId}" >&2

  if [ "${backend}" = "pykofamsearch" ]; then
    if command -v pykofamsearch >/dev/null 2>&1; then
      PKS=(pykofamsearch)
    elif python -c "import pykofamsearch" >/dev/null 2>&1; then
      PKS=(python -m pykofamsearch)
    else
      echo "[KOFAM] PyKOfamSearch executable not found" >&2
      exit 1
    fi

    set +e
    "${'$'}{PKS[@]}" \
      -i "${'$'}{faa_file}" \
      -o "${'$'}{outdir}/${'$'}{sample_id}.kofam.tsv" \
      -d "${'$'}{kofam_dir}" \
      -p ${threads} \
      --no_header
    rc=${'$'}?
    set -e
    if [ ${'$'}{rc} -ne 0 ]; then
      echo "[KOFAM] PyKOfamSearch failed for ${sampleId} (rc=${'$'}{rc})" >&2
      exit ${'$'}{rc}
    fi
  else
    set +e
    exec_annotation \
      --profile "${'$'}{kofam_dir}/profiles" \
      --ko-list "${'$'}{kofam_dir}/ko_list" \
      --cpu ${threads} \
      -f detail-tsv \
      -o "${'$'}{outdir}/${'$'}{sample_id}.kofam.tsv" \
      "${'$'}{faa_file}"
    rc=${'$'}?
    set -e
    if [ ${'$'}{rc} -ne 0 ]; then
      echo "[KOFAM] exec_annotation failed for ${sampleId} (rc=${'$'}{rc})" >&2
      exit ${'$'}{rc}
    fi
  fi
  """
}
