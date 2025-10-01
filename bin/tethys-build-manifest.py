#!/usr/bin/env python3
import sys, os, argparse
import csv

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

    with open(args.genomes_list) as gl, open(args.out, 'w', newline='') as out:
        w = csv.writer(out, delimiter='\t')
        for line in gl:
            asm = line.rstrip()
            if not asm:
                continue
            base = os.path.basename(asm)
            id_genome = base.split('.')[0]
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

