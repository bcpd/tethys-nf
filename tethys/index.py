#!/usr/bin/env python
import sys,os, argparse, warnings, subprocess
from collections import defaultdict
from pandas.errors import EmptyDataError
import pyfastx
from tqdm import tqdm

__program__ = os.path.split(sys.argv[0])[-1]

from pyexeggutor import (
    open_file_reader,
    read_pickle, 
    read_json,
    get_timestamp,
    format_bytes,
    get_file_size,
    profile_peak_memory,
    RunShellCommand,
)

@profile_peak_memory
def process_genomic_databases_and_check_inputs(fasta, feature_mapping, genomes, logger, config):
    genes_from_fasta = set()
    for id, seq in tqdm(pyfastx.Fasta(fasta, build_index=False), f"Loading fasta: {fasta}"):
        genes_from_fasta.add(id)
    gene_to_data = defaultdict(dict)
    genome_to_data = defaultdict(dict)
    features_from_data = set()
    with open_file_reader(feature_mapping) as f:
        first_line = f.readline().strip()
        assert "\t" in first_line
        fields = first_line.split("\t")
        assert len(fields) in {3,4}, "Expecting fields: [id_gene, features, id_genome, (Optional: id_genome_cluster)]"
        if len(fields) == 3:
            id_gene, features, id_genome  = fields
            gene_to_data[id_gene]["features"] = eval(features)
            gene_to_data[id_gene]["id_genome"] = id_genome
            gene_to_data[id_gene]["id_genome_cluster"] = None
            for line in tqdm(f, f"Loading feature mapping: {feature_mapping}"):
                line = line.strip()
                if line:
                    id_gene, features, id_genome = line.split("\t")
                    gene_to_data[id_gene]["features"] = eval(features)
                    gene_to_data[id_gene]["id_genome"] = id_genome
                    gene_to_data[id_gene]["id_genome_cluster"] = None
                    genome_to_data[id_genome]["id_genome_cluster"] = None
        elif len(fields) == 4:
            id_gene, features, id_genome, id_genome_cluster  = fields
            gene_to_data[id_gene]["features"] = eval(features)
            gene_to_data[id_gene]["id_genome"] = id_genome
            gene_to_data[id_gene]["id_genome_cluster"] = id_genome_cluster
            genome_to_data[id_genome]["id_genome_cluster"] = id_genome_cluster
            for line in tqdm(f, f"Loading feature mapping with genome clusters: {feature_mapping}"):
                line = line.strip()
                if line:
                    id_gene, features, id_genome, id_genome_cluster = line.split("\t")
                    gene_to_data[id_gene]["features"] = eval(features)
                    gene_to_data[id_gene]["id_genome"] = id_genome
                    gene_to_data[id_gene]["id_genome_cluster"] = id_genome_cluster
                    genome_to_data[id_genome]["id_genome_cluster"] = id_genome_cluster
        config["contains_genome_cluster_mapping"] = True
    for id_gene, data in gene_to_data.items():
        features_from_data.update(data["features"])
    genes_from_feature_mapping = set(gene_to_data.keys())
    genomes_from_feature_mapping = set(genome_to_data.keys())
    if genes_from_fasta != genes_from_feature_mapping:
        A_exclusive = genes_from_fasta - genes_from_feature_mapping
        B_exclusive = genes_from_feature_mapping - genes_from_fasta
        msg = "--fasta must contain same genes in --feature_mapping"
        if A_exclusive:
            msg += f"\nN={len(A_exclusive)} genes in --fasta not in --feature_mapping"
        if B_exclusive:
            msg += f"\nN={len(B_exclusive)} genes in --feature_mapping not in --fasta"
        logger.critical(msg); raise IndexError(msg)
    config["number_of_genes"] = len(genes_from_feature_mapping)
    config["number_of_features"] = len(features_from_data)
    config["feature_type_is_kegg_ortholog"] = True
    for id_feature in features_from_data:
        if not (id_feature.startswith("K") and len(id_feature)==6 and id_feature[1:].isnumeric()):
            config["feature_type_is_kegg_ortholog"] = False
    genomes_with_filepaths = set()
    if genomes is not None:
        with open_file_reader(genomes) as f:
            for line in tqdm(f, f"Loading genomes: {genomes}"):
                line = line.strip()
                if line:
                    id_genome, filepath = line.split("\t")
                    genome_to_data[id_genome]["filepath"] = filepath
                    genomes_with_filepaths.add(id_genome)
        if genomes_from_feature_mapping != genomes_with_filepaths:
            A_exclusive = genomes_from_feature_mapping - genomes_with_filepaths
            B_exclusive = genomes_with_filepaths - genomes_from_feature_mapping
            logger.warn(f"--feature_mapping and --genomes genome sets are different (A_exclusive={len(A_exclusive)}, B_exclusive={len(B_exclusive)})")
        config["contains_genome_filepaths"] = True
    config["number_of_genomes"] = len(genomes_with_filepaths)
    config["timestamp"] = get_timestamp()
    return config, gene_to_data, genome_to_data

