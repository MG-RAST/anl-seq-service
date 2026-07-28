# SRA Submission SOP — ANL wastewater surveillance

**Applies to:** batches destined for BioProject **PRJNA989260** (IWSS wastewater surveillance) via NCBI's submission FTP.
**Replaces:** legacy CDC `eft.cdc.gov` upload (preserved at `/local/incoming/covid/scripts/sra-upload.cdc-legacy`, mode 600).

---

## Steps

### 1. Download NWSS files

Pull the IDPH and CDPH NWSS submission sheets for this batch. Place them in the batch's `SRA/` subdirectory.

### 2. Reformat NWSS dates

Ensure `sample_collect_date` columns use `mm/dd/yyyy` (the pipeline reformats to `yyyy-mm-dd` automatically, but only from `mm/dd/yyyy` — other formats will emit `ERROR Date format not recognized`).

### 3. Stage batch templates in the batch's `SRA/` folder

Only two hand-curated files are needed per batch:

| File | Purpose |
|---|---|
| `*.run.tmpl.tsv` | run template — one row per sample you intend to submit |
| `*.biosample.tmpl.tsv` (or `.Biosample.tmpl.tsv`) | biosample template — same sample list |

**NWSS reference files are NOT copied per batch anymore** (as of 2026-07-27). `SiteID.tsv`, `NWSS_IDPH.csv`, and `NWSS_CDPH.csv` are read from the master dir `/incoming/SRA_COVID_Temp/` (override via `NWSS_MASTER_DIR` env var). The wrapper picks the latest-by-mtime `MM_DD_YYYY_NWSS_IDPH.csv` and `_CDPH.csv` automatically. Batch-local copies, if present, are ignored.

Rationale: NWSS sheets are cumulative longitudinal records. A sample may be sequenced in one batch and reported to NWSS only later — using the master ensures we always check against the newest data.

**Behavior for template samples that aren't in the master NWSS** (any of them):
they get written to a **blacklist file** and are **NOT uploaded to NCBI**. This is by design (as of 2026-07-27) — samples without real metadata should not ship with `not collected` defaults. Sarah / the NWSS side can review the blacklist and either update NWSS or drop them from the template. Default blacklist path: `./blacklist.<batch>.tsv` in your CWD (override with `-B <path>`).

### 4. Rename `.tmpl` → `.tsv`

The pipeline expects `*.tmpl.tsv` (double-suffixed). If the file is `.templ`, rename to `.tmpl.tsv`.

### 5. Source auth

```bash
source /nfs/seq-data/anl-seq-service/config/auth.sh
```

Sets **`NCBI_CONTACT`**, **`NCBI_CONTACT_FIRST`**, **`NCBI_CONTACT_LAST`**, **`NCBI_USER`**, **`NCBI_PASSWORD`**, **`NCBI_BASE_DIR`**.

Verify:
```bash
echo $NCBI_USER   # should print 'Illinois_WBE' for the center account
```

### 5a. (Optional but recommended for backlog replay) Check which samples are already published

Only relevant when re-processing a run that may have been partially submitted before (e.g., every batch we run for the CDC-era truncation-bug cleanup).

```bash
check-published-samples -r <run_folder>
```

This fetches NCBI's current runinfo for PRJNA989260 (24-hour cache under `~/.cache/anl-seq-service/`) and produces `<run_folder>/SRA/published.tsv` with per-sample status. The INFO summary reports `N published / M missing / T total` — review before triggering the upload.

Options:
- `--refresh` — force fresh eutils fetch even if the cache is <24h old
- `-b <bioproject>` — target a different BioProject (default PRJNA989260)
- `-o <out.tsv>` — override the output path

The output TSV columns: `sample_id  status  biosample_accession  run_accession  load_date`. `sra-upload` accepts this file directly via `-s` (see step 6) — no format conversion needed.

### 6. Run

