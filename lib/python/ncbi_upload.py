#!/usr/bin/env python3
"""Upload a generated submission package to NCBI's submission FTP or SFTP.

Reads submission.xml to discover the fastq filenames and BioProject, then
puts everything in a fresh folder under the account base dir on the chosen
transport (default SFTP), and writes the empty `submit.ready` trigger file.
Exits after upload (no report.xml polling).
"""

import argparse
import ftplib
import hashlib
import io
import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

try:
    import paramiko
except ImportError:  # pragma: no cover — paramiko is optional if only FTP used
    paramiko = None

logger = logging.getLogger(__name__)

DEFAULT_TRANSPORT = "sftp"  # sftp is encrypted; FTP kept for legacy use
DEFAULT_HOSTS = {
    "sftp": "sftp-private.ncbi.nlm.nih.gov",
    "ftp":  "ftp-private.ncbi.nlm.nih.gov",
}
DEFAULT_PORTS = {"sftp": 22, "ftp": 21}
SUBMIT_READY_NAME = "submit.ready"


# ---------------------------------------------------------------- transports

class SFTPTransport:
    """Encrypted SSH/SFTP transport via paramiko."""

    def __init__(self, host, port, user, password):
        if paramiko is None:
            raise RuntimeError(
                "paramiko is not installed; cannot use SFTP. "
                "Install with 'pip install paramiko' or pass --transport ftp."
            )
        self._client = paramiko.SSHClient()
        # TOFU: accept-on-first-use. TODO: pin host key file in a follow-up.
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            host, port=port, username=user, password=password,
            timeout=60, allow_agent=False, look_for_keys=False,
        )
        self._sftp = self._client.open_sftp()
        hk = self._client.get_transport().get_remote_server_key()
        self.host_key_desc = f"{hk.get_name()} sha256={hk.get_fingerprint().hex()}"

    def close(self):
        try:
            self._sftp.close()
        except Exception:
            pass
        try:
            self._client.close()
        except Exception:
            pass

    def chdir(self, path):     self._sftp.chdir(path)
    def getcwd(self):          return self._sftp.getcwd()
    def listdir(self):         return self._sftp.listdir()
    def mkdir(self, name):     self._sftp.mkdir(name)

    def put_file(self, local_path, remote_name):
        self._sftp.put(local_path, remote_name)

    def put_empty(self, remote_name):
        with self._sftp.file(remote_name, "wb") as f:
            f.write(b"")

    def size(self, remote_name):
        return self._sftp.stat(remote_name).st_size


class FTPTransport:
    """Legacy cleartext FTP transport via ftplib (for backward compat)."""

    def __init__(self, host, port, user, password):
        self._ftp = ftplib.FTP()
        self._ftp.connect(host, port, timeout=60)
        self._ftp.login(user, password)
        self.host_key_desc = "n/a (plaintext FTP)"

    def close(self):
        try:
            self._ftp.quit()
        except Exception:
            try: self._ftp.close()
            except Exception: pass

    def chdir(self, path):     self._ftp.cwd(path)
    def getcwd(self):          return self._ftp.pwd()
    def listdir(self):
        try:
            return self._ftp.nlst()
        except ftplib.error_perm:
            return []
    def mkdir(self, name):
        try:
            self._ftp.mkd(name)
        except ftplib.error_perm as e:
            raise OSError(str(e))

    def put_file(self, local_path, remote_name):
        with open(local_path, "rb") as f:
            self._ftp.storbinary(f"STOR {remote_name}", f)

    def put_empty(self, remote_name):
        self._ftp.storbinary(f"STOR {remote_name}", io.BytesIO(b""))

    def size(self, remote_name):
        try:
            return self._ftp.size(remote_name)
        except ftplib.error_perm:
            return None


def _open_transport(transport, host, port, user, password):
    if transport == "sftp":
        return SFTPTransport(host, port, user, password)
    if transport == "ftp":
        return FTPTransport(host, port, user, password)
    raise ValueError(f"Unknown transport {transport!r}")


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


