# SRA Backlog Replay SOP

**Purpose:** clear the ~7,000-sample submission gap under BioProject
**PRJNA989260**, one batch at a time, so progress is trackable across sessions.

**Scope:** this covers *choosing* a batch and *verifying* it. The mechanics of a
single submission are in [`sra-submission-sop.md`](sra-submission-sop.md) — read
that first if you have not run one before.

**Status as of 2026-08-01:** 2 batches done (126 samples), 9 identified and
ready in 2024 (~840 samples).

---

## The one-paragraph version

Pick the oldest batch that still has unpublished samples *and* has hand-curated
templates. Pre-flight it: how many are already published, how many will be
blacklisted for missing NWSS metadata, and whether any site IDs are undefined.
Submit with `-p -S -l`. Poll until `processed-ok`. Record the numbers. Move on.

---

## Progress log

Append a row here after every batch. This is the handoff record.

| date | batch | template | published | blacklisted | submitted | accessioned | remote folder |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-07-31 | `240423_Direct_227` | 82 | 15 | 4 | 63 | 63/63 | `PRJNA989260_240423_Direct_227_20260731-042440` |
| 2026-08-01 | `240606_Direct_236` | 75 | 8 | 4 | 63 | 63/63 | `PRJNA989260_240606_Direct_236_20260801-131609` |

Blacklisted so far, awaiting NWSS metadata:
`71230 72040 72043 72049 79497 79504 79510 79513`

---

## Step 1 — Pick the batch

### The queue (verified 2026-08-01, oldest first)

All nine have templates and fastqs on disk.

| batch | missing | would blacklist | in IDPH sheet |
|---|---:|---:|---:|
| `240829_Direct_248` | 76 | 0 | 57 |
| `240919_Direct_254_255_256` | 175 | 0 | 165 |
| `240925_Direct_257` | 90 | 0 | 86 |
| `241002_Direct_258` | 62 | 0 | 54 |
| `241009_Direct_259` | 81 | 2 | 71 |
| `241107_Direct_263_264_265` | 201 | 1 | 156 |
| `241114_Direct_266_267` | 72 | 0 | 19 |
| `241127_Direct_270_271` | 83 | 0 | 53 |

**Work oldest-first** so the log stays a clean frontier and it is obvious where
to resume.

### Recomputing the queue from scratch

If the list above is stale, rank batches by publish rate. A *broken* batch is
one whose rate is far below the ~63% median — those are the truncation-bug
casualties, where a handful of samples got through and the rest silently did
not. `240925_Direct_257` was 1/91; `240919` was 2/177.

```bash
# fresh NCBI truth (takes ~2 min, 13.7k+ rows)
bin/check-published-samples -r <any batch with a template> -o /tmp/pub.tsv --refresh
# the cache it writes is what everything else reads:
#   ~/.cache/anl-seq-service/ncbi_PRJNA989260_samples.tsv
```

Then per batch, compare the **template** (the authoritative candidate set)
against that cache. Do **not** use `reports/sra-audit-260714/` for this — it is
a frozen 2026-07-14 snapshot and its per-batch counts are wrong (see Trap 5).

### Batches with no `SRA/` directory

The 2026 tail (`260212_Direct_331` onward, 21 batches, ~1,200 samples) has fastqs
but **no templates**. Those are blocked on a human authoring the two `.tmpl.tsv`
files — never on tooling. Do not try to generate them; see Trap 6.

---

## Step 2 — Pre-flight

Four checks. All are read-only and take under a minute.

```bash
B=/nfs/seq-data/nextseq2k_output/nextseq2k_runs/<RUN>/<PARENT>/<BATCH>

# 1. template sample IDs (the candidate set)
cut -f1 "$B/SRA/"*[Bb]iosample.tmpl.tsv | tail -n +2 | sed 's/^\*//' \
  | grep -E '^[0-9]+$' | sort -u > /tmp/batch.txt
wc -l < /tmp/batch.txt

# 2. already published -> will be skipped by -S
bin/check-published-samples -r "$B" -o /tmp/pub.tsv --refresh   # reports N published / M missing

# 3. NWSS coverage -> anything absent gets BLACKLISTED, not submitted
cut -d, -f1 /incoming/SRA_COVID_Temp/*_NWSS_IDPH.csv \
            /incoming/SRA_COVID_Temp/*_NWSS_CDPH.csv | sort -u > /tmp/nwss.txt
comm -23 /tmp/batch.txt /tmp/nwss.txt          # -> the blacklist

# 4. site coverage -> undefined sites silently degrade metadata
awk -F'\t' 'NR==1{for(i=1;i<=NF;i++){g=$i;sub(/^\*/,"",g);
  if(g=="collection_site_id")c=i}next}{if(c&&$c!="")print $c}' \
  "$B/SRA/"*[Bb]iosample.tmpl.tsv | sort -u > /tmp/sites.txt
cut -f1 /incoming/SRA_COVID_Temp/SiteID.tsv | tail -n +2 | sort -u > /tmp/sdef.txt
comm -23 /tmp/sites.txt /tmp/sdef.txt          # -> should be empty
```

