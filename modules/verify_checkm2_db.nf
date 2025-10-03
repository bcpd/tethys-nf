process VERIFY_CHECKM2_DB {
  tag "checkm2_db"
  label 'VERIFY_CHECKM2_DB'
  conda "envs/checkm2.yml"

  input:
  val checkm2_param

  output:
  val task.ext.verified_dir, emit: db_dir

  script:
  def shellQuote = { str -> str.replace("'", "'\"'\"'") }
  def dbDir = (checkm2_param ?: (System.getenv('CHECKM2DB') ?: "${projectDir}/databases/checkm2")).toString()
  def dbDirEsc = shellQuote(dbDir)
  task.ext.verified_dir = dbDir
  """
  set -euo pipefail

  db_dir='${dbDirEsc}'
  dmnd_glob="\${db_dir}/CheckM2_database/*.dmnd"

  mkdir -p "\${db_dir}"

  if ! compgen -G "\${dmnd_glob}" > /dev/null; then
    tries=0
    max_tries=5
    until compgen -G "\${dmnd_glob}" > /dev/null; do
      tries=${'$'}((tries+1))
      echo "[VERIFY_CHECKM2_DB] Download attempt \${tries}/\${max_tries}…" >&2
      checkm2 database --download --path "\${db_dir}" || true
      if [ "\${tries}" -ge "\${max_tries}" ]; then
        echo "[VERIFY_CHECKM2_DB] Failed to provision CheckM2 database in \${db_dir}." >&2
        exit 1
      fi
      sleep 20
    done
  fi

  if ! compgen -G "\${dmnd_glob}" > /dev/null; then
    echo "[VERIFY_CHECKM2_DB] No DIAMOND database found after download attempts." >&2
    exit 1
  fi

  echo "[VERIFY_CHECKM2_DB] Using database directory: \${db_dir}" >&2
  """
}
