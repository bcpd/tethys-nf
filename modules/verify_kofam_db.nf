process VERIFY_KOFAM_DB {
  tag "kofam_db"
  label 'VERIFY_KOFAM_DB'
  conda "envs/build.yml"

  input:
  val kofam_param

  output:
  val task.ext.verified_dir, emit: db_dir

  script:
  def shellQuote = { str -> str.replace("'", "'\"'\"'") }
  def dbDir = (kofam_param ?: "${projectDir}/databases/kofam").toString()
  def dbDirEsc = shellQuote(dbDir)
  def downloaderPath = shellQuote("${projectDir}/bin/tethys-download-kofam-db.py")
  def stubFlag = new File("${dbDir}/.stub").exists()
  def stubEnv = stubFlag ? '1' : '0'
  task.ext.verified_dir = dbDir
  """
  set -euo pipefail

  db_dir='${dbDirEsc}'
  downloader='${downloaderPath}'
  stub_mode='${stubEnv}'

  if [ "${stub_mode}" = "1" ]; then
    mkdir -p "${db_dir}/profiles"
    touch "${db_dir}/ko_list"
    exit 0
  fi

  mkdir -p "${db_dir}"

  need_db=0
  if [ ! -d "${db_dir}/profiles" ] || [ ! -f "${db_dir}/ko_list" ]; then
    need_db=1
  else
    sample_bad=0
    count=0
    while IFS= read -r -d '' hmm_file; do
      [ -z "${hmm_file}" ] && continue
      count=$((count+1))
      if ! head -c 12 "${hmm_file}" | grep -q "HMMER3"; then
        sample_bad=1
        break
      fi
      if python - "${hmm_file}" <<'PY'
import sys
with open(sys.argv[1], "rb") as handle:
    data = handle.read(4096)
sys.exit(0 if b"\x00" in data else 1)
PY
      then
        sample_bad=1
        break
      fi
      if [ "${count}" -ge 500 ]; then
        break
      fi
    done < <(find "${db_dir}/profiles" -type f -name "*.hmm" -print0 2>/dev/null || true)

    hmm_n=$(find "${db_dir}/profiles" -type f -name "*.hmm" 2>/dev/null | wc -l | tr -d '[:space:]')
    if [ -z "${hmm_n}" ]; then
      hmm_n=0
    fi
    if [ "${count}" -eq 0 ] || [ "${sample_bad}" -eq 1 ] || [ "${hmm_n}" -lt 500 ]; then
      need_db=1
    fi
  fi

  if [ "${need_db}" -eq 1 ]; then
    echo "[VERIFY_KOFAM_DB] Database missing or invalid in ${db_dir}. Attempting download/repair…" >&2
    python "${downloader}" --outdir "${db_dir}" || {
      echo "[VERIFY_KOFAM_DB] Auto-download failed. Please download KOfam DB manually into ${db_dir}." >&2
      exit 1
    }
  fi

  if [ -d "${db_dir}/profiles" ]; then
    bad=0
    count=0
    while IFS= read -r -d '' hmm_file; do
      [ -z "${hmm_file}" ] && continue
      if ! hmmstat "${hmm_file}" >/dev/null 2>&1; then
        bad=1
        break
      fi
      count=$((count+1))
      if [ "${count}" -ge 500 ]; then
        break
      fi
    done < <(find "${db_dir}/profiles" -type f -name "*.hmm" -print0 2>/dev/null || true)

    if [ "${bad}" -eq 1 ]; then
      echo "[VERIFY_KOFAM_DB] Detected invalid HMM profile(s) via hmmstat. Refreshing KOfam DB…" >&2
      rm -rf "${db_dir}/profiles" || true
      rm -f "${db_dir}/profiles.tar.gz" || true
      python "${downloader}" --outdir "${db_dir}" || {
        echo "[VERIFY_KOFAM_DB] Auto-download/repair failed. Please (re)download KOfam DB manually into ${db_dir}." >&2
        exit 1
      }
    fi
  fi
  """
}
