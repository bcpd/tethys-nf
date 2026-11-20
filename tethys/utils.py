#!/usr/bin/env python
from collections import defaultdict
import ast
import gzip
import os


def find_profile_tables(profiling_directory, filename):
    tables = []
    missing = []
    for directory, _, filenames in os.walk(profiling_directory, followlinks=True):
        if directory == profiling_directory or os.path.basename(directory) != "output":
            continue
        if filename in filenames:
            tables.append(os.path.join(directory, filename))
        else:
            missing.append(os.path.basename(os.path.dirname(directory)))

    # A completely absent table group may be optional. A partial group loses sample data.
    if tables and missing:
        raise ValueError(f"Missing {filename} for sample(s): {', '.join(sorted(missing))}")
    return sorted(tables)


def _parse_feature_set(value):
    value = value.strip()
    if not value:
        return set()
    if value.startswith("{") or value.startswith("[") or value.startswith("("):
        parsed = ast.literal_eval(value)
        if isinstance(parsed, str):
            return {parsed}
        return set(parsed)
    return {value}


def read_annotations(filepath, format="pykofamsearch"):
    gene_to_features = defaultdict(set)
    reformatted = {
        "custom",
        "pykofamsearch-reformatted",
        "pyhmmsearch-reformatted",
    }

    opener = gzip.open if str(filepath).endswith(".gz") else open
    with opener(filepath, "rt") as handle:
        first = True
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if first and fields[0] in {"id_gene", "gene", "query", "target"}:
                first = False
                continue
            first = False

            if format in {"pykofamsearch", "pyhmmsearch"}:
                if len(fields) >= 2:
                    gene_to_features[fields[0]].add(fields[1])
            elif format in reformatted:
                if len(fields) >= 2:
                    gene_to_features[fields[0]].update(_parse_feature_set(fields[1]))
            else:
                raise ValueError(f"Unsupported annotation format: {format}")

    return {gene: set(features) for gene, features in gene_to_features.items()}
