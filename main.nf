nextflow.enable.types = true

/******************************************************
 * Tethys-NF: Nextflow DSL2 pipeline (build | profile | merge | all)
 ******************************************************/

include { CLUSTER_SKANI        } from './modules/cluster_skani.nf'
include { PRODIGAL_PYRO        } from './modules/prodigal_pyro.nf'
include { CONCAT_KOFAM         } from './modules/concat_kofam.nf'
include { BUILD_MANIFEST       } from './modules/build_manifest.nf'
include { TETHYS_PREPROCESS    } from './modules/tethys_preprocess.nf'
include { TETHYS_INDEX         } from './modules/tethys_index.nf'
include { VERIFY_KOFAM_DB      } from './modules/verify_kofam_db.nf'
include { KOFAM_SCAN           } from './modules/kofam_scan.nf'
include { VERIFY_CHECKM2_DB    } from './modules/verify_checkm2_db.nf'
include { CHECKM2              } from './modules/checkm2.nf'
include { PROFILE_TAX          } from './modules/profile_tax.nf'
include { PROFILE_FUNC         } from './modules/profile_func.nf'
include { MERGE_ARTIFACTS      } from './modules/merge_artifacts.nf'

params {
  mode: String = 'all'
  genomes_dir: String? = null
  samplesheet: Path? = null
  reads: String? = null
  outdir: String = 'results'
  threads: Integer = 8
  kofam_db: String? = null
  annotation_backend: String = 'kofamscan'
  checkm2_db: String? = null
  pathway_db: String? = null
  index_dir: String? = null
  skip_checkm2: Boolean = false
  kofam_cpus: Integer? = null
}

record SampleReads {
  sample_id: String
  fastq_1: Path
  fastq_2: Path
}

def requireParam(value, flag, runMode) {
  def normalized = (value instanceof CharSequence) ? value.toString().trim() : value
  if( normalized == null || (normalized instanceof CharSequence && !normalized) ) {
    throw new IllegalArgumentException("Missing --${flag} when running in mode '${runMode}'.")
  }
  return normalized
}

def requireNonEmptyItems(items, label) {
  if( items.isEmpty() ) {
    throw new IllegalArgumentException("${label} is empty.")
  }
  return items
}

def resolveSamplesheetFile(samplesheet, rawValue, columnName) {
  def text = rawValue?.toString()?.trim()
  if( !text ) {
    throw new IllegalArgumentException("Samplesheet column '${columnName}' is missing or empty")
  }

  def direct = file(text)
  if( direct.isFile() ) {
    return direct
  }

  def fromSheet = file("${samplesheet.parent}/${text}")
  if( fromSheet.isFile() ) {
    return fromSheet
  }

  throw new IllegalArgumentException("Samplesheet ${columnName} path not found: '${text}'")
}

def loadSamplesheet(samplesheet) {
  return channel.of(file(samplesheet, checkIfExists: true))
    .flatMap { csv -> csv.splitCsv(header: true) }
    .map { row ->
      def sampleId = row.sample_id?.toString()
      if( !sampleId?.trim() || sampleId == '.' || sampleId == '..' ||
          sampleId.any { character -> '/\\*?[]{}'.contains(character) } ) {
        throw new IllegalArgumentException("Invalid samplesheet sample_id: '${sampleId}'")
      }
      def fastq1 = resolveSamplesheetFile(samplesheet, row.fastq_1, 'fastq_1')
      def fastq2 = resolveSamplesheetFile(samplesheet, row.fastq_2, 'fastq_2')
      if( fastq1 == fastq2 ) {
        throw new IllegalArgumentException("R1 and R2 resolve to the same file for sample '${sampleId}'")
      }
      record(
        sample_id: sampleId,
        fastq_1: fastq1,
        fastq_2: fastq2
      )
    }
    .toList()
    .flatMap { samples ->
      requireNonEmptyItems(samples, "Samplesheet '${samplesheet}'")
      def seen = new HashSet<String>()
      def duplicate = samples.find { sample -> !seen.add(sample.sample_id) }
      if( duplicate != null ) {
        throw new IllegalArgumentException("Duplicate samplesheet sample_id: '${duplicate.sample_id}'")
      }
      samples
    }
}

