nextflow.enable.types = true

def shellQuote(value) {
  return value.toString().replace("'", "'\"'\"'")
}

process BUILD_MANIFEST {
  tag "manifest"
  label 'BUILD_MANIFEST'
  conda "envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  genome_paths: List<String>
  ffn_files: List<Path>
  clusters: Path

  stage:
  stageAs ffn_files, 'build/prodigal/*'

  output:
  manifest: Path = file('build/tethys/manifest.tsv')

  script:
  if( !genome_paths || genome_paths.isEmpty() ) {
    throw new IllegalArgumentException('BUILD_MANIFEST received no genome paths')
  }
  if( !ffn_files || ffn_files.isEmpty() ) {
    throw new IllegalArgumentException('BUILD_MANIFEST received no Prodigal FFN files')
  }
  def cl = clusters
  def clusterPathEsc = shellQuote(cl.toString())
  def genomePathsText = genome_paths.collect { path -> path.toString() }.join('\n') + '\n'
  def genomePathsEsc = shellQuote(genomePathsText)
  """
  set -euo pipefail
  mkdir -p build/tethys

  printf '%s' '${genomePathsEsc}' > genome_paths.list

  python "${projectDir}/bin/tethys-build-manifest.py" \
    --genomes_list genome_paths.list \
    --clusters '${clusterPathEsc}' \
    --prodigal_dir build/prodigal \
    -o build/tethys/manifest.tsv
  """
}