def update_genome_database_with_fasta_filepaths_and_check_inputs(index_directory, genomes, logger, config):
    gene_to_data = read_pickle(os.path.join(index_directory, "database", "gene_to_data.pkl.gz"))
    genome_to_data = read_pickle(os.path.join(index_directory, "database", "genome_to_data.pkl.gz"))
    genomes_from_feature_mapping = set(genome_to_data.keys())
    genomes_with_filepaths = set()
    with open_file_reader(genomes) as f:
        for line in tqdm(f, f"Loading genomes: {genomes}"):
            line = line.strip()
            if line:
                id_genome, filepath = line.split("\t")
                genome_to_data[id_genome]["filepath"] = filepath
                genomes_with_filepaths.add(id_genome)
    if genomes_from_feature_mapping != genomes_with_filepaths:
        A_exclusive = genomes_from_feature_mapping - genomes_with_filepaths
        B_exclusive = genomes_with_filepaths - genomes_from_feature_mapping
        logger.warn(f"--feature_mapping and --genomes genome sets are different (A_exclusive={len(A_exclusive)}, B_exclusive={len(B_exclusive)})")
    config["contains_genome_filepaths"] = True
    config["timestamp"] = get_timestamp()
    return config, gene_to_data, genome_to_data

def load_pathway_database_and_check_inputs(index_directory, gene_to_data, logger, config):
    from pyexeggutor import read_pickle as _rp
    pathway_to_data = _rp(os.path.join(index_directory, "database", "pathway_to_data.pkl.gz"))
    features_from_data = set()
    for id_gene, data in gene_to_data.items():
        features_from_data.update(data["features"])
    features_from_pathways = set()
    for id_pathway, data in pathway_to_data.items():
        features_from_pathways.update(set(data["ko_to_nodes"].keys()))
    overlapping = features_from_data & features_from_pathways
    if overlapping:
        config["number_of_features_in_pathways"] = len(features_from_pathways)
        config["number_of_features_overlapping_in_pathways"] = len(overlapping)
    else:
        raise IndexError("No overlapping features between feature mapping and pathway DB")
    config["timestamp"] = get_timestamp(); return config, pathway_to_data

def check_salmon_index(salmon_index_directory, logger):
    expected = ['seq.bin','info.json','pre_indexing.log','ref_indexing.log','ctable.bin','refAccumLengths.bin','mphf.bin','versionInfo.json','duplicate_clusters.tsv','ctg_offsets.bin','reflengths.bin','pos.bin','refseq.bin','complete_ref_lens.bin','rank.bin']
    missing, empty = [], []
    if os.path.exists(salmon_index_directory):
        from pyexeggutor import get_file_size
        for fn in expected:
            fp = os.path.join(salmon_index_directory, fn)
            if not os.path.exists(fp): missing.append(fp)
            sz = get_file_size(fp); logger.info(f"[salmon_index] {fp} ({format_bytes(sz)})")
            if sz < 1: empty.append(fp)
        if missing: raise FileNotFoundError(f"Salmon index missing: {missing}")
        if empty:   raise EmptyDataError(f"Salmon index has empty files: {empty}")
    else:
        raise FileNotFoundError(f"Salmon index does not exist: {salmon_index_directory}")

def run_salmon_indexer(logger, log_directory, salmon_executable, n_jobs, fasta, index_directory, index_options):
    cmd = RunShellCommand(command=[salmon_executable,'index','--keepDuplicates','--threads',n_jobs,'--transcripts',fasta,'--index',os.path.join(index_directory,'salmon_index'),index_options], name='salmon_indexer')
    logger.info(f"[{cmd.name}] running command: {cmd.command}"); cmd.run(); cmd.dump(log_directory); cmd.check_status(); return cmd

def run_sylph_genomes_sketcher(logger, log_directory, sylph_executable, n_jobs, genome_filepaths, index_directory, k, minimum_spacing, subsampling_rate, sylph_sketch_options):
    cmd = RunShellCommand(command=[sylph_executable,'sketch','-t',n_jobs,'--gl',genome_filepaths,'-o',os.path.join(index_directory,'database','genomes'),'-k',k,'--min-spacing',minimum_spacing,'-c',subsampling_rate,sylph_sketch_options], name='sylph_genomes_sketcher')
    logger.info(f"[{cmd.name}] running command: {cmd.command}"); cmd.run(); cmd.dump(log_directory); cmd.check_status(); return cmd

def run_kegg_pathway_downloader(logger, log_directory, pathway_database_downloader_executable,  index_directory, no_intermediate_files):
    cmd = RunShellCommand(command=[pathway_database_downloader_executable,'--download','--force','--no_intermediate_files' if no_intermediate_files else '', '--database', os.path.join(index_directory,'database','pathway_to_data.pkl.gz')], name='kegg_pathway_downloader')
    logger.info(f"[{cmd.name}] running command: {cmd.command}"); cmd.run(); cmd.dump(log_directory); cmd.check_status(); return cmd

