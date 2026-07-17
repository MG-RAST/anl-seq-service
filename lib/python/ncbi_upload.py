#!/usr/bin/env python3
"""Upload a generated submission package to NCBI's submission FTP.

Reads submission.xml to discover the fastq filenames and BioProject, then
puts everything in a fresh folder under the account base dir on
ftp-private.ncbi.nlm.nih.gov, and writes the empty `submit.ready` trigger
file. Exits after upload (no report.xml polling).
"""

import argparse
import ftplib
import io
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_HOST = "ftp-private.ncbi.nlm.nih.gov"
DEFAULT_PORT = 21
SUBMIT_READY_NAME = "submit.ready"


def parse_submission(xml_path):
    """Return (bioproject_accession, [fastq_filenames])."""
    root = ET.parse(xml_path).getroot()

    bioproject = ""
    for prim in root.iter("PrimaryId"):
        if prim.attrib.get("db") == "BioProject" and prim.text:
            bioproject = prim.text.strip()
            break

    fastqs = []
    seen = set()
    for f in root.iter("File"):
        fp = f.attrib.get("file_path", "").strip()
        if fp and fp not in seen:
            seen.add(fp)
            fastqs.append(fp)

    return bioproject, fastqs


def make_folder_name(bioproject, run_basename):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    parts = [p for p in (bioproject, run_basename) if p]
    parts.append(ts)
    return "_".join(parts)


def connect(host, port, user, password):
    logger.info("Connecting to %s:%d as %s", host, port, user)
    ftp = ftplib.FTP()
    ftp.connect(host, port, timeout=60)
    ftp.login(user, password)
    return ftp


def mkdir_and_cd(ftp, base_dir, folder_name):
    ftp.cwd(base_dir)
    try:
        ftp.mkd(folder_name)
    except ftplib.error_perm as e:
        # 550 typically means "already exists" or "permission denied"
        logger.error("Failed to create %s under %s: %s", folder_name, base_dir, e)
        raise
    ftp.cwd(folder_name)
    logger.info("Created and entered %s/%s", base_dir.rstrip("/"), folder_name)


def upload_file(ftp, local_path, remote_name=None):
    remote_name = remote_name or os.path.basename(local_path)
    size = os.path.getsize(local_path)
    t0 = time.monotonic()
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_name}", f)
    dt = time.monotonic() - t0
    mbps = (size * 8 / 1e6) / dt if dt > 0 else 0.0
    logger.info("Uploaded %s (%.1f MB in %.1fs, %.1f Mbit/s)",
                remote_name, size / 1e6, dt, mbps)
    return size, dt


def upload_empty(ftp, remote_name):
    logger.info("Uploading flag file %s", remote_name)
    ftp.storbinary(f"STOR {remote_name}", io.BytesIO(b""))


def cli():
    p = argparse.ArgumentParser(
        description="Upload submission package to NCBI submission FTP")
    p.add_argument("--submission-xml", required=True,
                   help="Path to submission.xml (also used to discover fastq files)")
    p.add_argument("--sequence-dir", required=True,
                   help="Directory containing the fastq files referenced in submission.xml")
    p.add_argument("--run-basename", default=None,
                   help="Base name used in the remote folder (default: basename of --sequence-dir)")
    p.add_argument("--user", default=os.environ.get("NCBI_USER"),
                   help="FTP username (default: $NCBI_USER)")
    p.add_argument("--password", default=os.environ.get("NCBI_PASSWORD"),
                   help="FTP password (default: $NCBI_PASSWORD)")
    p.add_argument("--base-dir", default=os.environ.get("NCBI_BASE_DIR"),
                   help="Account folder on the FTP host (default: $NCBI_BASE_DIR)")
    p.add_argument("--host", default=os.environ.get("NCBI_HOST", DEFAULT_HOST),
                   help=f"FTP host (default: $NCBI_HOST or {DEFAULT_HOST})")
    p.add_argument("--port", type=int, default=int(os.environ.get("NCBI_PORT", DEFAULT_PORT)),
                   help=f"FTP port (default: $NCBI_PORT or {DEFAULT_PORT})")
    p.add_argument("--dry-run", action="store_true",
                   help="List what would be uploaded, do not connect")
    p.add_argument("--no-trigger", action="store_true",
                   help="Upload everything except submit.ready (NCBI pipeline will not pick up). "
                        "Use to verify the upload before triggering submission.")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = p.parse_args()

    logging.basicConfig(format="%(levelname)s %(asctime)s\t%(message)s",
                        level=args.log_level)

    for name in ("user", "password", "base_dir"):
        if not getattr(args, name):
            logger.error("Missing required arg/env: --%s or $NCBI_%s",
                         name.replace("_", "-"), name.upper())
            sys.exit(2)

    if not os.path.isfile(args.submission_xml):
        logger.error("submission.xml not found: %s", args.submission_xml)
        sys.exit(1)
    if not os.path.isdir(args.sequence_dir):
        logger.error("sequence dir not found: %s", args.sequence_dir)
        sys.exit(1)

    bioproject, fastqs = parse_submission(args.submission_xml)
    if not fastqs:
        logger.error("No <File file_path=...> entries found in %s", args.submission_xml)
        sys.exit(1)
    logger.info("BioProject: %s, fastqs to upload: %d", bioproject or "(none)", len(fastqs))

    # Verify all fastqs exist locally before connecting
    missing = []
    for fq in fastqs:
        if not os.path.isfile(os.path.join(args.sequence_dir, fq)):
            missing.append(fq)
    if missing:
        logger.error("Missing %d fastq(s) under %s: %s",
                     len(missing), args.sequence_dir, missing[:5])
        sys.exit(1)

    run_basename = args.run_basename or os.path.basename(args.sequence_dir.rstrip("/"))
    folder_name = make_folder_name(bioproject, run_basename)
    logger.info("Target folder: %s/%s", args.base_dir.rstrip("/"), folder_name)

    if args.dry_run:
        logger.info("Dry run: would upload %d fastqs + submission.xml + %s",
                    len(fastqs), SUBMIT_READY_NAME)
        for fq in fastqs:
            logger.debug("  %s", fq)
        return

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    wall_t0 = time.monotonic()
    total_bytes = 0

    ftp = connect(args.host, args.port, args.user, args.password)
    try:
        mkdir_and_cd(ftp, args.base_dir, folder_name)
        for fq in fastqs:
            sz, _ = upload_file(ftp, os.path.join(args.sequence_dir, fq), remote_name=fq)
            total_bytes += sz
        sz, _ = upload_file(ftp, args.submission_xml, remote_name="submission.xml")
        total_bytes += sz
        if args.no_trigger:
            logger.warning("Skipping %s (--no-trigger). Submission NOT triggered. "
                           "Upload it manually to start NCBI's pipeline, or delete the folder.",
                           SUBMIT_READY_NAME)
        else:
            upload_empty(ftp, SUBMIT_READY_NAME)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()

    wall_dt = time.monotonic() - wall_t0
    avg_mbps = (total_bytes * 8 / 1e6) / wall_dt if wall_dt > 0 else 0.0
    suffix = " (not triggered)" if args.no_trigger else ""
    logger.info("Upload complete%s: %s/%s",
                suffix, args.base_dir.rstrip("/"), folder_name)
    logger.info("Timing: started %s, total %.1fs, %.2f GB, average %.1f Mbit/s",
                started_at, wall_dt, total_bytes / 1e9, avg_mbps)


if __name__ == "__main__":
    cli()
