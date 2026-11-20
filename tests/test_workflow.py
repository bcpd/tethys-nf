import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MERGE_DEPS = ("pandas", "pyarrow", "xarray", "h5netcdf", "tqdm", "pyexeggutor", "kegg_pathway_profiler")

PROFILE_SCRIPT = """
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("-1", type=Path, dest="r1")
parser.add_argument("-2", type=Path, dest="r2")
parser.add_argument("-n")
parser.add_argument("-d", type=Path)
parser.add_argument("-o", type=Path)
args, _ = parser.parse_known_args()
assert args.r1.read_text() == "forward"
assert args.r2.read_text() == "reverse"
config = json.loads((args.d / "config.json").read_text())
sample = args.o / args.n
(sample / "output").mkdir(parents=True)
subprocess.run(f"test -d {sample / 'output'}", shell=True, check=True)
(sample / "output" / "table.tsv").write_text(config.get("suffix", ""))
(sample / "intermediate").mkdir()
"""

MERGE_SCRIPT = """
import argparse
from glob import glob
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--taxonomic_profiling_directory", type=Path)
parser.add_argument("--pathway_profiling_directory", type=Path)
parser.add_argument("--index_directory", type=Path)
parser.add_argument("--output_directory", type=Path)
args, _ = parser.parse_known_args()
if args.index_directory is not None:
    assert (args.index_directory / "config.json").is_file()
def samples(directory):
    files = glob(str(directory / "**/output/table.tsv"), recursive=True)
    return sorted(Path(path).parents[1].name.removeprefix("sample=") + Path(path).read_text() for path in files)

tax = samples(args.taxonomic_profiling_directory)
func = samples(args.pathway_profiling_directory)
assert tax and tax == func, (tax, func)
(args.output_directory / "samples.nc").write_text("\\n".join(tax))
"""