def readMate(read) {
  def name = read.name
  if( name ==~ "(?i)^.+[._-]R1(?:_001)?\\.(?:fastq|fq)(?:\\.gz)?\$" ) {
    return 'R1'
  }
  if( name ==~ "(?i)^.+[._-]R2(?:_001)?\\.(?:fastq|fq)(?:\\.gz)?\$" ) {
    return 'R2'
  }
  throw new IllegalArgumentException("Could not infer R1/R2 mate from FASTQ filename: ${name}")
}

def readSampleId(read) {
  return read.name.replaceFirst("(?i)[._-]R[12](?:_001)?\\.(?:fastq|fq)(?:\\.gz)?\$", '')
}

def loadReadGlob(readsPattern) {
  log.warn "[tethys-nf] --reads is deprecated for typed workflows; prefer --samplesheet with columns sample_id,fastq_1,fastq_2."
  return channel.fromPath(readsPattern, checkIfExists: true)
    .map { read -> tuple(readSampleId(read), read) }
    .groupTuple()
    .map { sample_id, reads ->
      def r1s = reads.findAll { read -> readMate(read) == 'R1' }
      def r2s = reads.findAll { read -> readMate(read) == 'R2' }
      if( r1s.size() != 1 || r2s.size() != 1 ) {
        throw new IllegalArgumentException("Expected exactly one R1 and one R2 for sample '${sample_id}', found R1=${r1s.size()} R2=${r2s.size()}")
      }
      record(
        sample_id: sample_id.toString(),
        fastq_1: r1s[0],
        fastq_2: r2s[0]
      )
    }
}

def loadSampleReads(samplesheet, readsPattern, runMode) {
  if( samplesheet && readsPattern ) {
    throw new IllegalArgumentException("Provide either --samplesheet or deprecated --reads when running in mode '${runMode}', not both.")
  }
  if( samplesheet ) {
    return loadSamplesheet(samplesheet)
  }
  if( readsPattern ) {
    return loadReadGlob(readsPattern)
  }
  throw new IllegalArgumentException("Missing --samplesheet when running in mode '${runMode}' (or use deprecated --reads).")
}

workflow build_phase {
  take:
    genomes_dir: String
    kofam_db: String?
    annotation_backend: String
    pathway_db: String?
    checkm2_db: String?
    skip_checkm2: Boolean

  main:
    genomeFiles = channel
      .fromPath("${genomes_dir}/*.fna", checkIfExists: false)
      .mix(channel.fromPath("${genomes_dir}/*.fa", checkIfExists: false))
      .mix(channel.fromPath("${genomes_dir}/*.fasta", checkIfExists: false))
      .mix(channel.fromPath("${genomes_dir}/**/*.fna", checkIfExists: false))
      .mix(channel.fromPath("${genomes_dir}/**/*.fa", checkIfExists: false))
      .mix(channel.fromPath("${genomes_dir}/**/*.fasta", checkIfExists: false))
      .toSortedList { left, right -> left.toString() <=> right.toString() }
      .map { files -> requireNonEmptyItems(files, "--genomes_dir '${genomes_dir}' did not contain any uncompressed .fna, .fa, or .fasta files") }
    genomePaths = genomeFiles
      .map { files -> files.collect { genome -> genome.toAbsolutePath().toString() } }
    genomes = genomeFiles
      .flatMap { files -> files }

    cluster_out = CLUSTER_SKANI(genomeFiles)
    prodigal_out = PRODIGAL_PYRO(genomes)
    faa = prodigal_out.map { genome -> genome.faa }
    ffn = prodigal_out.map { genome -> genome.ffn }
    faaFiles = faa.toSortedList { left, right -> left.toString() <=> right.toString() }
    ffnFiles = ffn.toSortedList { left, right -> left.toString() <=> right.toString() }
    clusters = cluster_out.map { cluster -> cluster.clusters }

    kofamDb = VERIFY_KOFAM_DB(channel.value(kofam_db))
    kofamInput = faa
      .combine(kofamDb)
      .map { faa_file, db_dir -> tuple(faa_file, db_dir, annotation_backend) }
    kofam_out = KOFAM_SCAN(kofamInput)
    kofamFiles = kofam_out.toSortedList { left, right -> left.toString() <=> right.toString() }

    annotations = CONCAT_KOFAM(kofamFiles)
    manifest = BUILD_MANIFEST(genomePaths, ffnFiles, clusters)
    preprocess = TETHYS_PREPROCESS(manifest, annotations)
    index = TETHYS_INDEX(preprocess, channel.value(pathway_db))

    if( !skip_checkm2 ) {
      checkm2Db = VERIFY_CHECKM2_DB(channel.value(checkm2_db))
      checkm2Input = faaFiles.combine(checkm2Db)
      CHECKM2(checkm2Input)
    } else {
      log.warn "[build_phase] Skipping CHECKM2 as requested (params.skip_checkm2=true)"
    }

  emit:
    index_dir = index
}

