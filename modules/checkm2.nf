process CHECKM2 {
  tag "checkm2"
  label 'CHECKM2'
  conda "envs/checkm2.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true
  errorStrategy 'retry'
  maxRetries 2

  input:
  tuple path(faa_files), val(db_dir)

  output:
  path "build/checkm2", emit: summary

  script:
  if( !faa_files || faa_files.isEmpty() ) {
    throw new IllegalArgumentException('CHECKM2 received no FAA files to evaluate')
  }
  def indir = 'build/faa_dir'
  def outdir = 'build/checkm2'
  def dmndGlob = "${db_dir}/CheckM2_database/*.dmnd"
  def shellQuote = { str -> str.replace("'", "'\"'\"'") }
  def linkCmds = faa_files.collect { file ->
    def src = shellQuote(file.toString())
    def dst = shellQuote("${indir}/${file.getName()}")
    "ln -sf '${src}' '${dst}' || cp '${src}' '${dst}'"
  }.join('\n')
  def dmndGlobEsc = shellQuote(dmndGlob)
  def indirEsc = shellQuote(indir)
  def outdirEsc = shellQuote(outdir)
  def threads = task.cpus
  def dbDirEsc = shellQuote(db_dir.toString())
  """
  set -euo pipefail
  db_dir='${dbDirEsc}'
  mkdir -p '${indirEsc}' '${outdirEsc}'

  ${linkCmds}

  dmnd_file=$(ls '${dmndGlobEsc}' | head -n 1)
  if [ -z "${dmnd_file}" ]; then
    echo "[CHECKM2] Unable to locate DIAMOND database under '${dbDirEsc}'" >&2
    exit 1
  fi

  checkm2 predict -i '${indirEsc}' -o '${outdirEsc}' --threads ${threads} --genes -x faa --database_path "${dmnd_file}"
  """
}
