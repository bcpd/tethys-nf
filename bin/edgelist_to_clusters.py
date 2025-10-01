#!/usr/bin/env python3
import sys, argparse, csv
import networkx as nx

p = argparse.ArgumentParser()
p.add_argument('--basename', action='store_true')
p.add_argument('-t', '--ani', type=float, default=95)
p.add_argument('-a', '--af', type=float, default=50)
p.add_argument('--af_mode', default='relaxed')
p.add_argument('--cluster_prefix', default='PSLC-')
p.add_argument('-o', '--out', required=True)
p.add_argument('--identifiers', required=True)
p.add_argument('--export_graph')
p.add_argument('--export_dict')
p.add_argument('--export_representatives', required=True)
args = p.parse_args()

# Map ID→path
id2path = {}
with open(args.identifiers) as fh:
    for line in fh:
        i, pth = line.rstrip().split('\t')
        id2path[i] = pth

G = nx.Graph()

reader = csv.DictReader(sys.stdin, delimiter='\t', fieldnames=['q','s','ani','af','rest'])
for row in reader:
    try:
        ani = float(row['ani']); af = float(row['af'])
    except Exception:
        continue
    if ani >= args.ani and af >= args.af:
        G.add_edge(row['q'], row['s'])

for i in id2path:
    if i not in G:
        G.add_node(i)

clusters = []
rep_rows = []
for idx, comp in enumerate(nx.connected_components(G), start=1):
    comp = sorted(comp)
    cid = f"{args.cluster_prefix}{idx:05d}"
    for nid in comp:
        clusters.append((cid, nid, id2path.get(nid, '')))
    rep = comp[0]
    rep_rows.append((cid, rep, id2path.get(rep, '')))

with open(args.out, 'w') as out:
    out.write('cluster_id\tmember_id\tpath\n')
    for row in clusters:
        out.write('\t'.join(row) + '\n')

with open(args.export_representatives, 'w') as rep:
    rep.write('cluster_id\trepresentative_id\tpath\n')
    for row in rep_rows:
        rep.write('\t'.join(row) + '\n')
