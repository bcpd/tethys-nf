nextflow.enable.types = true

def shellQuote(value) {
  return value.toString().replace("'", "'\"'\"'")
}

process VERIFY_CHECKM2_DB {
  tag "checkm2_db"
  label 'VERIFY_CHECKM2_DB'
  conda "envs/checkm2.yml"

  input:
  checkm2_param: String?

  output:
  db_dir: String = task.ext.verified_dir

  script:
  def dbDir = (checkm2_param ?: (env('CHECKM2DB') ?: "${projectDir}/databases/checkm2")).toString()
  def dbDirEsc = shellQuote(dbDir)
  task.ext.verified_dir = dbDir

  """
  set -euo pipefail

  dmnd_glob='${dbDirEsc}/CheckM2_database/*.dmnd'

  mkdir -p '${dbDirEsc}'

  if ! compgen -G "\$dmnd_glob" > /dev/null; then
    tries=0
    max_tries=5
    until compgen -G "\$dmnd_glob" > /dev/null; do
      tries=\$((tries+1))
      echo "[VERIFY_CHECKM2_DB] Download attempt \$tries/\$max_tries..." >&2
      checkm2 database --download --path '${dbDirEsc}' || true
      if [ "\$tries" -ge "\$max_tries" ]; then
        echo "[VERIFY_CHECKM2_DB] Failed to provision CheckM2 database in ${dbDir}." >&2
        exit 1
      fi
      sleep 20
    done
  fi

  if ! compgen -G "\$dmnd_glob" > /dev/null; then
    echo "[VERIFY_CHECKM2_DB] No DIAMOND database found after download attempts." >&2
    exit 1
  fi

  echo "[VERIFY_CHECKM2_DB] Using database directory: ${dbDir}" >&2
  """.stripIndent()
}
