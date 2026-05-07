#!/usr/bin/env python
import sys, os, glob
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm
import pandas as pd
import numpy as np
import xarray as xr
from kegg_pathway_profiler.pathways import pathway_coverage_wrapper
from pyexeggutor import format_bytes, RunShellCommand, check_argument_choice

__program__ = os.path.split(sys.argv[0])[-1]


def normalize_profile_sample_id(sample_dir):
    return sample_dir[len("sample="):] if sample_dir.startswith("sample=") else sample_dir


def sample_id_from_profile_filepath(filepath):
    return normalize_profile_sample_id(Path(filepath).parents[1].name)


def add_profile_table(out, filepath, value):
    sample_id = sample_id_from_profile_filepath(filepath)
    if sample_id in out:
        raise ValueError(f"Duplicate normalized sample ID '{sample_id}' while merging {filepath}")
    out[sample_id] = value


def pathway_profile_pattern(profiling_directory, data_type, level, metric):
    if data_type == "feature_abundances":
        return f"{profiling_directory}/**/output/{data_type}.{level}.{metric}.parquet"
    if data_type == "pathway_abundances" and metric == "coverage":
        return f"{profiling_directory}/**/output/{data_type}.{level}.coverage.parquet"
    return f"{profiling_directory}/**/output/{data_type}.{level}.parquet"


def metric_column(df, data_type, metric):
    if metric in df.columns:
        return metric
    scaled = f"{metric}(scaled)"
    if scaled in df.columns:
        return scaled
    if data_type in {"feature_abundances", "pathway_abundances"}:
        raise KeyError(f"Missing metric column '{metric}' in columns: {list(df.columns)}")
    return metric

def run_salmon_quant(logger, log_directory, salmon_executable, samtools_executable, n_jobs, output_directory, index_directory, forward_reads, reverse_reads, minimum_score_fraction, include_mappings, alignment_format, salmon_gzip, salmon_quant_options):
    args = dict(command=[salmon_executable,'quant','--meta','--libType','A','--threads',n_jobs,'--minScoreFraction',minimum_score_fraction,'--index',os.path.join(index_directory,'salmon_index'),'-1',forward_reads,'-2',reverse_reads,'--writeUnmappedNames', salmon_quant_options if salmon_quant_options else '', '--output', output_directory], name='salmon_quant', validate_input_filepaths=[forward_reads, reverse_reads], validate_output_filepaths=[os.path.join(output_directory,'quant.sf.gz') if salmon_gzip else os.path.join(output_directory,'quant.sf')])
    if include_mappings:
        if alignment_format=='sam': args['command'] += ['--writeMappings','>',os.path.join(output_directory,'mapped.sam')]; args['validate_output_filepaths'].append(os.path.join(output_directory,'mapped.sam'))
        elif alignment_format=='bam': args['command'] += ['--writeMappings','|',samtools_executable,'view','-b','-h','-o',os.path.join(output_directory,'mapped.bam')]; args['validate_output_filepaths'].append(os.path.join(output_directory,'mapped.bam'))
        elif alignment_format=='sorted.bam': args['command'] += ['--writeMappings','|',samtools_executable,'view','-b','-h','|',samtools_executable,'sort','-@',n_jobs,'-o',os.path.join(output_directory,'mapped.sorted.bam'),'-']; args['validate_output_filepaths'].append(os.path.join(output_directory,'mapped.sorted.bam'))
    args['command'] += ['&&','rm','-v',os.path.join(output_directory,'aux_info','unmapped_names.txt')]
    if salmon_gzip: args['command'] += ['&&','gzip', os.path.join(output_directory,'quant.sf')]
    cmd = RunShellCommand(**args); logger.info(f"[{cmd.name}] running command: {cmd.command}"); cmd.run(); logger.info(f"[{cmd.name}] duration: {cmd.duration_}"); logger.info(f"[{cmd.name}] peak memory: {format_bytes(cmd.peak_memory_)}"); cmd.dump(log_directory); cmd.check_status(); return cmd

