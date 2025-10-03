/******************************************************
 * Tethys-NF: Nextflow DSL2 pipeline (build | profile | merge | all)
 ******************************************************/

include { CLUSTER_SKANI        } from './modules/cluster_skani.nf'
include { PRODIGAL_PYRO        } from './modules/prodigal_pyro.nf'
include { CONCAT_KOFAM         } from './modules/concat_kofam.nf'
include { BUILD_MANIFEST       } from './modules/build_manifest.nf'
include { TETHYS_PREPROCESS } from './modules/tethys_preprocess.nf'
include { TETHYS_INDEX      } from './modules/tethys_index.nf'
include { VERIFY_KOFAM_DB       } from './modules/verify_kofam_db.nf'
include { KOFAM_SCAN            } from './modules/kofam_scan.nf'
include { VERIFY_CHECKM2_DB     } from './modules/verify_checkm2_db.nf'
include { CHECKM2              } from './modules/checkm2.nf'
include { PROFILE_TAX          } from './modules/profile_tax.nf'
include { PROFILE_FUNC         } from './modules/profile_func.nf'
include { MERGE_ARTIFACTS      } from './modules/merge_artifacts.nf'

workflow {
  if( params.mode == 'build' ) {
    build_phase()
  }
  else if( params.mode == 'profile' ) {
    profile_phase(nextflow.Channel.value(params.index_dir))
    merge_phase(profile_phase.out.barrier)
  }
  else if( params.mode == 'all' ) {
    build_phase()
    profile_phase(build_phase.out.index_dir)
    merge_phase(profile_phase.out.barrier)
  }
  else if( params.mode == 'merge' ) {
    merge_phase(nextflow.Channel.value('ok'))
  }
}

workflow build_phase {
  // Allow genomes to be nested in subfolders; match recursively with **
  def genomeGlob = "${params.genomes_dir}/**/*.{fna,fa,fasta}"

  // Cluster all genomes in a single job
  CLUSTER_SKANI(nextflow.Channel.fromPath(genomeGlob).collect())
  def clusters = CLUSTER_SKANI.out.clusters

  // Call genes per-genome
  PRODIGAL_PYRO(nextflow.Channel.fromPath(genomeGlob))
  def faa = PRODIGAL_PYRO.out.faa

  VERIFY_KOFAM_DB(nextflow.Channel.value(params.kofam_db))
  def kofamDb = VERIFY_KOFAM_DB.out.db_dir

  // Annotate proteins per-genome (scatter for parallelism)
  def kofamInput = faa.cross(kofamDb)
  KOFAM_SCAN(kofamInput)
  def kofam = KOFAM_SCAN.out.kofam

  // Gather KOfam outputs for concatenation
  CONCAT_KOFAM(kofam.collect())
  def annotations = CONCAT_KOFAM.out.annotations

  // Build manifest from raw genome paths and clusters
  BUILD_MANIFEST(nextflow.Channel.fromPath(genomeGlob).collect(), clusters)
  def manifest = BUILD_MANIFEST.out.manifest

  TETHYS_PREPROCESS(manifest, annotations)
  def preprocess = TETHYS_PREPROCESS.out.preprocess

  TETHYS_INDEX(preprocess)

  // Optional QA on all proteins
  if( !params.skip_checkm2 ) {
    VERIFY_CHECKM2_DB(nextflow.Channel.value(params.checkm2_db))
    def checkm2Db = VERIFY_CHECKM2_DB.out.db_dir
    def checkm2Input = faa.collect().combine(checkm2Db)
    CHECKM2(checkm2Input)
  } else {
    log.warn "[build_phase] Skipping CHECKM2 as requested (params.skip_checkm2=true)"
  }

  // Expose the index path as a named workflow output
  emit:
    index_dir = TETHYS_INDEX.out.index
}

workflow profile_phase {
  take:
    index_dir
  main:
    READS = nextflow.Channel.fromFilePairs(params.reads, checkIfExists: true)
    PROFILE_TAX( READS, index_dir )
    PROFILE_FUNC( READS, index_dir )
    barrier = PROFILE_TAX.out.done.mix(PROFILE_FUNC.out.done).collect()
  emit:
    barrier
}

// (run_all removed; use explicit composition in top-level workflow)

workflow merge_phase {
  take:
    barrier
  main:
    MERGE_ARTIFACTS(params.outdir, barrier)
}
