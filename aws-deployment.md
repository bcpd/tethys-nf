# Assess AWS deployment

> User context
>
> Attachments:
> - You are working in the current repository as a senior bioinformatics platform e…: `~/.codex/attachments/2b0f7ec2-2469-4b96-861e-c3c6eb918f32/pasted-text.txt`

<details><summary>8 previous messages</summary>

> I’ll read the attached brief first, then inspect the repository state and carry out the requested work.
>
> <details><summary>Explored 2 files</summary>
>
> - Read `~/.codex/attachments/2b0f7ec2-2469-4b96-861e-c3c6eb918f32/pasted-text.txt`
> - Read `~/.codex/attachments/2b0f7ec2-2469-4b96-861e-c3c6eb918f32/pasted-text.txt`
>
> </details>
>
> This is Phase 1 only: I’ll keep the repository untouched, inventory the pipeline and Git state, then verify the three deployment paths against current official AWS, Nextflow, and Seqera documentation. The result will end with an exact Phase 2 approval list.
>
> <details><summary>Explored 7 files, 2 searches, 2 lists, ran 3 commands</summary>
>
> - Ran `pwd; git status --short --branch; git log -8 --oneline --decorate; rg --files -g '!work/**' -g '!results*/**' -g '!.nextflow/**' | sort`
>
> <details><summary>Explored 2 files</summary>
>
> - Read `./nextflow.config`
> - Read `./main.nf`
>
> </details>
>
> - Ran `for f in conf/*.config modules/*.nf docker/* envs/*.yml; do echo "### $f"; sed -n '1,240p' "$f"; done`
>
> - Ran `find . -maxdepth 3 -type f -not -path './.git/*' -not -path './work/*' -not -path './results*/*' | sort; sed -n '1,240p' README.md; sed -n '1,420p' TUTORIAL.md; sed -n '1,260p' tests/test_hardening.py; for f in schema/*.yaml examples/README.md examples/mini/params.json examples/mini/samplesheet.csv .gitignore .github/workflows/*; do if [ -f "$f" ]; then echo "### $f"; sed -n '1,240p' "$f"; fi; done`
>
> <details><summary>Explored 5 files, 2 searches, 2 lists</summary>
>
> - Listed files
> - Listed files
> - Read `./tests/test_hardening.py`
> - Searched for `(/Users/|/home/|/central/|AWS_|AKIA|secret|password|token|subprocess|os\.system|shutil\.(move|copy|rmtree)|\.rename\(|\.replace\(|symlink|link_to|requests\.|urllib|curl|wget|http|Path\(|open\(|temp|TMP|CUDA|gpu|publishDir|errorStrategy|maxRetries|maxErrors|scratch|disk|accelerator|executor|container|conda|plugin|workflow\.output|timeline|trace|dag|report|cache|resume)` in `.`
> - Read `./.Rhistory`
> - Read `./.dockerignore`
> - Read `./conf/local.config.example`
> - Read `./PLAN.md`
> - Searched for `subprocess\.(run|call|check_call|Popen)|shutil\.|os\.(rename|replace|remove|unlink|makedirs)|open\(.+['\"]w|NamedTemporary|mkdtemp|download|database_path|index_directory|output_directory` in `bin`
>
> </details>
>
> </details>
>
> The repository inventory has surfaced two decisive portability issues: cloud workers cannot rely on the head node’s `${projectDir}` files or local database paths, and the current images are mutable local tags that contain dependencies but not the pipeline’s Python code. I’m now checking whether each managed target can accommodate the pipeline’s required Nextflow 26.04 typed syntax and its storage/output semantics.
>
> <details><summary>Explored 23 files, a search, ran 2 commands, searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `site:nextflow.io/docs/latest aws batch executor S3 workDir Nextflow official ...`
> - Searched the web for `site:nextflow.io/docs/latest/aws.html AWS Batch executor workDir S3 container official Nextflow ...`
> - Searched the web for `site:nextflow.io/docs/latest "AWS Batch" "workDir" ...`
> - Searched the web for `https://www.nextflow.io/docs/latest/aws.html`
> - Searched the web for `'AWS Batch'`
> - Searched the web for `site:docs.aws.amazon.com/omics/latest/dev HealthOmics private workflow ECR images workflow definition zip nextflow_schema lint ...`
> - Searched the web for `site:docs.aws.amazon.com/batch/latest/userguide retry strategy spot interruptions AWS Batch official ...`
>
> </details>
>
> <details><summary>Explored 26 files, a search</summary>
>
> - Read `./main.nf`
> - Read `./modules/build_manifest.nf`
> - Read `./modules/tethys_index.nf`
> - Read `./modules/profile_tax.nf`
> - Read `./modules/profile_func.nf`
> - Read `./modules/merge_artifacts.nf`
> - Read `./tethys/index.py`
> - Read `./bin/tethys-index.py`
> - Read `./bin/tethys-preprocess.py`
> - Read `./bin/tethys-build-manifest.py`
> - Read `./nextflow.config`
> - Read `./conf/docker.config`
> - Read `./.github/workflows/ci.yml`
> - Read `./tethys/index.py`
> - Read `./bin/tethys-index.py`
> - Read `./bin/tethys-preprocess.py`
> - Read `./modules/verify_kofam_db.nf`
> - Read `./modules/verify_checkm2_db.nf`
> - Read `./docker/Dockerfile.build`
> - Read `./docker/Dockerfile.tethys`
> - Read `./docker/Dockerfile.checkm2`
> - Read `./envs/build.yml`
> - Read `./envs/tethys.yml`
> - Read `./envs/checkm2.yml`
> - Read `./tethys/profile_taxonomy.py`
> - Read `./bin/tethys-profile-taxonomy.py`
> - Searched for `\[.?filepath.?\]|get\(.?filepath|filepath.*genome_to_data|genome_to_data.*filepath` in `tethys`
>
> </details>
>
> - Ran `command -v nextflow || true; nextflow -version 2>/dev/null || true; command -v docker || true; docker --version 2>/dev/null || true; command -v aws || true; aws --version 2>/dev/null || true; command -v terraform || true; terraform version 2>/dev/null | head -3 || true; command -v cfn-lint || true; git status --short --branch`
>
> - Ran `rg -c '^    def test_' tests/test_hardening.py; git log --format='%h %ad %s' --date=short -12; git status --short --branch; git diff --stat; git diff --name-only`
>
> </details>
>
> The option comparison is now settled. Native AWS Batch is the defensible primary target without assuming a Seqera subscription, while HealthOmics is currently blocked by an explicit service limitation: it supports Nextflow 26.04 records but not the static-typing preview feature this pipeline enables. Seqera-managed Batch becomes the preferred operational variant only if Platform availability is confirmed, especially for a shared-filesystem work directory and managed head job.
>
> <details><summary>Plan</summary>
>
> - [x] Inventory repository, Git state, pipeline configuration, modules, environments, tests, and data-flow assumptions
> - [x] Verify current AWS Batch, Seqera Platform, and HealthOmics requirements in official documentation
> - [x] Compare options and design repository-specific target architecture
> - [x] Deliver Phase 1 report, implementation/validation plan, missing inputs, and approval request
>
> </details>
</details>

