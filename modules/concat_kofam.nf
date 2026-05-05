nextflow.enable.types = true

process CONCAT_KOFAM {
  tag "concat_kofam"
  label 'CONCAT_KOFAM'
  conda "envs/build.yml"
  publishDir "${params.outdir}", mode: 'copy', overwrite: true

  input:
  kofam_files: List<Path>

  output:
  annotations: Path = file('build/tethys/annotations.tsv.gz')

  script:
  """
  set -euo pipefail
  mkdir -p build/tethys

  python <<'PY'
import gzip
from pathlib import Path

output_path = Path('build/tethys/annotations.tsv.gz')
files = sorted(Path('.').glob('*.kofam.tsv'))

with gzip.open(output_path, 'wt') as out_handle:
    out_handle.write('id_gene\tid_feature\n')
    for file_path in files:
        header_checked = False
        with file_path.open() as handle:
            for line in handle:
                line = line.rstrip('\n')
                if not line or line.startswith('#'):
                    continue
                fields = line.split('\t')
                if not header_checked and fields[0] in {'id_gene', 'target', 'gene', 'query'}:
                    header_checked = True
                    continue
                header_checked = True
                if len(fields) >= 2:
                    out_handle.write(f"{fields[0]}\t{fields[1]}\n")
PY
  """
}
