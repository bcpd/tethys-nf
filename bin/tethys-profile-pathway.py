#!/usr/bin/env python
import sys,os, argparse, warnings, subprocess, glob, shutil, logging
from pathlib import Path
from collections import defaultdict
import pandas as pd
from tqdm import tqdm

__program__ = os.path.split(sys.argv[0])[-1]

from pyexeggutor import (
    read_pickle, 
    read_json,
    build_logger,
    get_file_size,
    format_bytes,
    check_file,
    RunShellCommand,
)
from tethys.index import(
    check_salmon_index,
)

from tethys.profile_pathway import(
    run_salmon_quant,
    reformat_gene_abundance,
    reformat_feature_abundance,
    build_wide_feature_prevalence_matrix,
    build_feature_prevalence_dictionary,
    build_feature_pathway_dictionary,
    calculate_pathway_coverage,
    aggregate_pathway_abundance_and_append_coverage,
    aggregate_feature_abundance_for_clusters,
)

def main(args=None):
    python_executable = sys.executable
    bin_directory = os.path.dirname(python_executable)
    script_directory  =  os.path.dirname(os.path.abspath( __file__ ))
    script_filename = __program__
    description = """
    Running: {} v{} via Python v{} | {}""".format(__program__, sys.version.split(" ")[0], python_executable, script_filename)
    usage = f"{__program__} -1 R1.fq.gz -2 R2.fq.gz -n sample -o project_dir -d index_dir"
    epilog = "Leviathan"

    parser = argparse.ArgumentParser(description=description, usage=usage, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

    parser_io = parser.add_argument_group('I/O arguments')
    parser_io.add_argument("-1","--forward_reads", type=str)
    parser_io.add_argument("-2","--reverse_reads", type=str)
    parser_io.add_argument("-n", "--name", type=str, required=True)
    parser_io.add_argument("-o","--project_directory", type=str, default="tethys_output/profiling/pathway")
    parser_io.add_argument("-d","--index_directory", type=str, required=True)
    parser_io.add_argument("-f","--output_format", type=str, choices={"tsv", "parquet"}, default="parquet")

    parser_utility = parser.add_argument_group('Utility arguments')
    parser_utility.add_argument("-p","--n_jobs", type=int, default=1)
    parser_utility.add_argument("--log_level", default="INFO", choices=["CRITICAL","ERROR","WARNING","INFO","DEBUG"], help="Logging verbosity")
    parser_utility.add_argument("--log_file", help="Optional file to append detailed logs")

    parser_salmon_quant = parser.add_argument_group('salmon quant arguments')
    parser_salmon_quant.add_argument("--salmon_executable", type=str)
    parser_salmon_quant.add_argument("-m", "--minimum_score_fraction", type=float, default=0.87)
    parser_salmon_quant.add_argument("--salmon_include_mappings", action="store_true")
    parser_salmon_quant.add_argument("--salmon_gzip", action="store_true")
    parser_salmon_quant.add_argument("--salmon_quant_options", type=str, default="")

    parser_samtools = parser.add_argument_group('samtools arguments')
    parser_samtools.add_argument("--samtools_executable", type=str)
    parser_samtools.add_argument("--alignment_format", type=str, choices={"sam", "bam", "sorted.bam"}, default="sorted.bam")

    parser_features = parser.add_argument_group('Features arguments')
    parser_features.add_argument("--no_split_feature_abundances", action="store_true")

    opts = parser.parse_args()
    opts.script_directory  = script_directory
    opts.script_filename = script_filename

    logger = build_logger("tethys profile-pathway")
    log_level = getattr(logging, opts.log_level.upper(), logging.INFO)
    logger.setLevel(log_level)
    if opts.log_file:
        fh = logging.FileHandler(opts.log_file)
        fh.setLevel(log_level)
        logger.addHandler(fh)
    logger.info(f"Command: {sys.argv}")

    def _require_file(path_str: str, label: str) -> None:
        if not os.path.exists(path_str):
            parser.error(f"{label} not found: {path_str}")
        if path_str.endswith('.gz'):
            with open(path_str, 'rb') as fh:
                magic = fh.read(2)
            if magic and magic != b"\x1f\x8b":
                parser.error(f"{label} does not appear to be gzipped despite .gz extension: {path_str}")

    if bool(opts.forward_reads) ^ bool(opts.reverse_reads):
        parser.error("Forward and reverse reads must be provided together")

    if opts.forward_reads and opts.reverse_reads:
        _require_file(opts.forward_reads, "Forward reads")
        _require_file(opts.reverse_reads, "Reverse reads")
        left_tag = Path(opts.forward_reads).name
        right_tag = Path(opts.reverse_reads).name
        if left_tag == right_tag:
            parser.error("Forward and reverse reads point to the same file")
        shared_prefix = os.path.commonprefix([left_tag.replace('R1',''), right_tag.replace('R2','')])
        if len(shared_prefix.strip()) < 2:
            logger.warning("Forward/Reverse filenames share little overlap; double-check pairing")

    if opts.n_jobs == -1:
        from multiprocessing import cpu_count 
        opts.n_jobs = cpu_count()
        logger.info(f"Setting --n_jobs to maximum threads {opts.n_jobs}")

    assert opts.n_jobs >= 1
    
    if not opts.salmon_executable:
        salmon_in_path = shutil.which("salmon")
        opts.salmon_executable = salmon_in_path or os.path.join(bin_directory, "salmon")
    if not os.path.exists(opts.salmon_executable):
        raise FileNotFoundError(f"salmon executable not found: {opts.salmon_executable}")

    if not opts.samtools_executable:
        samtools_in_path = shutil.which("samtools")
        opts.samtools_executable = samtools_in_path or os.path.join(bin_directory, "samtools")
    if not os.path.exists(opts.samtools_executable):
        raise FileNotFoundError(f"samtools executable not found: {opts.samtools_executable}")
    
    config = read_json(os.path.join(opts.index_directory, "config.json"))

    logger.info("Checking Salmon index") 
    check_salmon_index(
        salmon_index_directory=os.path.join(opts.index_directory, "salmon_index"),
        logger=logger,
    )
    
    gene_data_filepath = os.path.join(opts.index_directory, "database", "gene_to_data.pkl.gz")
    logger.info(f"Checking gene metadata: {gene_data_filepath}")
    check_file(gene_data_filepath, minimum_filesize=48)
    
    genome_data_filepath = os.path.join(opts.index_directory, "database", "genome_to_data.pkl.gz")
    logger.info(f"Checking genome metadata: {genome_data_filepath}")
    check_file(genome_data_filepath, minimum_filesize=48)
    
    if config.get("contains_pathways", False):
        pathway_data_filepath = os.path.join(opts.index_directory, "database", "pathway_to_data.pkl.gz")
        logger.info(f"Checking pathway metadata: {pathway_data_filepath}")
        check_file(pathway_data_filepath, minimum_filesize=48)
    else:
        logger.warning("No pathways available in index; pathway abundances/coverage will be omitted")

    output_directory = os.path.join(opts.project_directory, opts.name)
    os.makedirs(output_directory, exist_ok=True)
    os.makedirs(os.path.join(output_directory, "output"), exist_ok=True)
    os.makedirs(os.path.join(output_directory, "intermediate"), exist_ok=True)
    os.makedirs(os.path.join(output_directory, "logs"), exist_ok=True)
    os.makedirs(os.path.join(output_directory, "tmp"), exist_ok=True)
    
    logger.info("Running Salmon quant")
    cmd_salmon_quant = run_salmon_quant(
        logger=logger,
        log_directory=os.path.join(output_directory, "logs"), 
        salmon_executable=opts.salmon_executable, 
        samtools_executable=opts.samtools_executable,
        n_jobs=opts.n_jobs, 
        output_directory=os.path.join(output_directory, "intermediate"), 
        index_directory=opts.index_directory,
        forward_reads=opts.forward_reads, 
        reverse_reads=opts.reverse_reads, 
        minimum_score_fraction=opts.minimum_score_fraction, 
        include_mappings=opts.salmon_include_mappings,
        alignment_format=opts.alignment_format,
        salmon_gzip=opts.salmon_gzip,
        salmon_quant_options=opts.salmon_quant_options, 
    )
       
    level="genome"
    
    gene_abundance_base = os.path.join(output_directory, "output", f"gene_abundances.{level}s")
    feature_abundance_base = os.path.join(output_directory, "output", f"feature_abundances.{level}s")
    feature_prev_base = os.path.join(output_directory, "output", f"feature_prevalence.{level}s")
    feature_prev_bin_base = os.path.join(output_directory, "output", f"feature_prevalence-binary.{level}s")
    
    filepath_quantsf = os.path.join(output_directory, "intermediate", "quant.sf")
    if opts.salmon_gzip:
        filepath_quantsf += ".gz"
    df_quant = pd.read_csv(filepath_quantsf, sep="\t", index_col=0)
    df_gene_abundance = reformat_gene_abundance(df_quant, read_pickle(os.path.join(opts.index_directory, "database", "gene_to_data.pkl.gz")))
    if opts.output_format == "parquet":
        df_gene_abundance[["number_of_reads"]].to_parquet(gene_abundance_base+".number_of_reads.parquet", index=True)
        df_gene_abundance[["tpm"]].to_parquet(gene_abundance_base+".tpm.parquet", index=True)
    else:
        df_gene_abundance[["number_of_reads"]].to_csv(gene_abundance_base+".number_of_reads.tsv.gz", sep="\t")
        df_gene_abundance[["tpm"]].to_csv(gene_abundance_base+".tpm.tsv.gz", sep="\t")
        
    df_feature_abundance = reformat_feature_abundance(df_gene_abundance, read_pickle(os.path.join(opts.index_directory, "database", "gene_to_data.pkl.gz")), split_feature_abundances=not opts.no_split_feature_abundances)
    if opts.output_format == "parquet":
        # unscaled columns may be present; write consistent names
        cols = [c for c in df_feature_abundance.columns if c.startswith("number_of_reads")]
        df_feature_abundance[[cols[0]]].rename(columns={cols[0]:"number_of_reads"}).to_parquet(feature_abundance_base+".number_of_reads.parquet", index=True)
        cols = [c for c in df_feature_abundance.columns if c.startswith("tpm")]
        df_feature_abundance[[cols[0]]].rename(columns={cols[0]:"tpm"}).to_parquet(feature_abundance_base+".tpm.parquet", index=True)
    else:
        cols = [c for c in df_feature_abundance.columns if c.startswith("number_of_reads")]
        df_feature_abundance[[cols[0]]].rename(columns={cols[0]:"number_of_reads"}).to_csv(feature_abundance_base+".number_of_reads.tsv.gz", sep="\t")
        cols = [c for c in df_feature_abundance.columns if c.startswith("tpm")]
        df_feature_abundance[[cols[0]]].rename(columns={cols[0]:"tpm"}).to_csv(feature_abundance_base+".tpm.tsv.gz", sep="\t")
        
    df_feature_prevalence = build_wide_feature_prevalence_matrix(df_feature_abundance, threshold=0)
    if opts.output_format == "parquet":
        df_feature_prevalence.to_parquet(feature_prev_base+".parquet", index=True)
        (df_feature_prevalence>0).astype(int).to_parquet(feature_prev_bin_base+".parquet", index=True)
    else:
        df_feature_prevalence.to_csv(feature_prev_base+".tsv.gz", sep="\t")
        (df_feature_prevalence>0).astype(int).to_csv(feature_prev_bin_base+".tsv.gz", sep="\t")
        
    if config.get("contains_pathways", False):
        genome_to_features = build_feature_prevalence_dictionary((df_feature_prevalence>0).astype(int))
        feature_to_pathways = build_feature_pathway_dictionary(read_pickle(os.path.join(opts.index_directory, "database", "pathway_to_data.pkl.gz")))
        coverages = calculate_pathway_coverage(genome_to_features, read_pickle(os.path.join(opts.index_directory, "database", "pathway_to_data.pkl.gz")))
        pathway_abundance_base = os.path.join(output_directory, "output", f"pathway_abundances.{level}s")
        df_pathway_abundances = aggregate_pathway_abundance_and_append_coverage(df_feature_abundance, feature_to_pathways, coverages, index_names = [f"id_{level}", "id_pathway"])
        if opts.output_format == "parquet":
            df_pathway_abundances[["number_of_reads","tpm"]].to_parquet(pathway_abundance_base+".parquet", index=True)
            df_pathway_abundances[["coverage"]].to_parquet(pathway_abundance_base+".coverage.parquet", index=True)
        else:
            df_pathway_abundances[["number_of_reads","tpm"]].to_csv(pathway_abundance_base+".tsv.gz", sep="\t")
            df_pathway_abundances[["coverage"]].to_csv(pathway_abundance_base+".coverage.tsv.gz", sep="\t")

    if read_json(os.path.join(opts.index_directory, "config.json")).get("contains_genome_cluster_mapping", False):
        level="genome_cluster"
        df_feature_abundance_gc = aggregate_feature_abundance_for_clusters(df_feature_abundance, read_pickle(os.path.join(opts.index_directory, "database", "genome_to_data.pkl.gz")))
        base = os.path.join(output_directory, "output", f"feature_abundances.{level}s")
        if opts.output_format == "parquet":
            df_feature_abundance_gc[["number_of_reads"]].to_parquet(base+".number_of_reads.parquet", index=True)
            df_feature_abundance_gc[["tpm"]].to_parquet(base+".tpm.parquet", index=True)
        else:
            df_feature_abundance_gc[["number_of_reads"]].to_csv(base+".number_of_reads.tsv.gz", sep="\t")
            df_feature_abundance_gc[["tpm"]].to_csv(base+".tpm.tsv.gz", sep="\t")

        prev_base = os.path.join(output_directory, "output", f"feature_prevalence.{level}s")
        prev_bin_base = os.path.join(output_directory, "output", f"feature_prevalence-binary.{level}s")
        df_feature_prevalence_gc = (df_feature_prevalence.groupby(lambda x: read_pickle(os.path.join(opts.index_directory, "database", "genome_to_data.pkl.gz"))[x]["id_genome_cluster"]).sum())
        if opts.output_format == "parquet":
            df_feature_prevalence_gc.to_parquet(prev_base+".parquet", index=True)
            (df_feature_prevalence_gc>0).astype(int).to_parquet(prev_bin_base+".parquet", index=True)
        else:
            df_feature_prevalence_gc.to_csv(prev_base+".tsv.gz", sep="\t")
            (df_feature_prevalence_gc>0).astype(int).to_csv(prev_bin_base+".tsv.gz", sep="\t")

        if config.get("contains_pathways", False):
            feature_to_pathways = build_feature_pathway_dictionary(read_pickle(os.path.join(opts.index_directory, "database", "pathway_to_data.pkl.gz")))
            genome_to_data = read_pickle(os.path.join(opts.index_directory, "database", "genome_to_data.pkl.gz"))
            df_path_gc = aggregate_feature_abundance_for_clusters(df_feature_abundance, genome_to_data)
            df_prev_bin_gc = (df_feature_prevalence>0).astype(int).groupby(lambda x: genome_to_data[x]["id_genome_cluster"]).sum()
            genome_to_features_gc = build_feature_prevalence_dictionary(df_prev_bin_gc)
            coverages_gc = calculate_pathway_coverage(genome_to_features_gc, read_pickle(os.path.join(opts.index_directory, "database", "pathway_to_data.pkl.gz")))
            path_base = os.path.join(output_directory, "output", f"pathway_abundances.{level}s")
            df_pathway_gc = aggregate_pathway_abundance_and_append_coverage(df_path_gc, feature_to_pathways, coverages_gc, index_names = [f"id_{level}", "id_pathway"])
            if opts.output_format == "parquet":
                df_pathway_gc[["number_of_reads","tpm"]].to_parquet(path_base+".parquet", index=True)
                df_pathway_gc[["coverage"]].to_parquet(path_base+".coverage.parquet", index=True)
            else:
                df_pathway_gc[["number_of_reads","tpm"]].to_csv(path_base+".tsv.gz", sep="\t")
                df_pathway_gc[["coverage"]].to_csv(path_base+".coverage.tsv.gz", sep="\t")

    logger.info(f"Completed pathway profiling: {opts.name}")
    for filepath in glob.glob(os.path.join(output_directory, "output","*")):
        filesize = get_file_size(filepath, format=True)
        logger.info(f"Output: {filepath} ({filesize})")
    logger.info(f"Completed running tethys-profile-pathway for {opts.name}: {opts.project_directory}")

if __name__ == "__main__":
    main()
