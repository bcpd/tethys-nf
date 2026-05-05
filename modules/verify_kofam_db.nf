nextflow.enable.types = true

def shellQuote(value) {
  return value.toString().replace("'", "'\"'\"'")
}

process VERIFY_KOFAM_DB {
  tag "kofam_db"
  label 'VERIFY_KOFAM_DB'
  conda "envs/build.yml"

  input:
  kofam_param: String?

  output:
  db_dir: String = task.ext.verified_dir

  script:
  def dbDir = (kofam_param ?: "${projectDir}/databases/kofam").toString()
  def dbDirEsc = shellQuote(dbDir)
  def downloaderEsc = shellQuote("${projectDir}/bin/tethys-download-kofam-db.py")
  def stubFlag = new File("${dbDir}/.stub").exists()
  task.ext.verified_dir = dbDir

  if( stubFlag ) {
    return """
    set -euo pipefail

    mkdir -p '${dbDirEsc}/profiles'
    touch '${dbDirEsc}/ko_list'
    """.stripIndent()
  }

  """
  set -euo pipefail

  mkdir -p '${dbDirEsc}'

  need_db=0
  if [ ! -d '${dbDirEsc}/profiles' ] || [ ! -f '${dbDirEsc}/ko_list' ]; then
    need_db=1
  else
    sample_bad=0
    count=0
    while IFS= read -r -d '' hmm_file; do
      [ -z "\$hmm_file" ] && continue
      count=\$((count+1))
      if ! head -c 12 "\$hmm_file" | grep -q "HMMER3"; then
        sample_bad=1
        break
      fi
      if python -c "import sys; data=open(sys.argv[1],'rb').read(4096); sys.exit(0 if 0 in data else 1)" \"\$hmm_file\"; then
        sample_bad=1
        break
      fi
      if [ "\$count" -ge 500 ]; then
        break
      fi
    done < <(find '${dbDirEsc}/profiles' -type f -name "*.hmm" -print0 2>/dev/null || true)

    hmm_n=\$(find '${dbDirEsc}/profiles' -type f -name "*.hmm" 2>/dev/null | wc -l | tr -d '[:space:]')
    if [ -z "\$hmm_n" ]; then
      hmm_n=0
    fi
    if [ "\$count" -eq 0 ] || [ "\$sample_bad" -eq 1 ] || [ "\$hmm_n" -lt 500 ]; then
      need_db=1
    fi
  fi

  if [ "\$need_db" -eq 1 ]; then
    echo "[VERIFY_KOFAM_DB] Database missing or invalid in ${dbDir}. Attempting download/repair..." >&2
    python '${downloaderEsc}' --outdir '${dbDirEsc}' || {
      echo "[VERIFY_KOFAM_DB] Auto-download failed. Please download KOfam DB manually into ${dbDir}." >&2
      exit 1
    }
  fi

  if [ -d '${dbDirEsc}/profiles' ]; then
    bad=0
    count=0
    while IFS= read -r -d '' hmm_file; do
      [ -z "\$hmm_file" ] && continue
      if ! hmmstat "\$hmm_file" >/dev/null 2>&1; then
        bad=1
        break
      fi
      count=\$((count+1))
      if [ "\$count" -ge 500 ]; then
        break
      fi
    done < <(find '${dbDirEsc}/profiles' -type f -name "*.hmm" -print0 2>/dev/null || true)

    if [ "\$bad" -eq 1 ]; then
      echo "[VERIFY_KOFAM_DB] Detected invalid HMM profile(s) via hmmstat. Refreshing KOfam DB..." >&2
      rm -rf '${dbDirEsc}/profiles' || true
      rm -f '${dbDirEsc}/profiles.tar.gz' || true
      python '${downloaderEsc}' --outdir '${dbDirEsc}' || {
        echo "[VERIFY_KOFAM_DB] Auto-download/repair failed. Please (re)download KOfam DB manually into ${dbDir}." >&2
        exit 1
      }
    fi
  fi
  """.stripIndent()
}