```bash
# Baseline (submit everything in the run):
/local/incoming/covid/scripts/sra-upload \
    -r /local/incoming/nextseq2k_output/nextseq2k_runs/<DIR> \
    -p 2>&1 | tee run.log

# With explicit skip list from step 5a:
/local/incoming/covid/scripts/sra-upload \
    -r /local/incoming/nextseq2k_output/nextseq2k_runs/<DIR> \
    -p -s <run_folder>/SRA/published.tsv 2>&1 | tee run.log

# One-shot: auto-check + skip published + submit:
/local/incoming/covid/scripts/sra-upload \
    -r /local/incoming/nextseq2k_output/nextseq2k_runs/<DIR> \
    -p -S 2>&1 | tee run.log
```

**Flags:**
- `-r` — batch directory (must exist; the wrapper hints the correct path if wrong)
- `-p` — push package to NCBI's submission FTP
- `-T` — (optional) upload everything **except** `submit.ready` so nothing triggers on NCBI's side. Use this for the first real submission after any change (regenerate templates, new center account, etc.). Verify on NCBI, then re-run without `-T`.
- `-s <file>` — skip sample IDs listed in `<file>` (TSV from `check-published-samples` or plain list). Use when you've explicitly reviewed which samples to exclude.
- `-S` — auto-run `check-published-samples` before generating TSVs and skip anything currently public under PRJNA989260. Convenience wrapper around `-s`.
- `-B <file>` — override blacklist output path (default `./blacklist.<batch>.tsv`). Blacklist lists template samples that are absent from master NWSS.
- `-l` — force local Python (skip container). Useful if the container image is stale.
- `-d` — dry-run: prints the commands that would run without executing.

`-s` and `-S` are mutually exclusive. The end-of-run summary reports `Filtered: N sample(s) skipped via <file>` when either is active.

**Note:** `/local/incoming/covid/scripts/sra-upload` is a symlink to `/nfs/seq-data/anl-seq-service/bin/sra-upload`.

### 7. Read the ending

The wrapper prints three artifacts at the end of a real run:

1. A **WARNING/ERROR aggregation banner** listing every warning/error across all three phases (TSV generation, XML generation, upload). Even if warnings scroll past during upload, they appear again here.
2. A **SUBMISSION SUMMARY** block from `ncbi_upload.py`:
   ```
   ================================================================
   SUBMISSION SUMMARY
   ================================================================
   Started (UTC):   2026-07-17T14:12:03+00:00
   Duration:        342.1 s (5.7 min)
   Data:            18.66 GB, 227 files
   Avg bandwidth:   436.2 Mbit/s
   Remote folder:   uploads/wilke_anl.gov_6Kglbk1A/PRJNA989260_240612_Direct_237_20260717-141203
   Status:          TRIGGERED (submit.ready sent)
   XML SHA256:      3f0e9a...
   ================================================================
   ```
3. An **`upload_receipt.json`** written next to `submission.xml` (`<run>/SRA/submission/upload_receipt.json`) — audit trail for later "what did we submit when" queries.

Any of these three has clear success/failure signals. **Do not close the terminal until you've seen the summary block** — that's the only guaranteed evidence the upload completed.

### 7a. (Optional) Poll for terminal status + capture accessions

After `submit.ready` is written (Production only — Test never reaches
`processed-ok` because Test env has no BioProject data), run:

```bash
/nfs/seq-data/anl-seq-service/bin/poll-ncbi-report \
    --folder $NCBI_BASE_DIR/<remote_folder_from_summary_block> \
    --save-dir ./poll-<batch>
```