@unittest.skipUnless(shutil.which("nextflow"), "Nextflow is required for workflow tests")
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        shutil.copy(REPO / "main.nf", self.root)
        shutil.copytree(REPO / "modules", self.root / "modules")
        (self.root / "nextflow.config").write_text("process.cpus = 1\n")

        scripts = self.root / "bin"
        scripts.mkdir()
        (scripts / "python").symlink_to(sys.executable)
        for name in ("taxonomy", "pathway"):
            (scripts / f"tethys-profile-{name}.py").write_text(PROFILE_SCRIPT)
        (scripts / "tethys-merge.py").write_text(MERGE_SCRIPT)

        self.index = self.root / "external index"
        self.index.mkdir()
        (self.index / "config.json").write_text("{}")
        fixtures = self.root / "read fixtures"
        fixtures.mkdir()
        (fixtures / "forward.fq").write_text("forward")
        (fixtures / "reverse.fq").write_text("reverse")
        self.sheet = fixtures / "samplesheet.csv"

    def run_workflow(self, *args, script="main.nf", expected_error=None):
        result = subprocess.run(
            ["nextflow", "run", script, "-ansi-log", "false", *args],
            cwd=self.root,
            env={**os.environ, "NXF_OFFLINE": "true", "NXF_DISABLE_CHECK_LATEST": "true"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        if expected_error:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(expected_error, result.stdout)
        else:
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_profile_merges_only_current_samples_and_standalone_merges_published_tables(self):
        self.sheet.write_text(
            "sample_id,fastq_1,fastq_2\n"
            "case A,forward.fq,reverse.fq\n"
            "case B,forward.fq,reverse.fq\n"
        )
        outdir = self.root / "published results"
        for kind in ("tax", "func"):
            old = outdir / "profile" / kind / "sample=old" / "output"
            old.mkdir(parents=True)
            (old / "table.tsv").write_text("")
            sidecar = outdir / "profile" / kind / "case A" / "notes.txt"
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text("keep")

        self.run_workflow(
            "--mode", "profile", "--index_dir", "external index",
            "--samplesheet", str(self.sheet), "--outdir", str(outdir),
        )
        merged = outdir / "artifacts" / "samples.nc"
        self.assertEqual(merged.read_text(), "case A\ncase B")
        for kind in ("tax", "func"):
            profile = outdir / "profile" / kind / "case A"
            self.assertTrue((profile / "output" / "table.tsv").is_file())
            self.assertFalse((profile / "intermediate").exists())
            self.assertEqual((profile / "notes.txt").read_text(), "keep")

        self.run_workflow(
            "--mode", "merge", "--index_dir", "external index",
            "--outdir", str(outdir),
        )
        self.assertEqual(merged.read_text(), "case A\ncase B\nold")

        self.run_workflow("--mode", "merge", "--outdir", str(outdir))
        self.assertEqual(merged.read_text(), "case A\ncase B\nold")

        for kind in ("tax", "func"):
            table = outdir / "profile" / kind / "sample=old" / "output" / "table.tsv"
            table.write_text(" updated")
        self.run_workflow("-resume", "--mode", "merge", "--outdir", str(outdir))
        self.assertEqual(merged.read_text(), "case A\ncase B\nold updated")

    def test_profile_resume_reuses_retained_sample_and_detects_index_edits(self):
        header = "sample_id,fastq_1,fastq_2\n"
        retained = "case A,forward.fq,reverse.fq\n"
        self.sheet.write_text(header + retained + "case B,forward.fq,reverse.fq\n")
        outdir = self.root / "results"
        args = (
            "--mode", "profile", "--index_dir", str(self.index),
            "--samplesheet", str(self.sheet), "--outdir", str(outdir),
        )
        merged = outdir / "artifacts/samples.nc"
        self.run_workflow(*args)
        self.assertEqual(merged.read_text(), "case A\ncase B")

        self.sheet.write_text(header + retained)
        self.run_workflow("-resume", "-with-trace", "subset.tsv", *args)
        trace = (self.root / "subset.tsv").read_text()
        self.assertEqual(trace.count("CACHED"), 2, trace)
        self.assertEqual(merged.read_text(), "case A")

        (self.index / "config.json").write_text('{"suffix": " updated"}')
        self.run_workflow("-resume", *args)
        self.assertEqual(merged.read_text(), "case A updated")

        cached_tables = list(self.root.glob("work/*/*/profile/tax/case A/output/table.tsv"))
        self.assertTrue(cached_tables)
        for table in cached_tables:
            table.unlink()
        self.run_workflow("-resume", "-with-trace", "repair.tsv", *args)
        trace = (self.root / "repair.tsv").read_text()
        self.assertRegex(trace, r"PROFILE_TAX \(case A\)\tCOMPLETED\t")
        self.assertEqual(merged.read_text(), "case A updated")

    @unittest.skipUnless(all(find_spec(dep) for dep in MERGE_DEPS), "Merge dependencies are required")
    def test_real_merge_includes_all_samples_and_rejects_partial_tables(self):
        import pandas as pd
        import xarray as xr

        shutil.copy(REPO / "bin/tethys-merge.py", self.root / "bin")
        shutil.copytree(REPO / "tethys", self.root / "tethys", ignore=shutil.ignore_patterns("__pycache__"))
        (self.index / "config.json").write_text(
            '{"contains_genome_cluster_mapping": false, "contains_pathways": false}'
        )
        outdir = self.root / "published results"
        for sample, value in ((".case", 2), ("sample=legacy", 5)):
            tax = outdir / "profile" / "tax" / sample / "output"
            func = outdir / "profile" / "func" / sample / "output"
            tax.mkdir(parents=True)
            func.mkdir(parents=True)
            abundance = pd.DataFrame({"abundance": [value]}, index=["genome"])
            abundance.to_parquet(tax / "taxonomic_abundance.genomes.parquet")
            (abundance * 2).to_parquet(tax / "sequence_abundance.genomes.parquet")
            feature_index = pd.MultiIndex.from_tuples([("genome", "K00001")])
            for metric, count in (("number_of_reads", value), ("tpm", value * 3)):
                pd.DataFrame({metric: [count]}, index=feature_index).to_parquet(
                    func / f"feature_abundances.genomes.{metric}.parquet"
                )
            prevalence = pd.DataFrame({"K00001": [1]}, index=["genome"])
            prevalence.to_parquet(func / "feature_prevalence.genomes.parquet")
            prevalence.to_parquet(func / "feature_prevalence-binary.genomes.parquet")

        self.run_workflow(
            "--mode", "merge", "--index_dir", str(self.index), "--outdir", str(outdir),
        )
        artifacts = outdir / "artifacts"
        self.assertEqual(
            {path.name for path in artifacts.iterdir()},
            {"taxonomic_abundance.genomes.nc", "feature.genomes.nc"},
        )
        with xr.open_dataset(artifacts / "taxonomic_abundance.genomes.nc", engine="h5netcdf") as tax:
            self.assertEqual(tax.samples.values.tolist(), [".case", "legacy"])
            self.assertEqual(tax.taxonomic_abundances.sel(genomes="genome").values.tolist(), [2, 5])
            self.assertEqual(tax.sequence_abundances.sel(genomes="genome").values.tolist(), [4, 10])
        with xr.open_dataset(artifacts / "feature.genomes.nc", engine="h5netcdf") as func:
            self.assertEqual(func.samples.values.tolist(), [".case", "legacy"])
            self.assertEqual(func.tpm.sel(genomes="genome", features="K00001").values.tolist(), [6, 15])

        missing = outdir / "profile/func/.case/output/feature_abundances.genomes.tpm.parquet"
        missing.unlink()
        self.run_workflow(
            "-resume", "--mode", "merge", "--index_dir", str(self.index), "--outdir", str(outdir),
            expected_error="Missing feature_abundances.genomes.tpm.parquet for sample(s): .case",
        )
        with xr.open_dataset(artifacts / "feature.genomes.nc", engine="h5netcdf") as func:
            self.assertEqual(func.tpm.sel(genomes="genome", features="K00001").values.tolist(), [6, 15])

    def test_samplesheet_rejects_duplicate_sample_ids_before_profiling(self):
        self.sheet.write_text(
            "sample_id,fastq_1,fastq_2\n"
            "case A,forward.fq,reverse.fq\n"
            "case A,forward.fq,reverse.fq\n"
        )
        self.run_workflow(
            "--mode", "profile", "--index_dir", str(self.index),
            "--samplesheet", str(self.sheet),
            expected_error="Duplicate samplesheet sample_id: 'case A'",
        )
        self.assertFalse((self.root / "results" / "profile").exists())

    def test_samplesheet_rejects_header_only_input(self):
        self.sheet.write_text("sample_id,fastq_1,fastq_2\n")
        self.run_workflow(
            "--mode", "profile", "--index_dir", str(self.index),
            "--samplesheet", str(self.sheet), expected_error="is empty.",
        )

    def test_checkm2_reads_staged_proteins_and_database_with_spaces(self):
        (self.root / "first.faa").write_text("first")
        (self.root / "second.faa").write_text("second")
        db = self.root / "db with spaces" / "CheckM2_database"
        db.mkdir(parents=True)
        (db / "first db.dmnd").write_text("database")
        (self.root / "checkm2_test.nf").write_text(
            """nextflow.enable.types = true
include { CHECKM2 } from './modules/checkm2.nf'
include { VERIFY_CHECKM2_DB } from './modules/verify_checkm2_db.nf'

workflow {
    db = VERIFY_CHECKM2_DB(channel.value('db with spaces'))
    input = db.map { dir -> tuple([file('first.faa'), file('second.faa')], dir) }
    CHECKM2(input)
}
"""
        )
        checkm2 = self.root / "bin" / "checkm2"
        checkm2.write_text(
            """#!/usr/bin/env bash
set -eu
test "$1" = predict
shift
while [ "$#" -gt 0 ]; do
    case "$1" in
      -i) proteins=$2; shift ;;
      -o) output=$2; shift ;;
      --database_path) database=$2; shift ;;
    esac
    shift
done
test "$(cat "$database")" = database
test "$(cat "$proteins/first.faa")" = first
test "$(cat "$proteins/second.faa")" = second
touch "$output/quality_report.tsv"
"""
        )
        checkm2.chmod(0o755)
        self.run_workflow("--outdir", "results", script="checkm2_test.nf")
        self.assertTrue((self.root / "results/build/checkm2/quality_report.tsv").is_file())


if __name__ == "__main__":
    unittest.main()