workflow profile_phase {
  take:
    reads: Channel<SampleReads>
    index_dir: Channel<Path>

  main:
    // Nextflow hashes a directory input without checking the files inside it.
    index_revision = index_dir.map { index ->
      files("${index}/**", type: 'file', hidden: true)
        .collect { entry -> "${index.relativize(entry)}\t${java.nio.file.Files.size(entry)}\t${entry.lastModified()}".toString() }
        .sort()
    }
    tax_out = PROFILE_TAX(reads, index_dir, index_revision)
    func_out = PROFILE_FUNC(reads, index_dir, index_revision)
    tax_profiles = tax_out.map { tables -> tables.first().parent.parent }
      .toSortedList { left, right -> left.name <=> right.name }
    func_profiles = func_out.map { tables -> tables.first().parent.parent }
      .toSortedList { left, right -> left.name <=> right.name }

  emit:
    tax = tax_profiles
    func = func_profiles
}

workflow merge_phase {
  take:
    tax_profiles: Channel<List<Path>>
    func_profiles: Channel<List<Path>>
    index_dir: Channel<Path?>

  main:
    MERGE_ARTIFACTS(tax_profiles, func_profiles, index_dir)
}

workflow {
  main:
    runMode = (params.mode ?: 'all').toString()

    if( runMode == 'build' ) {
      genomesDir = requireParam(params.genomes_dir, 'genomes_dir', runMode).toString()
      build_phase(
        genomesDir,
        params.kofam_db,
        params.annotation_backend,
        params.pathway_db,
        params.checkm2_db,
        params.skip_checkm2
      )
    }
    else if( runMode == 'profile' ) {
      samples = loadSampleReads(params.samplesheet, params.reads, runMode)
      indexChannel = channel.value(file(requireParam(params.index_dir, 'index_dir', runMode), checkIfExists: true))
      profiles = profile_phase(samples, indexChannel)
      merge_phase(profiles.tax, profiles.func, indexChannel)
    }
    else if( runMode == 'all' ) {
      genomesDir = requireParam(params.genomes_dir, 'genomes_dir', runMode).toString()
      samples = loadSampleReads(params.samplesheet, params.reads, runMode)
      indexChannel = build_phase(
        genomesDir,
        params.kofam_db,
        params.annotation_backend,
        params.pathway_db,
        params.checkm2_db,
        params.skip_checkm2
      )
      profiles = profile_phase(samples, indexChannel)
      merge_phase(profiles.tax, profiles.func, indexChannel)
    }
    else if( runMode == 'merge' ) {
      defaultIndex = file("${params.outdir}/build/tethys/index")
      mergeIndex = params.index_dir ? file(params.index_dir, checkIfExists: true) : (defaultIndex.exists() ? defaultIndex : null)
      indexChannel = channel.value(mergeIndex)
      taxProfiles = channel.value([file("${params.outdir}/profile/tax", checkIfExists: true)])
      funcProfiles = channel.value([file("${params.outdir}/profile/func", checkIfExists: true)])
      merge_phase(taxProfiles, funcProfiles, indexChannel)
    }
    else {
      throw new IllegalArgumentException("Unsupported params.mode '${params.mode}'. Choose from: build, profile, merge, all.")
    }
}
