#!/usr/bin/env python3
"""Generate NCBI submission.xml (BioSample + SRA actions) from run.tsv + Biosample.tsv."""

import argparse
import csv
import logging
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)

# Columns rendered as structural XML elements rather than <Attribute>.
BIOSAMPLE_STRUCTURAL = {"sample_name", "sample_title", "bioproject_accession", "organism"}
RUN_STRUCTURAL = {"sample_name"}
RUN_FILE_COLUMNS = ("filename", "filename2", "filename3", "filename4")


def read_tsv(path):
    """Return (header, rows). Strips leading '*' (template required-column marker) from headers."""
    with open(path) as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if not rows:
        raise ValueError(f"Empty TSV: {path}")
    header = [c.lstrip("*") for c in rows[0]]
    return header, rows[1:]


def index_by_sample_name(header, rows):
    """Return {sample_name: {column: value}}. Raise on duplicate sample_name."""
    try:
        sn_idx = header.index("sample_name")
    except ValueError:
        raise ValueError("TSV missing 'sample_name' column")
    out = {}
    duplicates = []
    for row in rows:
        row = list(row) + [""] * (len(header) - len(row))
        name = row[sn_idx].strip()
        if not name:
            continue
        if name in out:
            duplicates.append(name)
            continue
        out[name] = dict(zip(header, row))
    if duplicates:
        raise ValueError(
            f"Duplicate sample_name(s) in TSV: {sorted(set(duplicates))}. "
            "Each sample must appear at most once."
        )
    return out


