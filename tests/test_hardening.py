import importlib.util
import csv
import glob
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HardeningTests(unittest.TestCase):
    def test_manifest_preserves_dotted_ids_and_original_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            original = tmp / "inputs with spaces" / "sample.v1.fna"
            original.parent.mkdir()
            original.write_text(">contig\nACGT\n")

            prodigal = tmp / "build" / "prodigal"
            prodigal.mkdir(parents=True)
            (prodigal / "sample.v1.ffn").write_text(">gene1\nACGT\n")

            clusters = tmp / "clusters.tsv"
            clusters.write_text("cluster_id\tmember_id\tpath\nPSLC-00001\tsample.v1.fna\tstaged/sample.v1.fna\n")
            genomes = tmp / "genomes.list"
            genomes.write_text(f"{original}\n")
            manifest = tmp / "manifest.tsv"

            subprocess.run(
                [
                    sys.executable,
                    str(REPO / "bin" / "tethys-build-manifest.py"),
                    "--genomes_list",
                    str(genomes),
                    "--clusters",
                    str(clusters),
                    "--prodigal_dir",
                    str(prodigal),
                    "-o",
                    str(manifest),
                ],
                check=True,
            )

            self.assertEqual(
                manifest.read_text().strip(),
                f"sample.v1\t{original}\t{prodigal / 'sample.v1.ffn'}\tPSLC-00001",
            )

    def test_manifest_rejects_duplicate_genome_filenames(self):
        module = load_module("tethys_build_manifest", REPO / "bin" / "tethys-build-manifest.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            genomes = tmp / "genomes.list"
            genomes.write_text(f"{tmp / 'a' / 'sample.fna'}\n{tmp / 'b' / 'sample.fna'}\n")
            with self.assertRaisesRegex(ValueError, "Duplicate genome filenames"):
                module.read_genome_paths(str(genomes))

    def test_profile_modules_use_explicit_typed_read_records_and_shell_quoting(self):
        r1 = re.compile(r"(?i)^.+[._-]R1(?:_001)?\.(?:fastq|fq)(?:\.gz)?$")
        r2 = re.compile(r"(?i)^.+[._-]R2(?:_001)?\.(?:fastq|fq)(?:\.gz)?$")
        self.assertRegex("tumorR1_sample_R1.fastq.gz", r1)
        self.assertRegex("tumorR2_sample-R2.fq.gz", r2)
        self.assertNotRegex("tumorR1_sample.fastq.gz", r1)
        self.assertNotRegex("tumorR2_sample.fastq.gz", r2)

        for module_name in ["profile_tax.nf", "profile_func.nf"]:
            source = (REPO / "modules" / module_name).read_text()
            self.assertIn("nextflow.enable.types = true", source)
            self.assertIn("sample_id: String", source)
            self.assertIn("fastq_1: Path", source)
            self.assertIn("fastq_2: Path", source)
            self.assertNotIn("=~ /R1/", source)
            self.assertNotIn("=~ /R2/", source)
            self.assertNotIn("~/(?i)", source)
            self.assertIn("shellQuote(fastq_1)", source)
            self.assertIn("shellQuote(fastq_2)", source)
            self.assertIn("shellQuote(sample_id)", source)
            self.assertIn("shellQuote(index_dir)", source)

    def test_samplesheet_handles_spaces_and_r_tags_in_sample_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reads_dir = tmp / "reads with spaces"
            reads_dir.mkdir()
            r1_path = reads_dir / "tumorR1_case_R1.fastq.gz"
            r2_path = reads_dir / "tumorR1_case_R2.fastq.gz"
            r1_path.write_bytes(b"\x1f\x8b")
            r2_path.write_bytes(b"\x1f\x8b")
            samplesheet = tmp / "samplesheet.csv"
            samplesheet.write_text(
                "sample_id,fastq_1,fastq_2\n"
                f"tumorR1 case,{r1_path},{r2_path}\n"
            )

            with samplesheet.open(newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["sample_id"], "tumorR1 case")
            self.assertEqual(Path(rows[0]["fastq_1"]), r1_path)
            self.assertEqual(Path(rows[0]["fastq_2"]), r2_path)

    def test_mini_reads_glob_matches_samplesheet_pairing(self):
        samplesheet = REPO / "examples" / "mini" / "samplesheet.csv"
        with samplesheet.open(newline="") as handle:
            row = next(csv.DictReader(handle))

        globbed = sorted(
            Path(path).as_posix()
            for mate in ["R1", "R2"]
            for path in glob.glob(str(REPO / "examples" / "mini" / "reads" / f"*_{mate}.fastq.gz"))
        )
        sheet_pair = sorted([
            (REPO / row["fastq_1"]).as_posix(),
            (REPO / row["fastq_2"]).as_posix(),
        ])
        self.assertEqual(row["sample_id"], "sampleA")
        self.assertEqual(globbed, sheet_pair)

    def test_three_column_feature_mapping_keeps_cluster_flag_false(self):
        source = (REPO / "tethys" / "index.py").read_text()
        self.assertIn("contains_genome_cluster_mapping = len(fields) == 4", source)
        self.assertIn('config["contains_genome_cluster_mapping"] = contains_genome_cluster_mapping', source)
        self.assertNotIn('config["contains_genome_cluster_mapping"] = True', source)

    def test_merge_normalizes_sample_prefix_and_rejects_duplicates(self):
        for module_path in [REPO / "tethys" / "profile_taxonomy.py", REPO / "tethys" / "profile_pathway.py"]:
            source = module_path.read_text()
            self.assertIn('sample_dir[len("sample="):]', source)
            self.assertIn("Duplicate normalized sample ID", source)

    def test_merge_does_not_swallow_unexpected_exceptions(self):
        source = (REPO / "bin" / "tethys-merge.py").read_text()
        self.assertNotIn("except Exception", source)
        self.assertIn("except FileNotFoundError", source)


if __name__ == "__main__":
    unittest.main()
