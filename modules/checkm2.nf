nextflow.enable.types = true

def shellQuote(value) {
  return value.toString().replace("'", "'\"'\"'")
}

process CHECKM2 {
  tag "checkm2"
  label 'CHECKM2'
  conda "envs/checkm2.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true
  errorStrategy 'retry'
  maxRetries 2

  input:
  tuple(faa_files: List<Path>, db_dir: String)

  output:
  summary: Path = file("build/checkm2")

  script:
  if( !faa_files || faa_files.isEmpty() ) {
    throw new IllegalArgumentException('CHECKM2 received no FAA files to evaluate')
  }
  def indir = 'build/faa_dir'
  def outdir = 'build/checkm2'
  def dmndGlob = "${db_dir}/CheckM2_database/*.dmnd"
  def linkCmds = faa_files.collect { file ->
    def src = shellQuote(file.toString())
    def dst = shellQuote("${indir}/${file.getName()}")
    "ln -sf '${src}' '${dst}' || cp '${src}' '${dst}'"
  }.join('\n')
  def dmndGlobEsc = shellQuote(dmndGlob)
  def indirEsc = shellQuote(indir)
  def outdirEsc = shellQuote(outdir)
  def dbDirEsc = shellQuote(db_dir.toString())
  def threads = task.cpus

  """
  set -euo pipefail
  mkdir -p '${indirEsc}' '${outdirEsc}'

  ${linkCmds}

  dmnd_file=\$(ls '${dmndGlobEsc}' | head -n 1)
  if [ -z "\$dmnd_file" ]; then
    echo "[CHECKM2] Unable to locate DIAMOND database under '${dbDirEsc}'" >&2
    exit 1
  fi

  checkm2 predict -i '${indirEsc}' -o '${outdirEsc}' --threads ${threads} --genes -x faa --database_path "\$dmnd_file"
  """.stripIndent()
}
