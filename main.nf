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
  annotation_backend: String = 'pykofamsearch'
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

def loadSamplesheet(samplesheet) {
  return channel.of(samplesheet)
    .flatMap { csv -> csv.splitCsv(header: true) }
    .map { row ->
      record(
        sample_id: row.sample_id.toString(),
        fastq_1: file(row.fastq_1.toString()),
        fastq_2: file(row.fastq_2.toString())
      )
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
    genomeGlob = "${genomes_dir}/**/*.{fna,fa,fasta}"
    genomes = channel.fromPath(genomeGlob)
    genomePaths = genomes
      .map { genome -> genome.toAbsolutePath().toString() }
      .collect()

    cluster_out = CLUSTER_SKANI(genomes.collect())
    prodigal_out = PRODIGAL_PYRO(genomes)
    faa = prodigal_out.map { genome -> genome.faa }
    ffn = prodigal_out.map { genome -> genome.ffn }
    clusters = cluster_out.map { cluster -> cluster.clusters }

    kofamDb = VERIFY_KOFAM_DB(channel.value(kofam_db))
    kofamInput = faa
      .combine(kofamDb)
      .map { faa_file, db_dir -> tuple(faa_file, db_dir, annotation_backend) }
    kofam_out = KOFAM_SCAN(kofamInput)

    annotations = CONCAT_KOFAM(kofam_out.collect())
    manifest = BUILD_MANIFEST(genomePaths, ffn.collect(), clusters)
    preprocess = TETHYS_PREPROCESS(manifest, annotations)
    index = TETHYS_INDEX(preprocess, channel.value(pathway_db))

    if( !skip_checkm2 ) {
      checkm2Db = VERIFY_CHECKM2_DB(channel.value(checkm2_db))
      checkm2Input = faa.collect().combine(checkm2Db)
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
    index_dir: Channel<String>

  main:
    tax_out = PROFILE_TAX(reads, index_dir)
    func_out = PROFILE_FUNC(reads, index_dir)
    tax_done = tax_out.map { sample -> sample.done }
    func_done = func_out.map { sample -> sample.done }
    barrier = tax_done.mix(func_done).collect()

  emit:
    barrier = barrier
}

workflow merge_phase {
  take:
    barrier: Channel<List<Path>>
    index_dir: Channel<String>
    outdir: String

  main:
    MERGE_ARTIFACTS(channel.value(outdir), barrier, index_dir)
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
      indexChannel = channel.value(requireParam(params.index_dir, 'index_dir', runMode).toString())
      profileBarrier = profile_phase(samples, indexChannel)
      merge_phase(profileBarrier, indexChannel, params.outdir)
    }
    else if( runMode == 'all' ) {
      genomesDir = requireParam(params.genomes_dir, 'genomes_dir', runMode).toString()
      samples = loadSampleReads(params.samplesheet, params.reads, runMode)
      buildIndex = build_phase(
        genomesDir,
        params.kofam_db,
        params.annotation_backend,
        params.pathway_db,
        params.checkm2_db,
        params.skip_checkm2
      )
      indexChannel = buildIndex.map { index_dir -> index_dir.toString() }
      profileBarrier = profile_phase(samples, indexChannel)
      merge_phase(profileBarrier, indexChannel, params.outdir)
    }
    else if( runMode == 'merge' ) {
      indexChannel = channel.value((params.index_dir ?: "${params.outdir}/build/tethys/index").toString())
      merge_phase(channel.value([] as List<Path>), indexChannel, params.outdir)
    }
    else {
      throw new IllegalArgumentException("Unsupported params.mode '${params.mode}'. Choose from: build, profile, merge, all.")
    }
}
