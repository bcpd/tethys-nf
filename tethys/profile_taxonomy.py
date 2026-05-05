#!/usr/bin/env python
import sys, os, glob, numpy as np, pandas as pd, xarray as xr
from pathlib import Path
from tqdm import tqdm
from collections import OrderedDict
from pyexeggutor import format_bytes, get_file_size, RunShellCommand, check_argument_choice

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

def check_reads_format(forward_reads, reverse_reads, reads_sketch, logger):
    fmt=None
    if any([forward_reads, reverse_reads]):
        assert forward_reads!=reverse_reads and forward_reads and reverse_reads
        fmt='paired'
    if reads_sketch is not None:
        assert forward_reads is None and reverse_reads is None
        fmt='sketch'
    if fmt is None:
        logger.critical('Provide paired fastq or a Sylph sketch'); raise ValueError('reads format not detected')
    logger.info(f"Auto-detected reads format: {fmt}"); return fmt

def check_genome_database(index_directory, logger):
    dbp = os.path.join(index_directory,'database','genomes.syldb'); gdp=os.path.join(index_directory,'database','genome_to_data.pkl.gz')
    if not os.path.exists(dbp): raise FileNotFoundError(f"Missing genomes DB: {dbp}")
    if not os.path.exists(gdp): raise FileNotFoundError(f"Missing genome metadata: {gdp}")

def run_sylph_reads_sketcher(logger, log_directory, sylph_executable, n_jobs, output_directory, forward_reads, reverse_reads, k, minimum_spacing, subsampling_rate, sylph_sketch_options):
    fn = os.path.split(forward_reads)[-1]
    cmd = RunShellCommand(command=[sylph_executable,'sketch','-t',n_jobs,'-k',k,'-c',subsampling_rate,'--min-spacing',minimum_spacing,'-d',output_directory,'-1',forward_reads,'-2',reverse_reads,'&&','mv',os.path.join(output_directory,f"{fn}.paired.sylsp"), os.path.join(output_directory,'reads.sylsp')], name='sylph_reads_sketcher', validate_input_filepaths=[forward_reads, reverse_reads], validate_output_filepaths=[forward_reads, reverse_reads, os.path.join(output_directory,'reads.sylsp')])
    logger.info(f"[{cmd.name}] running command: {cmd.command}"); cmd.run(); cmd.dump(log_directory); cmd.check_status(); return cmd

def run_sylph_profiler(logger, log_directory, sylph_executable, n_jobs, output_directory, index_directory,  reads, minimum_ani, minimum_number_kmers, minimum_count_correct, sylph_profile_options):
    cmd = RunShellCommand(command=[sylph_executable,'profile','--estimate-unknown','-t',n_jobs,'--minimum-ani',minimum_ani,'--min-number-kmers',minimum_number_kmers,'--min-count-correct',minimum_count_correct, sylph_profile_options, os.path.join(index_directory,'database','genomes.syldb'), reads, '|', 'gzip', '>', os.path.join(output_directory,'sylph_profile.tsv.gz')], name='sylph_profiler', validate_input_filepaths=[os.path.join(index_directory,'database','genomes.syldb'), reads], validate_output_filepaths=[os.path.join(output_directory,'sylph_profile.tsv.gz')])
    logger.info(f"[{cmd.name}] running command: {cmd.command}"); cmd.run(); cmd.dump(log_directory); cmd.check_status(); return cmd

def merge_taxonomic_profiling_tables_as_pandas(profiling_directory:str, level='genome', data_type:str='taxonomic_abundances', fillna_with_zeros:bool=False, sparse:bool=False):
    choices={"genomes","genome_clusters"};
    if level not in choices: raise KeyError(f"level must be in {choices}")
    out={}
    patt=f"{profiling_directory}/*/output/{data_type[:-1]}.{level}.parquet"; fps=glob.glob(patt)
    if not fps: raise FileNotFoundError(f"No {data_type[:-1]}.{level}.parquet in {profiling_directory}")
    for fp in tqdm(fps, f"Merging {level}-level {data_type.replace('_',' ')}"):
        add_profile_table(out, fp, pd.read_parquet(fp).squeeze('columns'))
    X=pd.DataFrame(out).T
    if fillna_with_zeros: X=X.fillna(0.0)
    if sparse: X=X.astype(pd.SparseDtype('float',0.0))
    return X

def merge_taxonomic_profiling_tables_as_xarray(profiling_directory:str, level='genomes', fillna_with_zeros:bool=False):
    check_argument_choice(query=level, choices={'genomes','genome_clusters'})
    tax_fps=glob.glob(f"{profiling_directory}/*/output/taxonomic_abundance.{level}.parquet"); seq_fps=glob.glob(f"{profiling_directory}/*/output/sequence_abundance.{level}.parquet")
    if not tax_fps: raise FileNotFoundError(f"No taxonomic_abundance.{level}.parquet in {profiling_directory}")
    if not seq_fps: raise FileNotFoundError(f"No sequence_abundance.{level}.parquet in {profiling_directory}")
    out=OrderedDict()
    for var in ['taxonomic_abundances','sequence_abundances']:
        df=merge_taxonomic_profiling_tables_as_pandas(profiling_directory=profiling_directory, level=level, data_type=var, fillna_with_zeros=fillna_with_zeros, sparse=False)
        out[var]=xr.DataArray(df.values, coords=[('samples', df.index), (level, df.columns)])
    X=xr.Dataset(out).astype(np.float32); X = X.fillna(0.0) if fillna_with_zeros else X; return X
