#!/usr/bin/env python3
import sys, os, argparse
import csv
from collections import Counter
from pathlib import Path

GENOME_SUFFIXES = (".fasta", ".fna", ".fa")


def genome_id_from_path(filepath):
    """Return the Nextflow-like baseName for supported genome FASTA files."""
    name = Path(filepath).name
    lower_name = name.lower()
    for suffix in GENOME_SUFFIXES:
        if lower_name.endswith(suffix):
            return name[: -len(suffix)]
    return Path(name).stem


def read_genome_paths(genomes_list):
    with open(genomes_list) as handle:
        paths = [line.rstrip("\n") for line in handle if line.strip()]

    filenames = [Path(path).name for path in paths]
    duplicate_filenames = sorted(name for name, count in Counter(filenames).items() if count > 1)
    if duplicate_filenames:
        raise ValueError(
            "Duplicate genome filenames are not supported because staged Nextflow inputs "
            f"and cluster membership are keyed by filename: {', '.join(duplicate_filenames)}"
        )

    genome_ids = [genome_id_from_path(path) for path in paths]
    duplicate_ids = sorted(genome_id for genome_id, count in Counter(genome_ids).items() if count > 1)
    if duplicate_ids:
        raise ValueError(
            "Duplicate genome IDs after removing FASTA extensions are not supported: "
            f"{', '.join(duplicate_ids)}"
        )

    return sorted(paths, key=lambda path: Path(path).name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--genomes_list', required=True, help='File listing genome assembly paths (one per line)')
    ap.add_argument('--clusters', help='Optional genome_clusters.tsv with columns: cluster_id\tmember_id\tpath')
    ap.add_argument('--prodigal_dir', default='build/prodigal', help='Directory containing per-genome .ffn files')
    ap.add_argument('-o','--out', required=True, help='Output manifest TSV')
    args = ap.parse_args()

    member_to_cluster = {}
    if args.clusters and os.path.exists(args.clusters):
        with open(args.clusters) as fh:
            next(fh)
            for line in fh:
                cid, mid, path = line.rstrip().split('\t')
                member_to_cluster[mid] = cid

    genome_paths = read_genome_paths(args.genomes_list)

    with open(args.out, 'w', newline='') as out:
        w = csv.writer(out, delimiter='\t')
        for asm in genome_paths:
            base = os.path.basename(asm)
            id_genome = genome_id_from_path(asm)
            ffn = os.path.join(args.prodigal_dir, f"{id_genome}.ffn")
            if os.path.exists(ffn):
                row = [id_genome, asm, ffn]
                cid = member_to_cluster.get(base)
                if cid:
                    row.append(cid)
                w.writerow(row)
            else:
                sys.stderr.write(f"[build-manifest] WARNING: Missing CDS for {id_genome}: {ffn}\n")

if __name__ == '__main__':
    main()
