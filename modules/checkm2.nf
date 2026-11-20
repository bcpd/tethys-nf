nextflow.enable.types = true

process CHECKM2 {
  tag "checkm2"
  label 'CHECKM2'
  conda "envs/checkm2.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true
  errorStrategy 'retry'
  maxRetries 2

  input:
  tuple(faa_files: List<Path>, db_dir: String)

  stage:
  stageAs faa_files, 'faa/*'

  output:
  summary: Path = file("build/checkm2")

  script:
  if( !faa_files || faa_files.isEmpty() ) {
    throw new IllegalArgumentException('CHECKM2 received no FAA files to evaluate')
  }
  def outdir = 'build/checkm2'
  def dbDirEsc = db_dir.replace("'", "'\"'\"'")

  """
  set -euo pipefail
  mkdir -p '${outdir}'
  db_dir='${dbDirEsc}'

  dmnd_file=''
  for candidate in "\$db_dir"/CheckM2_database/*.dmnd; do
    if [ -f "\$candidate" ]; then
      dmnd_file=\$candidate
      break
    fi
  done
  if [ -z "\$dmnd_file" ]; then
    echo "[CHECKM2] Unable to locate DIAMOND database under '\$db_dir'" >&2
    exit 1
  fi

  checkm2 predict -i faa -o '${outdir}' --threads ${task.cpus} --genes -x faa --database_path "\$dmnd_file"
  """.stripIndent()
}