def derive_contact_name():
    """First/Last from `git config user.name`; ('', '') if not set."""
    try:
        full = subprocess.check_output(
            ["git", "config", "--get", "user.name"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "", ""
    parts = full.split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return parts[0], ""
    return "", ""


def build_description(comment, org, email, first, last):
    desc = ET.Element("Description")
    ET.SubElement(desc, "Comment").text = comment
    organization = ET.SubElement(desc, "Organization", role="owner", type="center")
    ET.SubElement(organization, "Name").text = org
    contact = ET.SubElement(organization, "Contact", email=email)
    name = ET.SubElement(contact, "Name")
    ET.SubElement(name, "First").text = first
    ET.SubElement(name, "Last").text = last
    return desc


def build_biosample_action(sample, header, package, spuid_ns):
    name = sample["sample_name"]
    action = ET.Element("Action")
    add = ET.SubElement(action, "AddData", target_db="BioSample")
    data = ET.SubElement(add, "Data", content_type="XML")
    xml_content = ET.SubElement(data, "XmlContent")
    bs = ET.SubElement(xml_content, "BioSample", schema_version="2.0")

    sample_id = ET.SubElement(bs, "SampleId")
    ET.SubElement(sample_id, "SPUID", spuid_namespace=spuid_ns).text = name

    descriptor = ET.SubElement(bs, "Descriptor")
    if sample.get("sample_title"):
        ET.SubElement(descriptor, "Title").text = sample["sample_title"]

    organism = ET.SubElement(bs, "Organism")
    ET.SubElement(organism, "OrganismName").text = sample.get("organism", "")

    bp = sample.get("bioproject_accession", "")
    if bp:
        bioproject = ET.SubElement(bs, "BioProject")
        ET.SubElement(bioproject, "PrimaryId", db="BioProject").text = bp

    ET.SubElement(bs, "Package").text = package

    attrs = ET.SubElement(bs, "Attributes")
    for col in header:
        if col in BIOSAMPLE_STRUCTURAL:
            continue
        val = sample.get(col, "")
        if not val:
            continue
        ET.SubElement(attrs, "Attribute", attribute_name=col).text = val

    identifier = ET.SubElement(add, "Identifier")
    ET.SubElement(identifier, "SPUID", spuid_namespace=spuid_ns).text = name
    return action


def build_sra_action(sample, header, spuid_ns, bioproject):
    name = sample["sample_name"]
    action = ET.Element("Action")
    add = ET.SubElement(action, "AddFiles", target_db="SRA")

    for col in RUN_FILE_COLUMNS:
        fn = sample.get(col, "")
        if fn:
            f = ET.SubElement(add, "File", file_path=fn)
            ET.SubElement(f, "DataType").text = "generic-data"

    for col in header:
        if col in RUN_STRUCTURAL or col in RUN_FILE_COLUMNS:
            continue
        val = sample.get(col, "")
        if not val:
            continue
        ET.SubElement(add, "Attribute", name=col).text = val

    if bioproject:
        ref_bp = ET.SubElement(add, "AttributeRefId", name="BioProject")
        rid = ET.SubElement(ref_bp, "RefId")
        ET.SubElement(rid, "PrimaryId", db="BioProject").text = bioproject

    ref_bs = ET.SubElement(add, "AttributeRefId", name="BioSample")
    rid = ET.SubElement(ref_bs, "RefId")
    ET.SubElement(rid, "SPUID", spuid_namespace=spuid_ns).text = name

    identifier = ET.SubElement(add, "Identifier")
    ET.SubElement(identifier, "SPUID", spuid_namespace=spuid_ns).text = f"SRA_{name}"
    return action


def build_submission(biosample_tsv, run_tsv, package, spuid_ns,
                     org, email, first, last, comment):
    bs_header, bs_rows = read_tsv(biosample_tsv)
    bs_samples = index_by_sample_name(bs_header, bs_rows)
    run_header, run_rows = read_tsv(run_tsv)
    run_samples = index_by_sample_name(run_header, run_rows)

    # BioProject is the same across all samples; grab from first non-empty row.
    bioproject = next(
        (s["bioproject_accession"] for s in bs_samples.values() if s.get("bioproject_accession")),
        "",
    )
    if not bioproject:
        logger.warning("No bioproject_accession found in %s", biosample_tsv)

    submission = ET.Element("Submission")
    submission.append(build_description(comment, org, email, first, last))

    for name, sample in bs_samples.items():
        submission.append(build_biosample_action(sample, bs_header, package, spuid_ns))

    skipped = []
    for name, sample in run_samples.items():
        if name not in bs_samples:
            logger.warning("Sample %s in run.tsv but not in Biosample.tsv", name)
        if not any(sample.get(c) for c in RUN_FILE_COLUMNS):
            skipped.append(name)
            continue
        submission.append(build_sra_action(sample, run_header, spuid_ns, bioproject))

    if skipped:
        logger.warning("Skipped %d SRA actions with no fastq filenames: %s",
                       len(skipped), skipped)

    logger.info("BioSample actions: %d, SRA actions: %d, BioProject: %s",
                len(bs_samples), len(run_samples) - len(skipped), bioproject or "(none)")
    return submission


def write_xml(elem, path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    rough = ET.tostring(elem, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    with open(path, "wb") as f:
        f.write(pretty)


def cli():
    p = argparse.ArgumentParser(
        description="Generate NCBI submission.xml from run.tsv + Biosample.tsv")
    p.add_argument("--run-tsv", required=True,
                   help="Final run TSV (e.g. SRA/240119.run.tsv)")
    p.add_argument("--biosample-tsv", required=True,
                   help="Final BioSample TSV (e.g. SRA/240119.Biosample.tsv)")
    p.add_argument("--output", required=True,
                   help="Output path for submission.xml")
    p.add_argument("--package", default="SARS-CoV-2.wwsurv.1.0",
                   help="NCBI BioSample package")
    p.add_argument("--spuid-namespace", default="ANL",
                   help="SPUID namespace prefix")
    p.add_argument("--org", default="Argonne National Laboratory",
                   help="Organization name")
    p.add_argument("--contact-email", default=os.environ.get("NCBI_CONTACT"),
                   help="Submitter contact email (defaults to $NCBI_CONTACT)")
    p.add_argument("--contact-first", default=None,
                   help="Submitter first name (default: from git config user.name)")
    p.add_argument("--contact-last", default=None,
                   help="Submitter last name (default: from git config user.name)")
    p.add_argument("--comment", default=None,
                   help="Submission comment (default: derived from run-tsv basename)")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = p.parse_args()

    logging.basicConfig(format="%(levelname)s %(asctime)s\t%(message)s",
                        level=args.log_level)

    if not args.contact_email:
        logger.error("Contact email required: pass --contact-email or set NCBI_CONTACT")
        sys.exit(2)

    if args.contact_first is None or args.contact_last is None:
        gf, gl = derive_contact_name()
        if args.contact_first is None:
            args.contact_first = gf
        if args.contact_last is None:
            args.contact_last = gl

    if not args.contact_first or not args.contact_last:
        logger.error("Contact first/last required: pass --contact-first/--contact-last "
                     "or set `git config user.name`")
        sys.exit(2)

    if not args.comment:
        base = os.path.basename(args.run_tsv)
        for suffix in (".run.tsv", ".tsv"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        args.comment = f"Wastewater surveillance run {base}"

    submission = build_submission(
        args.biosample_tsv, args.run_tsv, args.package, args.spuid_namespace,
        args.org, args.contact_email, args.contact_first, args.contact_last,
        args.comment,
    )
    write_xml(submission, args.output)
    logger.info("Wrote %s", args.output)


if __name__ == "__main__":
    cli()