def reformat_gene_abundance(df_quant:pd.DataFrame, gene_to_data:dict):
    idx, vals = [], []
    for id_gene, row in tqdm(df_quant.iterrows(), "Removing zero-abundance features"):
        abundance = row['NumReads']; tpm = row['TPM']
        if abundance>0:
            idx.append((gene_to_data[id_gene]['id_genome'], id_gene)); vals.append([abundance, tpm])
    return pd.DataFrame(vals, index=pd.MultiIndex.from_tuples(idx, names=['id_genome','id_gene']), columns=['number_of_reads','tpm'])

def reformat_feature_abundance(df_gene_abundances:pd.DataFrame, gene_to_data:dict, split_feature_abundances:bool):
    acc = defaultdict(lambda: np.zeros(2, dtype=float))
    if split_feature_abundances:
        for (id_genome,id_gene), (abundance,tpm) in tqdm(df_gene_abundances.iterrows(), "Aggregating feature counts (split)"):
            feats = gene_to_data[id_gene]['features']; n=len(feats) if feats else 0
            if n:
                for f in feats: acc[(id_genome,f)] += [abundance/n, tpm/n]
        cols=["number_of_reads(scaled)","tpm(scaled)"]
    else:
        for (id_genome,id_gene), (abundance,tpm) in tqdm(df_gene_abundances.iterrows(), "Aggregating feature counts"):
            feats = gene_to_data[id_gene]['features']
            if feats:
                for f in feats: acc[(id_genome,f)] += [abundance, tpm]
        cols=["number_of_reads","tpm"]
    return pd.DataFrame(acc, index=cols).T.rename_axis(index=['id_genome','id_feature'])

def build_wide_feature_prevalence_matrix(df_feature_abundance:pd.DataFrame, threshold:float=0.0):
    genomes = sorted(df_feature_abundance.index.get_level_values(0).unique()); features = sorted(df_feature_abundance.index.get_level_values(1).unique())
    gi = {g:i for i,g in enumerate(genomes)}; fj = {f:j for j,f in enumerate(features)}
    M = np.zeros((len(genomes), len(features)), dtype=int)
    for (g,f), v in tqdm(df_feature_abundance.iloc[:,0].items(), total=df_feature_abundance.shape[0]):
        if v>threshold: M[gi[g], fj[f]] += 1
    return pd.DataFrame(M, index=pd.Index(genomes,name='id_genome'), columns=pd.Index(features,name='id_feature'))

def build_feature_prevalence_dictionary(df_feature_prevalence_binary:pd.DataFrame):
    return {g:set(prevalence[lambda x: x>0].index) for g, prevalence in df_feature_prevalence_binary.iterrows()}

def build_feature_pathway_dictionary(pathway_to_data:dict):
    out = defaultdict(set)
    for pid, data in pathway_to_data.items():
        for ko in data['ko_to_nodes']: out[ko].add(pid)
    return out

def calculate_pathway_coverage(genome_to_features:dict, pathway_to_data:dict):
    cov = {}
    for gid, feats in genome_to_features.items():
        res = pathway_coverage_wrapper(evaluation_kos=feats, database=pathway_to_data, progressbar_description=f"Calculating pathway coverage: {gid}")
        for pid, r in res.items(): cov[(gid,pid)] = r['coverage']
    return cov

def aggregate_pathway_abundance_and_append_coverage(df_feature_abundance:pd.DataFrame, feature_to_pathways:dict, coverages:dict, index_names=["id_genome","id_pathway"]):
    mat = defaultdict(lambda: np.zeros(3, dtype=float))
    for (gid, feat), vals in df_feature_abundance.iterrows():
        for pid in feature_to_pathways[feat]: mat[(gid,pid)][:-1] += vals
    for key in mat: mat[key] += [0.0,0.0, coverages.get(key, 0.0)]
    df = pd.DataFrame(mat, index=df_feature_abundance.columns.tolist()+['coverage']).T
    df.index.names = index_names; return df