# Phase 1 AWS deployment assessment

## 1. Recommendation

Primary target: native Nextflow on AWS Batch, using EC2 compute environments, private ECR images, an S3 work directory, and a small persistent EC2 driver.

Confidence: moderate.

Why:

- The pipeline already uses Nextflow DSL2 and is directly compatible with the native `awsbatch` executor.
- No Seqera Platform subscription or installation is confirmed.
- AWS HealthOmics cannot currently run this pipeline unchanged: the repository enables Nextflow 26.04 static typing, which HealthOmics explicitly does not support, even though it supports record types.
- AWS Batch preserves local execution by adding a profile rather than replacing the Conda or Docker profiles.
- The task resource range—1–8 CPUs and 2–16 GB—is straightforward for mixed x86 EC2 instance families.
- The pipeline has no GPU requirement.

The recommendation could change to Seqera-managed AWS Batch if Seqera Platform is available and reducing operational burden is a priority. Its managed head job, Batch Forge, UI, access controls, and optional shared-filesystem work directory fit this workflow well. Wave and Fusion are not required for the initial deployment.

HealthOmics should be reconsidered only if the project accepts removal or isolation of static typing, HealthOmics-specific output handling, ECR-only images, workflow packaging, and service-specific run semantics.

All documentation below was accessed July 10, 2026. Relevant primary sources include the [Nextflow AWS Batch executor](https://docs.seqera.io/nextflow/executor), [Nextflow AWS guide](https://docs.seqera.io/nextflow/aws), [Seqera AWS Batch environments](https://docs.seqera.io/platform-cloud/compute-envs/aws-batch), and [HealthOmics Nextflow support](https://docs.aws.amazon.com/omics/latest/dev/workflow-definition-nextflow.html).

## 2. Current cloud-readiness assessment

### Already suitable

- DSL2 entry point at [main.nf](./main.nf:1), with three named workflows for build, profile, and merge.
- Required Nextflow version is declared as `>=26.04.0`; the local installation is 26.04.4.
- Static typed parameters and typed read records provide useful validation.
- Scientific tasks are reasonably decomposed:
  - Per-genome: Prodigal and KOfam.
  - Per-sample: taxonomic and functional profiling.
  - Aggregating: clustering, index building, and artifact merge.
- Every scientific tool has either a Conda environment or a Docker-image assignment.
- CPU and memory requests exist for the main scientific processes.
- The repository contains a small, non-sensitive fixture and 14 Python hardening tests.
- There are no Nextflow plugins, GPUs, preview executors, or external subworkflow repositories.
- Git is clean and synchronized with `origin/main`.
- No credentials, account IDs, or obvious secrets were found in tracked files.

### Material gaps

1. Cloud workers cannot access repository code by head-node path.

   Several modules execute `${projectDir}/bin/...` and add `${projectDir}` to `PYTHONPATH`, for example [profile_tax.nf](./modules/profile_tax.nf:41). AWS Batch workers do not share the driver’s repository filesystem.

2. Images are not deployable or immutable.

   The Docker profile uses local `:latest` tags in [docker.config](./conf/docker.config:7). The Dockerfiles install dependencies but do not contain `bin/` or `tethys/`. No registry exists, and neither base images nor final images are pinned by digest.

3. Several directory values bypass Nextflow staging.

   `kofam_db`, `checkm2_db`, `pathway_db`, and `index_dir` are passed as strings. More importantly, original absolute genome paths are written into the manifest at [main.nf](./main.nf:155), then reopened by the index process. Those paths will not exist on another Batch worker.

4. Merge depends on published files as shared local state.

   [merge_artifacts.nf](./modules/merge_artifacts.nf:20) scans `${outdir}/profile/...` rather than consuming profile outputs as Nextflow path inputs. This is unsafe with S3 `publishDir` and relies on local/shared filesystem behavior.

5. Runtime database mutation is inappropriate for cloud production.

   KOfam and CheckM2 verification processes create, download, repair, and sometimes delete database content. Concurrent jobs could race, and database contents are not immutably identified.

6. Resource definitions are incomplete.

   `CHECKM2` and database verification have no explicit CPU, memory, time, or storage requests. Most other tasks have no timeout. No disk requirements are defined. Native AWS Batch on EC2 does not use Nextflow’s `disk` directive, so worker EBS must be sized through the launch template.

7. Reproducibility is incomplete.

   Conda dependencies include version ranges; there are no lock files. Images use mutable tags. KOfam, CheckM2, and the optional pathway database can be downloaded at run time without recorded checksums or versions.

8. CI currently contradicts the pipeline requirement.

   CI sets `NXF_VER=25.04.7` in [ci.yml](./.github/workflows/ci.yml:19), while the pipeline requires 26.04. It also checks obsolete `sample=sampleA` output paths.

9. Parameter schema is absent.

   `schema/*.yaml` describes scientific stages; it is not a `nextflow_schema.json` and does not validate launch parameters or generate a HealthOmics parameter template.

10. Operational artifacts are optional rather than standard.

    Reports are enabled manually. Trace, timeline, DAG, run metadata, cost tags, log retention, work retention, and cleanup are not configured.

### Scientific-behavior risks

The proposed work should not change clustering thresholds, annotation backend, profiling algorithms, output formats, or defaults. The main regression risk is changing genome path handling: Sylph stores genome path identifiers in its database and downstream code maps them back to genome IDs. Any staging fix must preserve that mapping and be tested against byte- or value-equivalent local outputs.

The uncompressed SAM output requested by functional profiling can also be a dominant intermediate-storage cost.

## 3. Option comparison

| Criterion | Native AWS Batch | Seqera-managed AWS Batch | HealthOmics |
|---|---|---|---|
| Current Nextflow syntax | Compatible | Compatible | Blocked by static typing |
| Workflow changes | Moderate staging/path fixes | Same fixes; shared storage may reduce them | Substantial |
| Containers | Reachable registry required | Reachable registry; Wave optional | Private ECR, same Region, x86_64 only |
| Driver/head | User-managed EC2 recommended | Managed head job | Service-managed |
| Work storage | S3 required | S3, EFS, or FSx | Managed run filesystem |
| Resume | S3 work plus persistent driver cache | Platform-managed run context plus work storage | Call cache; not native `-resume` equivalence |
| Iterative development | Good, but operationally manual | Best user experience | Workflow-version/run oriented |
| Observability | Batch and CloudWatch plus Nextflow reports | Platform UI plus CloudWatch | CloudWatch, S3 logs, task metrics |
| IAM burden | Highest | Medium; Forge needs broad provisioning permissions | Medium; service role and ECR/S3 access |
| Portability | Highest | High, with platform dependency | Lowest |
| Current readiness | Best unconditional option | Best if Platform exists | Not deployable unchanged |

### Native AWS Batch

Nextflow requires a container for every process and an S3 work directory. It can launch from a workstation or EC2, but EC2 is recommended for long workloads. Nextflow automatically creates task job definitions; infrastructure must supply compute environments and queues. Without Wave/Fusion, AWS CLI support must be present in the images or worker AMI. [Nextflow documents these requirements directly](https://docs.seqera.io/nextflow/aws).

EC2 is preferred over Fargate because Nextflow’s Fargate support remains experimental and requires Wave. The pipeline also benefits from flexible instance sizing, persistent EBS scratch, and EFS-mounted reference databases.

### Seqera-managed AWS Batch

Seqera can provision resources with Batch Forge or use manually supplied Batch infrastructure. It supports separate head and compute queues, distinct head and task roles, resource labels, CloudWatch access, and S3/EFS/FSx work storage. Forge-created resources can be disposed when the compute environment is deleted. These features reduce operational work but require Platform availability, licensing decisions, and provisioning IAM permissions. [Seqera documents both automatic and manual modes](https://docs.seqera.io/platform-cloud/compute-envs/aws-batch).

The pipeline must work without Wave or Fusion first. They should be evaluated only after baseline profiling identifies S3 staging as a meaningful bottleneck.

### AWS HealthOmics

HealthOmics now supports Nextflow 26.04 and record types, but not static typing. This repository sets `nextflow.enable.types = true` throughout and uses typed parameters and channels. That is a direct compatibility blocker documented in the [HealthOmics 26.04 support matrix](https://docs.aws.amazon.com/omics/latest/dev/workflow-definition-nextflow.html).

Additional adaptations would include:

- Private, same-Region ECR images; public registries and ARM images are unsupported.
- Workflow ZIP or repository integration and workflow-version management.
- `nextflow_schema.json` or an explicit parameter template.
- Output publication through `/mnt/workflow/pubdir` or `/mnt/workflow/output`.
- HealthOmics storage sizing, task metrics, service role, linting, and retry configuration.
- Validation of its call-cache behavior against current `-resume` expectations.

See [HealthOmics container requirements](https://docs.aws.amazon.com/omics/latest/dev/workflows-ecr.html), [workflow creation](https://docs.aws.amazon.com/omics/latest/dev/create-private-workflow.html), and [run storage](https://docs.aws.amazon.com/omics/latest/dev/workflows-run-types.html).

## 4. Proposed native AWS Batch architecture

### Execution path

1. An On-Demand x86_64 EC2 driver runs Nextflow 26.04.x.
2. The driver uses an encrypted persistent EBS volume for the repository, `.nextflow/cache`, launch metadata, and reports.
3. Nextflow submits task jobs to AWS Batch EC2 queues.
4. Tasks stage inputs and outputs through `s3://<WORK_BUCKET>/tethys/<environment>/work/<run-id>/`.
5. Final outputs publish to `s3://<RESULTS_BUCKET>/tethys/<run-id>/`.
6. KOfam and CheckM2 references are mounted read-only from encrypted EFS because KOfam’s many files would otherwise be repeatedly downloaded for every per-genome task.

### Containers

Three x86_64 images remain aligned with the current environments:

- `tethys-build`
- `tethys-runtime`
- `tethys-checkm2`

They will contain the appropriate repository Python code, Bash, and AWS staging support. Images will be pushed to private ECR and referenced by digest. Local Docker tags remain unchanged for developers.

### Compute

- On-Demand queue for `CLUSTER_SKANI`, `TETHYS_INDEX`, merge, database validation, and the initial scientific baseline.
- Spot queue, enabled after baseline validation, for idempotent per-genome and per-sample tasks.
- Diversified x86 families such as current-generation `c`, `m`, and `r` Intel/AMD instances.
- Initial smoke-test ceiling: 32–64 vCPUs; production ceiling remains a required input.
- Encrypted gp3 worker root volumes, initially modeled at 200 GB but sized only after real input/intermediate measurements.
- No GPU, Fargate, Graviton, FSx, Wave, or Fusion initially.

AWS recommends diversified capacity and explicit Spot retry handling; Nextflow no longer supplies implicit Spot retries by default. See [AWS Batch Spot guidance](https://docs.aws.amazon.com/batch/latest/userguide/bestpractice6.html) and [Nextflow Spot retry behavior](https://nextflow.io/docs/latest/updating-spot-retries.html).

### IAM

Separate roles:

- Driver role: submit/describe/terminate jobs, register/deregister Nextflow-created job definitions, read ECR metadata, access scoped S3 prefixes, write run metadata, and pass only the approved task role.
- Batch service role.
- EC2 instance role: ECS/ECR and CloudWatch agent operations.
- Task job role: scoped S3 input/work/results access, EFS access where required, ECR pulls, KMS use, and CloudWatch logging.

No static AWS credentials will be stored.

### Networking and security

- Existing VPC and private subnets supplied as parameters.
- No inbound SSH; Systems Manager for driver access.
- S3 gateway endpoint and ECR API/DKR, CloudWatch Logs, STS, and Systems Manager endpoints where appropriate.
- EFS security group permitting NFS only from driver/Batch security groups.
- S3 Block Public Access, TLS-only bucket policies, encryption at rest, encrypted EBS/EFS, and optional customer-managed KMS keys.
- No runtime reference downloads in the production profile. A NAT gateway is unnecessary if all dependencies and references are pre-provisioned and the required endpoints exist.
- Project, environment, owner, cost-center, and run tags.

### Logging, retry, and resume

- Batch job logs in a dedicated CloudWatch log group with finite retention.
- Nextflow trace, report, timeline, DAG, resolved configuration, Git revision, image digests, reference checksums, and parameter snapshot stored under `pipeline_info/`.
- Explicit bounded retries only for idempotent tasks and recognized infrastructure/Spot failures.
- Deterministic tool failures terminate after the bounded retry policy.
- `-resume` uses the persistent driver cache plus retained S3 work objects.
- Queue-blocked EventBridge notifications and optional automatic cancellation for long-stuck `RUNNABLE` jobs. AWS documents these controls in [Jobs stuck in RUNNABLE](https://docs.aws.amazon.com/batch/latest/userguide/job_stuck_in_runnable.html).

### Cost and cleanup

Primary cost drivers are compute duration, Spot interruption waste, S3 work volume and requests, EFS storage/throughput, worker EBS, CloudWatch ingestion, ECR storage, and the always-on duration of the driver.

Controls:

- `minvCpus=0` for Batch compute environments.
- Conservative `maxvCpus`.
- Driver stopped outside active runs.
- S3 work expiration after a configurable validation window, plus incomplete multipart-upload cleanup.
- Longer retention for results and run metadata.
- Finite CloudWatch retention and ECR lifecycle policies.
- Explicit cleanup script that previews objects/resources before deletion.
- No automatic deletion until scientific comparison and user approval are complete.

## 5. File-level Phase 2 implementation plan

| File | Action | Purpose and main content | Local effect | Status |
|---|---|---|---|---|
| `nextflow.config` | Modify | Add `awsbatch` profile include; add internal code-location/database-download controls; complete missing task resources/timeouts | Existing profiles unchanged | Required |
| `conf/awsbatch.config` | Create | Executor, queues, Region placeholder, S3 work path, ECR digest placeholders, retry policy, concurrency caps, reports, and AWS role settings | None unless selected | Required |
| `main.nf` | Modify | Carry genome/index/profile artifacts as staged paths rather than inaccessible strings; preserve typed records and all four modes | Same scientific flow | Required |
| `modules/build_manifest.nf` | Modify | Use the container code root and preserve explicit genome provenance | No output-format change | Required |
| `modules/cluster_skani.nf` | Modify | Use containerized helper path | No scientific change | Required |
| `modules/prodigal_pyro.nf` | Modify | Use containerized helper path | No scientific change | Required |
| `modules/tethys_preprocess.nf` | Modify | Use containerized helper path | No scientific change | Required |
| `modules/tethys_index.nf` | Modify | Stage genome assemblies and pathway DB explicitly; create task-local genome mapping before Sylph indexing | Genome identifiers preserved; internal path provenance changes | Required |
| `modules/profile_tax.nf` | Modify | Accept a staged index path and use containerized code | Outputs unchanged | Required |
| `modules/profile_func.nf` | Modify | Accept a staged index path and use containerized code | Outputs unchanged | Required |
| `modules/merge_artifacts.nf` | Modify | Consume actual profile outputs and staged index instead of scanning published storage | Outputs unchanged | Required |
| `modules/verify_kofam_db.nf` | Modify | Add validation-only mode that forbids cloud mutation/download | Local auto-download remains default | Required |
| `modules/verify_checkm2_db.nf` | Modify | Add validation-only mode that forbids cloud mutation/download | Local auto-download remains default | Required |
| `docker/Dockerfile.build` | Modify | Copy required code, install staging support, use pinned base/dependencies | Local image remains available | Required |
| `docker/Dockerfile.tethys` | Modify | Copy `bin/` and `tethys/`, set stable Python path, install staging support | Local image remains available | Required |
| `docker/Dockerfile.checkm2` | Modify | Pin base and install staging support | No scientific change | Required |
| `.conda-lock/build-linux-64.yml` | Create | Exact build-image dependency lock | None until image build | Required |
| `.conda-lock/tethys-linux-64.yml` | Create | Exact runtime-image dependency lock | None until image build | Required |
| `.conda-lock/checkm2-linux-64.yml` | Create | Exact CheckM2-image dependency lock | None until image build | Required |
| `nextflow_schema.json` | Create | Parameter types, modes, URI/path expectations, and validation | Adds validation/documentation only | Required |
| `tests/test_hardening.py` | Modify | Update path and staging assertions while preserving current regression coverage | Tests only | Required |
| `tests/test_cloud_config.py` | Create | Assert all cloud processes have images/resources and cloud database mutation is disabled | Tests only | Required |
| `.github/workflows/ci.yml` | Modify | Use Nextflow 26.04.x, correct output assertions, run config/schema/container checks | CI only | Required |
| `infra/aws-batch/template.yaml` | Create | CloudFormation for ECR, S3, EFS, IAM, log group, Batch queues/environments, launch template, and optional driver | No effect until deployed | Required |
| `infra/aws-batch/parameters.example.json` | Create | Placeholder-only deployment inputs and tags | None | Required |
| `scripts/aws/build-images.sh` | Create | Reproducible amd64 builds and digest reporting; no push by default | None until invoked | Required |
| `scripts/aws/validate.sh` | Create | Schema, config, container, CloudFormation, IAM, and package checks | Read-only validation | Required |
| `scripts/aws/smoke-test.sh` | Create | Print/submit the approved minimal run with explicit limits | No action without explicit flag/approval | Required |
| `scripts/aws/cleanup.sh` | Create | Inventory-first cleanup commands with destructive confirmation | None until invoked | Required |
| `docs/aws-batch.md` | Create | Deployment, operation, monitoring, retry, resume, cost, rollback, and cleanup runbook | Documentation only | Required |
| `docs/adr/0001-aws-execution-target.md` | Create | Decision record and alternatives | Documentation only | Required |
| `README.md` | Modify | Link the cloud runbook; retain current local quickstart | Documentation only | Required |
| `conf/seqera-awsbatch.config` | Create | Platform-compatible overrides without Wave/Fusion | None unless selected | Optional, only if Seqera is confirmed |
| `docs/healthomics-gap-analysis.md` | Create | Record static-typing and service-specific blockers | Documentation only | Optional |

CloudFormation is proposed because no existing IaC framework or Terraform installation is present, and the selected target is AWS-only. This choice can be changed before Phase 2.

## 6. Validation plan

Phase 2 local validation:

1. Run the 14 Python hardening tests with bytecode writes disabled.
2. Resolve every existing profile and the new AWS profile using Nextflow 26.04.x.
3. Run the existing Conda mini workflow before and after changes.
4. Run the local Docker mini workflow using the rebuilt images.
5. Compare manifests, index metadata, Parquet tables, and NetCDF values and dimensions against the pre-change baseline.
6. Specifically verify Sylph genome-path-to-ID mapping after staged genome handling.
7. Confirm all AWS-executed processes resolve to an immutable x86_64 image.
8. Confirm the cloud profile disables Conda and runtime database mutation.
9. Validate `nextflow_schema.json`.
10. Lint shell scripts and run their dry-run paths.
11. Validate CloudFormation structure and IAM policy syntax. The required AWS CLI and CloudFormation linter are not currently installed.
12. Build images locally without pushing; inspect architecture, entrypoint, included code, and installed versions.
13. Scan tracked and untracked changes for secrets and account-specific identifiers.
14. Confirm deployment packages exclude Git metadata, work/results, databases, caches, credentials, and local config.
15. Review the complete Git diff.

First cloud smoke-test design, after separate deployment approval:

- One tiny genome, one paired-read sample, `--skip_checkm2`, fixed pathway/KOfam references.
- On-Demand only, low `maxvCpus`, unique work/result prefixes.
- Capture Batch/CloudWatch logs and all Nextflow reports.
- Compare scientific outputs with the local Docker baseline.
- Retain work and test resources until cleanup is separately approved.

No tests or pipeline runs were performed in Phase 1 because the brief restricted this phase to read-only inspection.

## 7. Missing information

| Missing value | Why it matters / could change recommendation | Safe example | Where supplied |
|---|---|---|---|
| AWS Region | Service availability, ECR/S3 locality, pricing and residency; can change target | `ca-central-1` | Phase 2 parameter file |
| AWS account ID | ARN construction and IAM scoping; does not normally change target | `123456789012` | Untracked deployment parameters |
| Seqera availability/version/licensing | Could change primary target to Seqera-managed Batch | `Platform Cloud: yes` | Approval response |
| Input volume per run | Determines S3, EBS, EFS, staging and instance design; may favor Seqera/Fusion | `20 samples, 15 GB/sample` | Runbook variables |
| Expected concurrency | Determines Batch `maxvCpus`, quotas and queue design | `40 samples; 80 concurrent tasks` | IaC parameters |
| Data classification | Controls KMS, network isolation, logging and audit; may favor HealthOmics after code adaptation | `research human genomic, de-identified` | Security section of parameter file |
| Primary optimization goal | Affects Spot use and operational platform choice | `balanced` | Approval response |
| Existing IaC preference | Could replace CloudFormation with Terraform/CDK | `CloudFormation` | Approval response |
| Existing registry | Determines whether ECR resources and migration are needed | `none` or an ECR URI | Parameter file |
| Existing VPC/subnets/endpoints | Determines networking resources and NAT requirements | `vpc-…, subnet-…, subnet-…` | Untracked deployment parameters |
| KOfam/CheckM2/pathway versions and sizes | Determines EFS sizing, checksums and reproducibility | `KOfam 2026-05, 45 GB` | Reference manifest |
| Index and largest intermediate sizes | Determines worker disk; SAM mappings may dominate | `index 80 GB; max task 250 GB` | Measurement worksheet |
| Retention and recovery requirements | Determines S3 lifecycle and resume window | `work 30 days; results 7 years` | IaC parameters |
| KMS and notification requirements | Determines key policies, alarms and audit integration | `customer KMS key; SNS topic ARN` | Security parameters |
| Cost ceiling | Sets safe vCPU and storage caps | `USD 250 per smoke test` | Deployment approval |

## 8. Approval request

Phase 1 is complete and the repository remains unchanged.

Approval is requested for the required Phase 2 changes listed in section 5, using:

- Native AWS Batch as the primary target.
- CloudFormation as the initial IaC system.
- EC2 Batch compute, not Fargate or Graviton.
- S3 work/results plus encrypted EFS for read-only reference databases.
- Three private ECR images referenced by digest.
- No Wave, Fusion, Seqera provisioning, AWS resource creation, image push, upload, pipeline submission, commit, or remote action.

A suitable approval is: “Approve the required Phase 2 plan with native AWS Batch and CloudFormation.”

> not sure if i should test the implementation with a subset of the pipeline; i have USD100 in credits

<details><summary>2 previous messages</summary>

> Yes—use the credits for a staged smoke test, but test a tiny end-to-end path rather than only one module. I’ll check the current AWS billing controls so the recommendation includes practical guardrails and doesn’t treat a budget alert as a hard spending cap.
>
> <details><summary>Searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `site:docs.aws.amazon.com cost management AWS Budgets alerts not stop resources official ...`
>
> </details>
>
> </details>
</details>

Yes. With USD 100, I’d reserve only about USD 25–40 for initial validation and keep the remainder for debugging and a second representative run.

Do a tiny end-to-end smoke test—not just a pipeline subset—because the main AWS risks occur at the boundaries between build, profile, and merge:

1. Infrastructure-only validation: no running compute.
2. Container pull/start test for all three images.
3. Tiny `--mode all` run:
   - 1 small genome
   - 1 paired-read sample with roughly 1,000–10,000 read pairs
   - KOfam stub
   - `--skip_checkm2`
   - On-Demand compute
   - `maxvCpus=8`
4. Repeat with the real KOfam database to validate shared-reference access and real annotation.
5. Only then test 2–3 samples, merge behavior, `-resume`, and one controlled task failure.

Suggested credit allocation:

| Stage | Stop threshold |
|---|---:|
| Infrastructure and container smoke test | USD 5 |
| Stubbed end-to-end run | USD 10 |
| Real KOfam end-to-end run | USD 15 |
| Resume/failure test | USD 10 |
| Reserve for debugging and representative testing | USD 60 |

Use On-Demand initially. Spot is better tested after scientific equivalence is established; otherwise interruptions complicate diagnosis.

Important safeguards:

- Keep Batch `minvCpus=0`.
- Start with `maxvCpus=8`, increasing to 16 only if a task cannot schedule.
- Stop the Nextflow driver when idle.
- Use short S3 work-object retention.
- Avoid NAT Gateway creation for the first test if VPC endpoints and pre-provisioned references suffice; an idle NAT gateway can consume credits continuously.
- Do not provision FSx.
- Keep EFS minimal and remove it after testing if it is no longer needed.
- Tag everything with a unique test run ID.
- Set budget alerts at USD 20, 35, 50, and 75.

AWS Batch itself has no additional service charge; you pay for EC2, EBS, S3, EFS, logs, and networking resources ([AWS Batch pricing](https://aws.amazon.com/batch/pricing/)). Budget alerts are delayed because AWS billing data updates at least daily, so they are not a real-time hard cap ([AWS Budgets guidance](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html)).

One correction to sequencing: there is no cloud implementation to test yet—Phase 1 was assessment only. If you approve Phase 2, I would implement the smoke-test fixture and conservative compute limits as part of it, with the first external AWS run still requiring separate approval.