def connect(transport, host, port, user, password):
    logger.info("Connecting %s to %s:%d as %s", transport.upper(), host, port, user)
    conn = _open_transport(transport, host, port, user, password)
    logger.info("Connected. Host key: %s", conn.host_key_desc)
    return conn


def mkdir_and_cd(conn, base_dir, folder_name, run_basename):
    """Create the timestamped upload folder. If prior folders for the same
    run are present under base_dir, warn about them so operators can decide
    whether to leave, delete, or investigate.
    """
    conn.chdir(base_dir)
    try:
        existing = conn.listdir()
    except Exception:
        existing = []
    prior = [d for d in existing
             if d != folder_name and run_basename and run_basename in d]
    if prior:
        logger.warning("Prior upload folder(s) exist for %s: %s. "
                       "New folder will still be created (fresh timestamp); "
                       "clean up the old ones on NCBI's side if they are stale.",
                       run_basename, prior)
    try:
        conn.mkdir(folder_name)
    except Exception as e:
        logger.error("Failed to create %s under %s: %s", folder_name, base_dir, e)
        raise
    conn.chdir(folder_name)
    logger.info("Created and entered %s/%s", base_dir.rstrip("/"), folder_name)


def upload_file(conn, local_path, remote_name=None, progress=""):
    """Upload one file. Verifies remote size matches local afterwards.

    Returns (size, duration_seconds, verified: bool).
    """
    remote_name = remote_name or os.path.basename(local_path)
    size = os.path.getsize(local_path)
    t0 = time.monotonic()
    conn.put_file(local_path, remote_name)
    dt = time.monotonic() - t0
    mbps = (size * 8 / 1e6) / dt if dt > 0 else 0.0

    # Post-upload integrity: server-reported size must equal local size.
    verified = True
    try:
        remote_size = conn.size(remote_name)
        if remote_size is not None and remote_size != size:
            logger.error("SIZE mismatch on %s: local %d, remote %d — "
                         "upload corrupted, folder should be discarded.",
                         remote_name, size, remote_size)
            verified = False
    except Exception as e:
        logger.debug("Could not verify size for %s: %s", remote_name, e)

    verify_tag = "" if verified else " [SIZE MISMATCH!]"
    logger.info("%sUploaded %s (%.1f MB in %.1fs, %.1f Mbit/s)%s",
                progress, remote_name, size / 1e6, dt, mbps, verify_tag)
    return size, dt, verified


