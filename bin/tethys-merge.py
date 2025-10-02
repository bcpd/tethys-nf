#!/usr/bin/env python
import sys
import os
import argparse
from collections import defaultdict
from itertools import product, chain
from pandas.errors import EmptyDataError
from tqdm import tqdm
import xarray as xr

from pyexeggutor import (
    build_logger,
)

from tethys.profile_taxonomy import (
    merge_taxonomic_profiling_tables_as_xarray,
)
from tethys.profile_pathway import (
    merge_pathway_profiling_tables_as_xarray,
)

__program__ = os.path.split(sys.argv[0])[-1]


def main(args=None):
    python_executable = sys.executable
    script_directory  =  os.path.dirname(os.path.abspath( __file__ ))
    script_filename = __program__
    description = """
    Running: {} v{} via Python v{} | {}""".format(__program__, sys.version.split(" ")[0], python_executable, script_filename)
    usage = f"{__program__} -t path/to/profiling/tax -p path/to/profiling/pathway -o path/to/output/"
    epilog = "Tethys"

    parser = argparse.ArgumentParser(description=description, usage=usage, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-t","--taxonomic_profiling_directory", type=str, help = "path/to/profiling/taxonomy/")
    parser.add_argument("-p","--pathway_profiling_directory", type=str, help = "path/to/profiling/pathway/")
    parser.add_argument("-o","--output_directory", type=str,  help = "path/to/output_directory")
    parser.add_argument("-z","--fillna_with_zeros", action="store_true")
    parser.add_argument("-e", "--xarray_engine", type=str, choices={"h5netcdf", "netcdf4"}, default="h5netcdf")
    parser.add_argument("-c", "--xarray_compression_level", type=int, choices=set(range(0, 10)), default=4)
    
    opts = parser.parse_args()
    opts.script_directory  = script_directory
    opts.script_filename = script_filename

    logger = build_logger("tethys merge")
    logger.info(f"Command: {sys.argv}")
    
    if opts.taxonomic_profiling_directory:
        outdir = opts.output_directory or opts.taxonomic_profiling_directory
        os.makedirs(outdir, exist_ok=True)
        for level in ["genomes", "genome_clusters"]:
            try:
                filepath = os.path.join(outdir, f"taxonomic_abundance.{level}.nc")
                X = merge_taxonomic_profiling_tables_as_xarray(
                    profiling_directory=opts.taxonomic_profiling_directory, 
                    level=level, 
                    fillna_with_zeros=bool(opts.fillna_with_zeros), 
                )
                if opts.xarray_compression_level:
                    for v in X.data_vars:
                        X[v].encoding.update({"compression": "gzip", "compression_opts": opts.xarray_compression_level})
                X.to_netcdf(filepath, engine=opts.xarray_engine, mode="w")
            except Exception as e:
                logger.warning(f"No {level} taxonomy files found: {e}")

    if opts.pathway_profiling_directory:
        outdir = opts.output_directory or opts.pathway_profiling_directory
        os.makedirs(outdir, exist_ok=True)

        levels = ["genomes", "genome_clusters"]
        abundance_data_types = ["feature_abundances", "pathway_abundances"]
        prevalence_data_types = ["feature_prevalence", "feature_prevalence-binary", "feature_prevalence-ratio"]
        metrics = ["number_of_reads", "tpm", "coverage"]
        group_to_dataset = {}
        group_to_modes = {}
        for level, data_type, metric in chain(product(levels, abundance_data_types, metrics), product(levels, prevalence_data_types, ["number_of_reads"])):
            illegal_conditions = [
                (level == "genomes") and (data_type == "feature_prevalence-ratio"),
                (data_type != "pathway_abundances") and (metric == "coverage"),
            ]
            if any(illegal_conditions):
                continue
            try:
                group = (data_type.split("_")[0], level)
                if group not in group_to_dataset:
                    group_to_dataset[group] = xr.Dataset()
                    group_to_modes[group] = "w"
                filepath = os.path.join(outdir, f"{group[0]}.{group[1]}.nc")
                name = metric if "abundances" in data_type else data_type.split("_")[-1]
                X = merge_pathway_profiling_tables_as_xarray(
                    profiling_directory=opts.pathway_profiling_directory, 
                    data_type=data_type, 
                    level=level, 
                    metric=metric, 
                    fillna_with_zeros=bool(opts.fillna_with_zeros), 
                )
                group_to_dataset[group][name] = X
                if opts.xarray_compression_level:
                    group_to_dataset[group][name].encoding.update({"compression": "gzip", "compression_opts": opts.xarray_compression_level})
                group_to_dataset[group].to_netcdf(filepath, engine=opts.xarray_engine, mode=group_to_modes[group])
                group_to_modes[group] = "a"
            except Exception as e:
                logger.warning(f"Could not merge {data_type}.{level}.{metric}: {e}")

    logger.info("Completed tethys-merge")

if __name__ == "__main__":
    main()
