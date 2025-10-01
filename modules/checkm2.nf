process CHECKM2 {
  tag "checkm2"
  label 'CHECKM2'
  conda "envs/checkm2.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  path faa

  output:
  path "build/checkm2", emit: summary

  script:
  def indir = 'build/faa_dir'
  def outdir = 'build/checkm2'
  def t = task.cpus
  // Choose DB directory: prefer params.checkm2_db, else $CHECKM2DB, else project-local cache
  def db_dir = params.checkm2_db ?: (System.getenv('CHECKM2DB') ?: "${projectDir}/databases/checkm2")
  def shellQuote = { str -> str.replace("'", "'\"'\"'") }
  def dbDirEsc = shellQuote(db_dir.toString())
  def indirEsc = shellQuote(indir)
  def outdirEsc = shellQuote(outdir)
  def dmnd_glob = "${db_dir}/CheckM2_database/*.dmnd"
  def dmndGlobEsc = shellQuote(dmnd_glob)
  """
  set -euo pipefail
  mkdir -p '${indirEsc}' '${outdirEsc}' '${dbDirEsc}'

  python <<'PY'
from pathlib import Path

workdir = Path('.')
indir = Path('${indir}')
indir.mkdir(parents=True, exist_ok=True)

faa_inputs = []
for entry in workdir.iterdir():
    if entry.is_file() and entry.suffix.lower() == '.faa':
        faa_inputs.append(entry.resolve())

faa_inputs.sort()

for src in faa_inputs:
    dest = indir / src.name
    if dest.exists():
        continue
    try:
        dest.symlink_to(src)
    except FileExistsError:
        pass
PY

  # Resolve CheckM2 database; download with retries if missing (large download from Zenodo)
  db_file=""
  if compgen -G '${dmndGlobEsc}' > /dev/null; then
    db_file=`ls '${dmnd_glob}' | head -n 1`
  else
    echo "[CHECKM2] Database not found in ${db_dir}; attempting download (this is large)." >&2
    tries=0; max_tries=5
    until compgen -G '${dmndGlobEsc}' > /dev/null; do
      let tries+=1 || true
      echo "[CHECKM2] Download attempt \${tries}/\${max_tries}…" >&2
      # Let checkm2 handle resuming internally if supported
      checkm2 database --download --path "${db_dir}" || true
      if [ \${tries} -ge \${max_tries} ]; then
        echo "[CHECKM2] Failed to download database after \${max_tries} attempts. You can pre-download manually with:\n  checkm2 database --download --path \"${db_dir}\"\nThen rerun with -resume." >&2
        exit 1
      fi
      # small backoff
      sleep 20
    done
    db_file=`ls '${dmnd_glob}' | head -n 1`
  fi

  echo "[CHECKM2] Using database: \${db_file}" >&2
  checkm2 predict -i '${indir}' -o '${outdir}' --threads ${t} --genes -x faa --database_path "\${db_file}"
  """
}