**Expected arithmetic:** `template − published − blacklisted = submitted`.
If that does not hold, stop and find out why before uploading.

### Optional: overlap with IDPH's missing-metadata spreadsheet

```bash
comm -12 /tmp/batch.txt /tmp/sheet_ids.txt | wc -l
```

`sheet_ids.txt` is the first column of `IL_Missing_Metadata_1.xlsx`, sorted
unique. Useful for reporting back to IDPH which of their flagged samples a given
submission clears. Their list matched our computed missing set **exactly** on
`240423_Direct_227` (67 of 67), so it is a good independent cross-check.

---

## Step 3 — Submit

```bash
source /nfs/seq-data/anl-seq-service/config/auth.sh
bin/sra-upload -r "$B" -p -S -l 2>&1 | tee run.log
```

- `-S` auto-skips already-published samples.
- **`-l` is currently mandatory** — the container image is stale (Trap 1).
- Target is `submit/Production` per `config/auth.sh`. Verify with
  `echo $NCBI_BASE_DIR` before you start.

Expect ~4–5 min for a ~13 GB batch at ~380 Mbit/s. Do not close the terminal
before the `SUBMISSION SUMMARY` block appears — it is the only guaranteed
evidence the upload finished.

### Verify before walking away

```bash
python3 -c "
import json; d=json.load(open('$B/SRA/submission/upload_receipt.json'))
print(d['status'], d['verify_failures'], d['submit_ready_written'])"
# want: TRIGGERED (submit.ready sent)  []  True
```

---

## Step 4 — Poll for accessions

```bash
mkdir -p reports/poll-<BATCH>
nohup bin/poll-ncbi-report \
  --folder submit/Production/<remote_folder_from_summary_block> \
  --save-dir reports/poll-<BATCH> > reports/poll-<BATCH>/poll.log 2>&1 &
```

Terminal status arrives in **13–15 minutes** in practice — much faster than the
"1–4 hours" the older SOP predicts. Both completed batches hit `processed-ok`
with `actions={'processed-ok': 126}` (63 BioSample + 63 SRA).

```bash
grep -E 'TERMINAL' reports/poll-<BATCH>/poll.log
awk -F'\t' 'NR>1 && $3!=""' reports/poll-<BATCH>/accessions.tsv | wc -l   # SRRs issued
grep -o 'error_code="[^"]*"' reports/poll-<BATCH>/report*.xml             # want: nothing
```

Then append a row to the progress log at the top of this document.

---

## Traps

Each of these cost real time. They are in the order you are likely to hit them.

### 1. The container image is stale — `-l` is mandatory

`wilke/anl-seq-service:latest` ships a **pre-NCBI-migration `SRA.py`** with
`--upload-url` / `--user` / `--password` (the CDC interface) and no
`--blacklist-out` or `--skip-samples`. Without `-l` the run dies at step 1:

```
SRA.py: error: unrecognized arguments: --blacklist-out ... --skip-samples ...
```

It fails *before* uploading, so it is loud rather than dangerous. Tracked as
issue #16. Rebuild with `cd Docker && ./build-anl-seq-service.sh`; note
`INFO: Using cached SIF image` means `-u` alone may not refresh Singularity's
cache.

### 2. `/incoming` is a different, non-durable filer

`/local/incoming/...` and `/incoming/...` look alike and are **different NFS
servers**. `/local` is the analysis filer (`sto-386-01`); `/incoming` is the
instrument landing zone (`10.140.134.34`).

The NWSS master lives **only** on the landing zone. When it went away on
2026-07-31, submission was blocked even though fastqs and templates were safe.

`sra-upload` now resolves the master in this order, first reachable wins:
`$NWSS_MASTER_DIR` → `/nfs/seq-data/SRA_COVID_Temp` (durable mirror) →
`/incoming/SRA_COVID_Temp` (landing zone, with a WARNING).