def aggregate_feature_abundance_for_clusters(df_feature_abundance:pd.DataFrame, genome_to_data:dict):
    def f(x): gid, feat = x; return (genome_to_data[gid]['id_genome_cluster'], feat)
    out = df_feature_abundance.groupby(f).sum(); out.index = pd.MultiIndex.from_tuples(out.index, names=['id_genome_cluster','id_feature']); return out

def merge_pathway_profiling_tables_as_pandas(profiling_directory:str, data_type:str, level='genomes', metric='number_of_reads', fillna_with_zeros:bool=False, sparse:bool=False):
    check_argument_choice(query=data_type, choices={"feature_abundances","feature_prevalence","feature_prevalence-binary","feature_prevalence-ratio","gene_abundances","pathway_abundances"}); check_argument_choice(query=level, choices={"genomes","genome_clusters"}); check_argument_choice(query=metric, choices={"number_of_reads","tpm","coverage"})
    if (level=='genomes' and data_type=='feature_prevalence-ratio') or (data_type!='pathway_abundances' and metric=='coverage'): raise ValueError('Invalid combination')
    fps = sorted(glob.glob(pathway_profile_pattern(profiling_directory, data_type, level, metric), recursive=True));
    if not fps: raise FileNotFoundError(f"No {data_type}.{level}.parquet in {profiling_directory}")
    out={}
    if data_type in {"feature_abundances","gene_abundances","pathway_abundances"}:
        for fp in tqdm(fps, f"Merging {level}-level {data_type.replace('_',' ')} {metric}"):
            df = pd.read_parquet(fp); add_profile_table(out, fp, df[metric_column(df, data_type, metric)])
    else:
        for fp in tqdm(fps, f"Merging {level}-level {data_type.replace('_',' ')}"):
            df = pd.read_parquet(fp); add_profile_table(out, fp, df.stack())
    X = pd.DataFrame(out).T
    if fillna_with_zeros: X = X.fillna(0 if data_type=='feature_prevalence-binary' else 0.0)
    if sparse: X = X.astype(pd.SparseDtype('int' if data_type=='feature_prevalence-binary' else 'float', 0 if data_type=='feature_prevalence-binary' else 0.0))
    return X

def merge_pathway_profiling_tables_as_xarray(profiling_directory:str, data_type:str, level='genomes', metric='number_of_reads', fillna_with_zeros:bool=False):
    check_argument_choice(query=data_type, choices={"feature_abundances","feature_prevalence","feature_prevalence-binary","feature_prevalence-ratio","pathway_abundances"}); check_argument_choice(query=level, choices={"genomes","genome_clusters"}); check_argument_choice(query=metric, choices={"number_of_reads","tpm","coverage"})
    if (level=='genomes' and data_type=='feature_prevalence-ratio') or (data_type!='pathway_abundances' and metric=='coverage'): raise ValueError('Invalid combination')
    fps = sorted(glob.glob(pathway_profile_pattern(profiling_directory, data_type, level, metric), recursive=True));
    if not fps: raise FileNotFoundError(f"No {data_type}.{level}.parquet in {profiling_directory}")
    out={}
    if data_type in {"feature_abundances","pathway_abundances"}:
        varlbl = data_type.split('_')[0] + 's'
        for fp in tqdm(fps, f"Merging {level}-level {data_type.replace('_',' ')} {metric}"):
            df = pd.read_parquet(fp); df = df[metric_column(df, data_type, metric)].unstack(); add_profile_table(out, fp, xr.DataArray(df.values, coords=[(level, df.index), (varlbl, df.columns)]))
    else:
        varlbl = data_type.split('_')[0] + 's'
        for fp in tqdm(fps, f"Merging {level}-level {data_type.replace('_',' ')}"):
            df = pd.read_parquet(fp); add_profile_table(out, fp, xr.DataArray(df.values, coords=[(level, df.index), (varlbl, df.columns)]))
    X = xr.concat(out.values(), dim='samples'); X['samples'] = list(out.keys())
    if data_type in {"feature_prevalence-binary","feature_prevalence"}: X = X.astype(np.int8); X = X.fillna(0) if fillna_with_zeros else X
    else: X = X.astype(np.float32); X = X.fillna(0.0) if fillna_with_zeros else X
    return X
