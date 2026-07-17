# SRA Submission SOP — ANL wastewater surveillance

**Applies to:** batches destined for BioProject **PRJNA989260** (IWSS wastewater surveillance) via NCBI's submission FTP.
**Replaces:** legacy CDC `eft.cdc.gov` upload (preserved at `/local/incoming/covid/scripts/sra-upload.cdc-legacy`, mode 600).

---

## Steps

### 1. Download NWSS files

Pull the IDPH and CDPH NWSS submission sheets for this batch. Place them in the batch's `SRA/` subdirectory.

### 2. Reformat NWSS dates

Ensure `sample_collect_date` columns use `mm/dd/yyyy` (the pipeline reformats to `yyyy-mm-dd` automatically, but only from `mm/dd/yyyy` — other formats will emit `ERROR Date format not recognized`).

### 3. Move / stage files in the batch's `SRA/` folder

The pipeline discovers these by suffix under `<run_folder>/SRA/`:

| File | Purpose |
|---|---|
| `*IDPH.csv` | Illinois NWSS samples |
| `*CDPH.csv` | Chicago NWSS samples |
| `*SiteID*.tsv` | site→collected_by/ww_population lookup |
| `*.run.tmpl.tsv` | run template |
| `*.biosample.tmpl.tsv` (or `.Biosample.tmpl.tsv`) | biosample template |

`ord.samples.csv` is optional (kept for provenance).

**Before running:** confirm `SiteID.tsv` includes every site referenced in the biosample template. Missing sites no longer crash the pipeline (fixed 2026-07-16), but the samples get `collected_by=not collected` / `ww_population=not collected` in NCBI. See the WARNINGS block at the end of the run.

### 4. Rename `.tmpl` → `.tsv`

The pipeline expects `*.tmpl.tsv` (double-suffixed). If the file is `.templ`, rename to `.tmpl.tsv`.

### 5. Source auth

```bash
source /nfs/seq-data/anl-seq-service/config/auth.sh
```

Sets **`NCBI_CONTACT`**, **`NCBI_CONTACT_FIRST`**, **`NCBI_CONTACT_LAST`**, **`NCBI_USER`**, **`NCBI_PASSWORD`**, **`NCBI_BASE_DIR`**.

Verify:
```bash
echo $NCBI_USER   # should print 'subftp' (or the assigned Center ID user)
```

### 6. Run

```bash
/local/incoming/covid/scripts/sra-upload \
    -r /local/incoming/nextseq2k_output/nextseq2k_runs/<DIR> \
    -p 2>&1 | tee run.log
```

**Flags:**
- `-r` — batch directory (must exist; the wrapper hints the correct path if wrong)
- `-p` — push package to NCBI's submission FTP
- `-T` — (optional) upload everything **except** `submit.ready` so nothing triggers on NCBI's side. Use this for the first real submission after any change (regenerate templates, new center account, etc.). Verify on NCBI, then re-run without `-T`.
- `-l` — force local Python (skip container). Useful if the container image is stale.
- `-d` — dry-run: prints the commands that would run without executing.

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

## Post-migration reference

- Old CDC-flavored script preserved at `/local/incoming/covid/scripts/sra-upload.cdc-legacy` (chmod 600). Do not use; it targets `eft.cdc.gov` which is no longer the canonical endpoint.
- Git tag `v1.0-cdc-nwss` on the `anl-seq-service` repo is the last CDC-era code state.
- Current CDC-to-NCBI transition summary: `reports/work-260714.sra-submission-audit.md`.