**The mirroring cron on mgrast-01 does not exist yet** (issue #17), so in
practice the landing zone is still the only source and every run warns. Adding
that one cron line is what makes submission independent of the volatile filer:

```cron
2 */3 * * * if [ ! -f /tmp/cron.nwss.running ] ; then touch /tmp/cron.nwss.running ; date ; time rsync -rtlP /incoming/SRA_COVID_Temp /nfs/seq-data/ ; rm /tmp/cron.nwss.running ; else echo Found lockfile for nwss ; fi
```

When that filer is down:

- **Do not** substitute the batch-local NWSS copies under `<batch>/SRA/`. They
  are point-in-time snapshots; a 2026-07-24 analysis found **90 of 92** samples
  they flag as "missing from NWSS" *do* have metadata in the cumulative master.
  Using them blacklists submittable samples.
- **Do not** run bare `df` or `ls /` — both enumerate all mountpoints and hang.
- A hard NFS mount makes `[ -d ]` **block**, not return false, so scripts wedge
  rather than erroring. `timeout` only partly helps: uninterruptible sleep
  defers SIGTERM and SIGKILL alike.
- After it returns, check mgrast-01 for a stale `/tmp/cron.*.running` lockfile.
  If the rsync was killed mid-flight, **intake stays halted even after the mount
  recovers**, and nothing alerts (issue #11).

### 3. Do not walk the run tree to find things

285 run folders over NFS takes minutes and will blow past command timeouts. You
almost always already know the batch path. Read the template directly and use
`comm`:

```bash
cut -f1 "$B/SRA/"*[Bb]iosample.tmpl.tsv | tail -n +2 | sed 's/^\*//' | sort -u
```

Two `cut`s and a `comm` answer in under a second what a `find` answers in ten
minutes.

### 4. A batch label is not an identifier

Sixteen `Direct_NNN` labels are **reused across dates** — `260717_Direct_353`
and `260725_Direct_353` both exist. Always key on the full path.

Covid analysis dirs also drift from their batch: only 160 of 373 name-match.
`covid/runs/260717_Direct_353` actually came from batch `260717_Direct_355` —
provable because `assembly.sh` writes `${id}.reads` from the directory name *at
analysis time*, so a mismatch is a rename detector.

### 5. The frozen audit's numbers are wrong

`reports/sra-audit-260714/` reports **16,070 missing**. That counts
`(directory, sample)` **rows**, not samples:

| | |
|---|---|
| rows | 32,211 |
| **distinct sample IDs** | **15,630** |
| rows from reanalysis dirs (`.re20240317` etc.) | 10,790 → only 149 IDs unique to them |
| controls/pools/artifacts (never submittable) | 80 |
| **true missing** | **~7,114** |
| NCBI records with no local match | 5,265 |

Recompute with `seqtrack/reconcile/verify_backlog.py`, which attributes every
difference to a named rule. Also note **one batch can appear as several rows** —
`240423_Direct_227` showed as `227` (17 samples) *and* `227-first-round` (97)
because the covid side has four analysis dirs; there is only **one** batch with
**one** 82-row template.

### 6. Templates are hand-curated — never generate them

Standing directive. The two `.tmpl.tsv` files are authored by a human in Excel.
The submission set is `template ∩ latest master NWSS − already published`.
Samples absent from NWSS are **blacklisted, not submitted with defaults** — that
policy was set on 2026-07-27 and must not be reverted.

Assisted *validation* (the Step 2 pre-flight) is the right kind of help.
Generation is not.

### 7. NCBI's eutils index lags accession issue

After a successful submission, `check-published-samples --refresh` will not show
the new samples immediately — accessions exist in `accessions.tsv` well before
runinfo indexes them. The 58 samples from `240612_Direct_237` took days.

Consequence: the `-S` skip list may under-report for a batch submitted very
recently. It does not matter when working oldest-first through disjoint batches,
but do not rely on eutils to confirm a submission you just made — use the poll
output.

### 8. One malformed NWSS row is losing data

Every run reports:

```
ERROR Line 124732: 53 columns > 50 header columns; extra fields dropped
```

This is a pre-existing defect in the merged IDPH/CDPH sheet, not caused by the
submission. It is the only ERROR in an otherwise clean run — do not let it mask
a real one.

---

## Known-good reference numbers

For sanity-checking a future run:

| | `240423_Direct_227` | `240606_Direct_236` |
|---|---|---|
| template rows | 82 | 75 |
| published (skipped) | 15 | 8 |
| blacklisted | 4 | 4 |
| **submitted** | **63** | **63** |
| fastqs uploaded | 126 + xml | 126 + xml |
| upload | 12.69 GB / 4.4 min | 13.17 GB / 4.6 min |
| bandwidth | 381 Mbit/s | 382 Mbit/s |
| terminal status | `processed-ok` 13.2 min | `processed-ok` 14.3 min |
| accessions | 63/63 SAMN + SRR | 63/63 SAMN + SRR |
| errors | 0 | 0 |

A batch of ~75–85 template rows should land ~63 samples, ~13 GB, ~4.5 min
upload, ~14 min to terminal. Deviations are worth investigating.

## Related

- [`sra-submission-sop.md`](sra-submission-sop.md) — single-submission mechanics
- `reports/work-260730.seqtrack.md` — findings and defect inventory
- Issues #16 (stale container), #17 (NWSS mirroring), #11 (mirror-cron
  observability), #12 (undefined site IDs), PR #18 (merged)

