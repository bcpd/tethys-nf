#!/usr/bin/env python
from collections import defaultdict
import ast
import gzip


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