The tool watches the folder over SFTP, always re-fetches `report.xml` /
`report.N.xml` on every tick (NCBI overwrites the same filename with
newer status — an earlier ad-hoc poll cached the initial version and
silently missed the terminal state; that's fixed here), and on
`processed-ok` writes `accessions.tsv` with `sample_name → SAMN → SRR`.

Typical timing: BioSamples get `SAMN` accessions in ~5 min. SRA runs
often take 1–4 hours for `SRR` accessions. `--max-hours 6` by default.

### 8. If it failed partway through

Do NOT just re-run without checking the NCBI side. Each re-run creates a NEW timestamped folder; orphan partial folders accumulate.

```bash
# List existing folders under your account:
python3 -c "
import ftplib, os
ftp = ftplib.FTP('ftp-private.ncbi.nlm.nih.gov')
ftp.login(os.environ['NCBI_USER'], os.environ['NCBI_PASSWORD'])
ftp.cwd(os.environ['NCBI_BASE_DIR'])
for e in ftp.nlst(): print(e)
ftp.quit()
"

# Delete a stale folder (adapt the path):
python3 -c "
import ftplib, os
ftp = ftplib.FTP('ftp-private.ncbi.nlm.nih.gov')
ftp.login(os.environ['NCBI_USER'], os.environ['NCBI_PASSWORD'])
folder = 'uploads/wilke_anl.gov_6Kglbk1A/<STALE_FOLDER>'
ftp.cwd(folder)
for f in ftp.nlst(): ftp.delete(f)
ftp.cwd('..')
ftp.rmd('<STALE_FOLDER>')
ftp.quit()
"
```

Once the stale folder is gone, re-run step 6.

The wrapper also emits a WARNING at start of upload if it finds a prior folder for the same run — pay attention to it.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR: NCBI_CONTACT is not set` | Step 5 skipped | `source /nfs/seq-data/anl-seq-service/config/auth.sh` |
| `ERROR: Run folder not found: /incoming/…` | Missing `/local/` prefix in step 6 | Use `-r /local/incoming/nextseq2k_output/nextseq2k_runs/...` |
| `WARNING Missing site IDs: ['S0183', ...]` | Site newly added upstream, not yet in `SiteID.tsv` | Add the missing site row(s) to `SiteID.tsv`. Pipeline still completes; those samples get `not collected` defaults for `collected_by`/`ww_population` |
| `ERROR SIZE mismatch on <file>` | Upload corruption | Wrapper refuses to write `submit.ready`. Delete the folder on NCBI, re-run |
| `ERROR Date format not recognized: <val>` | Date is neither `yyyy-mm-dd` nor `mm/dd/yyyy` | Fix the NWSS CSV date column and re-run |
| `WARNING: IDPH (54 cols) and CDPH (53 cols) headers differ` | IDPH-only `days_in_sewer` column | Non-fatal; wrapper uses the wider header + pads |

## Timing baselines (Illinois_WBE center account, verified 2026-07-22 / 2026-07-27)

Measured end-to-end for the 240612 batch (71 samples, 131–143 files, ~11 GB):

| Phase | Duration | Notes |
|---|---|---|
| Upload — plain FTP | 126–136 s | 679 Mbit/s average |
| Upload — SFTP (default as of 2026-07-27) | ~200 s | 440 Mbit/s average — encryption overhead |
| NCBI ingest → first `report.xml` | ~3–4 min | Test folder |
| NCBI processing → accessions (Production) | ~15–30 min | based on typical NCBI SLA; not yet measured |

**Transport:** SFTP is the default. Set `NCBI_TRANSPORT=ftp` (or pass `--transport ftp` to `ncbi_upload.py`) to fall back to plain FTP if paramiko isn't available in the container image. Endpoints: `sftp-private.ncbi.nlm.nih.gov:22` and `ftp-private.ncbi.nlm.nih.gov:21`.

## Test-folder gotcha

**`/submit/Test/` does NOT have access to production BioProject records.** A Test submission referencing PRJNA989260 will get through the upload cleanly, pass schema validation, then fail during processing with:

```
error_code="63" severity="error-stop"
BioProject accession PRJNA989260 does not exist. Please provide a valid BioProject accession.
```

This is **expected Test-folder behavior**, not a real problem with your account or XML. It means the upload + schema validation half of the pipeline works.

Options for confirming end-to-end:
1. **Trust the test.** Upload validated, schema validated. Submit next batch straight to `/submit/Production/`.
2. **Ask NCBI helpdesk** for a Test-only BioProject accession to reference for future Test runs.

Real accessions (`SAMN########`, `SRR########`) only get issued on `/submit/Production/`.

## Post-migration reference

- Old CDC-flavored script preserved at `/local/incoming/covid/scripts/sra-upload.cdc-legacy` (chmod 600). Do not use; it targets `eft.cdc.gov` which is no longer the canonical endpoint.
- Git tag `v1.0-cdc-nwss` on the `anl-seq-service` repo is the last CDC-era code state.
- Current CDC-to-NCBI transition summary: `reports/work-260714.sra-submission-audit.md`.
- First Test submission (SUB1137596) evidence: `reports/sra-audit-260714/first-test-submission-SUB1137596/`.
