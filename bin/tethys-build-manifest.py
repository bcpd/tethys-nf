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


def cds_id_from_path(filepath):
    name = Path(filepath).name
    lower_name = name.lower()
    if lower_name.endswith(".ffn"):
        return name[:-4]
    return Path(name).stem


def read_ffn_paths(ffn_files_list):
    if not ffn_files_list:
        return {}

    with open(ffn_files_list) as handle:
        paths = [line.rstrip("\n") for line in handle if line.strip()]

    id_to_path = {}
    duplicates = []
    for path in paths:
        genome_id = cds_id_from_path(path)
        if genome_id in id_to_path:
            duplicates.append(genome_id)
        id_to_path[genome_id] = path

    if duplicates:
        raise ValueError(
            "Duplicate Prodigal FFN files for genome IDs: "
            f"{', '.join(sorted(set(duplicates)))}"
        )

    return id_to_path


def read_cluster_mapping(clusters):
    member_to_cluster = {}
    if not clusters or not os.path.exists(clusters):
        return member_to_cluster

    with open(clusters) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames and {"cluster_id", "member_id"}.issubset(reader.fieldnames):
            for row in reader:
                cid = row.get("cluster_id", "").strip()
                mid = row.get("member_id", "").strip()
                if cid and mid:
                    member_to_cluster[mid] = cid
                    member_to_cluster[genome_id_from_path(mid)] = cid
            return member_to_cluster

    with open(clusters) as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 2 or fields[0] == "cluster_id":
                continue
            cid, mid = fields[:2]
            if cid and mid:
                member_to_cluster[mid] = cid
                member_to_cluster[genome_id_from_path(mid)] = cid

    return member_to_cluster


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--genomes_list', required=True, help='File listing genome assembly paths (one per line)')
    ap.add_argument('--clusters', help='Optional genome_clusters.tsv with columns: cluster_id\tmember_id\tpath')
    ap.add_argument('--prodigal_dir', default='build/prodigal', help='Directory containing per-genome .ffn files')
    ap.add_argument('--ffn_files_list', help='File listing Prodigal .ffn paths staged by Nextflow')
    ap.add_argument('-o','--out', required=True, help='Output manifest TSV')
    args = ap.parse_args()

    member_to_cluster = read_cluster_mapping(args.clusters)

    genome_paths = read_genome_paths(args.genomes_list)
    if not genome_paths:
        raise ValueError("--genomes_list did not contain any genome paths")
    ffn_by_id = read_ffn_paths(args.ffn_files_list)

    rows_written = 0
    with open(args.out, 'w', newline='') as out:
        w = csv.writer(out, delimiter='\t')
        for asm in genome_paths:
            base = os.path.basename(asm)
            id_genome = genome_id_from_path(asm)
            ffn = ffn_by_id.get(id_genome, os.path.join(args.prodigal_dir, f"{id_genome}.ffn"))
            if os.path.exists(ffn):
                row = [id_genome, asm, ffn]
                cid = member_to_cluster.get(base) or member_to_cluster.get(id_genome)
                if cid:
                    row.append(cid)
                w.writerow(row)
                rows_written += 1
            else:
                sys.stderr.write(f"[build-manifest] WARNING: Missing CDS for {id_genome}: {ffn}\n")

    if rows_written == 0:
        raise ValueError(
            "Manifest would be empty because no genome paths had matching Prodigal .ffn files"
        )

if __name__ == '__main__':
    main()