def upload_empty(conn, remote_name):
    logger.info("Uploading flag file %s", remote_name)
    conn.put_empty(remote_name)


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
                   help="Account folder on the transport host (default: $NCBI_BASE_DIR)")
    p.add_argument("--transport",
                   default=os.environ.get("NCBI_TRANSPORT", DEFAULT_TRANSPORT),
                   choices=["sftp", "ftp"],
                   help=f"Transport protocol (default: $NCBI_TRANSPORT or {DEFAULT_TRANSPORT}). "
                        f"sftp = encrypted, ftp = cleartext legacy.")
    p.add_argument("--host", default=os.environ.get("NCBI_HOST"),
                   help="Host (default: $NCBI_HOST, or sftp-private.ncbi.nlm.nih.gov / "
                        "ftp-private.ncbi.nlm.nih.gov depending on --transport)")
    p.add_argument("--port", type=int,
                   default=int(os.environ["NCBI_PORT"]) if os.environ.get("NCBI_PORT") else None,
                   help="Port (default: $NCBI_PORT, or 22 for sftp / 21 for ftp)")
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

    # Fill in transport-specific host/port defaults after arg parsing so the
    # --transport choice controls the fallback endpoint.
    if not args.host:
        args.host = DEFAULT_HOSTS[args.transport]
    if not args.port:
        args.port = DEFAULT_PORTS[args.transport]

    if args.transport == "sftp" and paramiko is None:
        logger.error("--transport sftp requires paramiko. Install it "
                     "(pip install paramiko) or pass --transport ftp.")
        sys.exit(2)

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
    n_total = len(fastqs) + 1  # + submission.xml
    verify_failures = []

    conn = connect(args.transport, args.host, args.port, args.user, args.password)
    try:
        mkdir_and_cd(conn, args.base_dir, folder_name, run_basename)
        for i, fq in enumerate(fastqs, 1):
            sz, _, ok = upload_file(
                conn, os.path.join(args.sequence_dir, fq),
                remote_name=fq,
                progress=f"[{i}/{n_total}] ",
            )
            total_bytes += sz
            if not ok:
                verify_failures.append(fq)
        sz, _, ok = upload_file(
            conn, args.submission_xml, remote_name="submission.xml",
            progress=f"[{n_total}/{n_total}] ",
        )
        total_bytes += sz
        if not ok:
            verify_failures.append("submission.xml")

        if verify_failures:
            logger.error("REFUSING to write submit.ready — %d file(s) failed "
                         "SIZE verification: %s. Investigate and re-upload "
                         "before triggering.",
                         len(verify_failures), verify_failures[:5])
        elif args.no_trigger:
            logger.warning("Skipping %s (--no-trigger). Submission NOT triggered. "
                           "Upload it manually to start NCBI's pipeline, or delete "
                           "the folder.", SUBMIT_READY_NAME)
        else:
            upload_empty(conn, SUBMIT_READY_NAME)
    finally:
        conn.close()

    wall_dt = time.monotonic() - wall_t0
    avg_mbps = (total_bytes * 8 / 1e6) / wall_dt if wall_dt > 0 else 0.0
    if verify_failures:
        status = f"UPLOAD INCOMPLETE ({len(verify_failures)} SIZE mismatch — not triggered)"
    elif args.no_trigger:
        status = "STAGED (not triggered)"
    else:
        status = "TRIGGERED (submit.ready sent)"

    # Compute SHA256 of submission.xml for the audit trail — cheap and
    # gives us a way to answer "what did we actually submit" months later.
    xml_sha256 = hashlib.sha256(open(args.submission_xml, "rb").read()).hexdigest()

    # Write audit trail next to the submission.xml so it's carried with
    # the batch. Answers "what did this batch upload where and when."
    receipt = {
        "started_utc": started_at,
        "duration_seconds": round(wall_dt, 1),
        "bytes_uploaded": total_bytes,
        "files_uploaded": n_total,
        "avg_mbit_s": round(avg_mbps, 1),
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "base_dir": args.base_dir,
        "folder_name": folder_name,
        "bioproject": bioproject,
        "submission_xml_sha256": xml_sha256,
        "submit_ready_written": (not args.no_trigger) and (not verify_failures),
        "verify_failures": verify_failures,
        "status": status,
    }
    receipt_path = os.path.join(os.path.dirname(args.submission_xml),
                                "upload_receipt.json")
    try:
        with open(receipt_path, "w") as f:
            json.dump(receipt, f, indent=2)
        logger.info("Audit receipt: %s", receipt_path)
    except OSError as e:
        logger.warning("Could not write %s: %s", receipt_path, e)

    # End-of-run summary block — deliberately distinctive so it doesn't blend
    # into the per-file INFO stream.
    banner = "=" * 64
    logger.info("")
    logger.info(banner)
    logger.info("SUBMISSION SUMMARY")
    logger.info(banner)
    logger.info("Started (UTC):   %s", started_at)
    logger.info("Duration:        %.1f s (%.1f min)", wall_dt, wall_dt / 60)
    logger.info("Data:            %.2f GB, %d files", total_bytes / 1e9, n_total)
    logger.info("Avg bandwidth:   %.1f Mbit/s", avg_mbps)
    logger.info("Remote folder:   %s/%s", args.base_dir.rstrip("/"), folder_name)
    logger.info("Status:          %s", status)
    logger.info("XML SHA256:      %s", xml_sha256[:16] + "...")
    logger.info(banner)


if __name__ == "__main__":
    cli()
