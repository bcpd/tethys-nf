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
  def dbDir = file(checkm2_param ?: (env('CHECKM2DB') ?: "${projectDir}/databases/checkm2")).toString()
  def dbDirEsc = shellQuote(dbDir)
  task.ext.verified_dir = dbDir

  """
  set -euo pipefail

  db_dir='${dbDirEsc}'
  dmnd_glob="\$db_dir/CheckM2_database/*.dmnd"

  mkdir -p "\$db_dir"

  if ! compgen -G "\$dmnd_glob" > /dev/null; then
    tries=0
    max_tries=5
    until compgen -G "\$dmnd_glob" > /dev/null; do
      tries=\$((tries+1))
      echo "[VERIFY_CHECKM2_DB] Download attempt \$tries/\$max_tries..." >&2
      checkm2 database --download --path "\$db_dir" || true
      if compgen -G "\$dmnd_glob" > /dev/null; then
        break
      fi
      if [ "\$tries" -ge "\$max_tries" ]; then
        echo "[VERIFY_CHECKM2_DB] Failed to provision CheckM2 database in '\$db_dir'." >&2
        exit 1
      fi
      sleep 20
    done
  fi

  if ! compgen -G "\$dmnd_glob" > /dev/null; then
    echo "[VERIFY_CHECKM2_DB] No DIAMOND database found after download attempts." >&2
    exit 1
  fi

  echo "[VERIFY_CHECKM2_DB] Using database directory: \$db_dir" >&2
  """.stripIndent()
}
