import logging
import argparse
import sys
import os
import re
import glob

logging.basicConfig(format='%(levelname)s %(asctime)s\t%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# create config
def init( options : None) :
    """Create initial config"""
    # logger.setLevel(logging.DEBUG)
    # logger.debug("Debugging")
    logger.setLevel(options.level)
    
    cfg = None
    if options :
        cfg = options
    return cfg

def read_biosample_template(biosample_template=None) :
    """Read biosample template file"""

    logger.info("Reading biosample template " + str(biosample_template))

    mapping = None
    data = None
    const = {}
    
    # find header and first row
    found_header_row = False
    first_row        = False
    
    # store header information
    header = None
    data   = []
    constants = {}

    if biosample_template and os.path.isfile(biosample_template) :
        with open(biosample_template) as f :
            for line in f:
                parts = line.rstrip().split("\t")

                if not found_header_row :
                    if re.search("sample_name", parts[0]) :
                        header = parts
                        found_header_row = True
                        first_row = True
                elif first_row :

                    data.append(parts)
                else :
                    data.append(parts)
                line = f.readline()
                print(line)
                logger.debug("Searching sample_name, skipping line.")
                found_header_row = True

def read_site_ID(file) :
    logger.debug("Reading SiteID file.")

    sites = None

    if file and os.path.isfile(file) :
        sites = {}
        header = {}
        with open(file) as f:

            l = f.readline().rstrip()
            h = map( lambda x : x.lstrip("*") , l.split("\t"))
            for i,v in enumerate(h):
                header[i] = v

            for lineno, line in enumerate(f, 2):
                # rstrip("\r\n") preserves trailing empty fields; rstrip()
                # without args drops them (S0188 case: empty ww_population
                # becomes 2-element row and IndexError'd on parts[2]).
                parts = line.rstrip("\r\n").split("\t")
                if not parts or not parts[0]:
                    continue
                # Pad row to header width so short rows don't IndexError.
                if len(parts) < len(header):
                    parts = parts + [""] * (len(header) - len(parts))
                sites[parts[0]] = {
                    header[1] : parts[1] ,
                    header[2] : parts[2] ,
                }
    else:
        logger.error("No SiteID file:\t" + str(file))

    return sites

def read_sequence_dir(dir) :
    """Read sequence dir, collect all fastq files"""

    logger.debug("Creating list of fastq files from " + str(dir))
    fastq_files = []

    if dir and os.path.isdir(dir):
        # print(glob.glob(dir + "/*.fastq*"))
        for fastq in glob.glob(dir + "/*.fastq*") :
            fastq_files.append( os.path.basename(fastq))
    else:
        logger.error("Missing directory " + str(dir))
    logger.info("Found " + str(len(fastq_files)) + " files.")
    return fastq_files

def fastqs_to_samples(list_of_fastqs) :
    """Takes a list of fastq files and extract sample ID. Return dictionary sample to files."""
    logger.debug("Creating sample list.")
    samples = {}

    for f in list_of_fastqs :
        parts = f.split("_")
        # print(parts)
        ID = parts[0]

        # Initialize sample dict and key and value variables for dictionary
        sample = {
            "file" : None ,
            "R1" : None ,
            "R2" : None 
            }

        k = "file" # key
        v = None   # value

        for p in parts:
            if "R1" == p  or "R2" == p:
                logger.debug("Found %s in %s.", p,f)
                k = p
                v = f
       
        if not ID in samples :
            samples[ID] = sample
    
        samples[ID][k]=v
    # logger.debug(str(samples))
    logger.info("Found %s samples" , len(samples.keys()))
    return samples

def _site_field(sites, site_id, field, default="not collected"):
    """Look up sites[site_id][field] safely; return default if missing/empty."""
    if not site_id:
        return default
    entry = sites.get(site_id) if sites else None
    if not entry:
        return default
    value = entry.get(field, "")
    return value if value else default


def make_biosample_file(header=None, data=None, constants=None, mapping=None, samples=None, sites=None, output=None) :
    logger.debug("Creating biosample file.")

    # assuming sample_name column is index 0
    sample_idx  = 0
    idx   = []
    word = re.compile("\w+")
    map2 = {}
    # Per-row failure counters so a single bad row can't truncate the whole file.
    skipped_missing_site = set()
    rows_crashed = 0

    # find columns
    for i,v in enumerate(header) :
        if re.search("filename|sample_name|collection_date|collection_time|collection_site_id|collected_by|ww_population|ww_sample_type|ww_sample_duration|ww_surv_system_sample_id|ww_surv_target_1_conc|ww_surv_jurisdiction", v) :
            idx.append(i)
            map2[v] = i
            logger.debug("Found column %s : %s", v , str(i))
        else:
            map2[v] = i
 
        
    logger.debug("Columns: " + str(idx))

    # Print file
    fh = None
    if output :
        fh = open(output, "w")
    # Header
    if fh :
        fh.write("\t".join(header) + "\n")
    else:
        print("\t".join(header))

    for row in data:

        # ensure row has same length than header
        while len(row) < len(header) :
            row.append('')

        id = row[sample_idx]
        idx = 0

        # fill in constants
        for i,v in enumerate(row) :
            if not v :
                if header[i] in constants and constants[header[i]] is not None :
                    row[i] = constants[header[i]]
                else :
                    row[i] = ''

        # talked to Sarah - always set to sample_name
        row[map2['ww_surv_system_sample_id']] = row[map2['sample_name']]

        site_id = row[map2["collection_site_id"]] if "collection_site_id" in map2 else ""
        if site_id and sites is not None and site_id not in sites:
            skipped_missing_site.add(site_id)

        # Guarantee NCBI-required fields have a value BEFORE enrichment tries.
        # If enrichment fails partway (KeyError / IndexError), the row still
        # writes with these defaults instead of a partially-populated broken row.
        REQUIRED_DEFAULTS = ('collection_date', 'ww_population',
                             'ww_sample_type', 'ww_sample_duration',
                             'collected_by')
        for req in REQUIRED_DEFAULTS:
            if req in map2 and not row[map2[req]]:
                row[map2[req]] = "not collected"

        try:

          if row[0] in mapping['samples'] :
            # fill in collected_by and ww_population based on sites file
            collected_by = _site_field(sites, site_id, 'collected_by')
            row[map2['collected_by']] = collected_by if word.search(collected_by) else "not collected"
            ww_population = _site_field(sites, site_id, 'ww_population')
            row[map2['ww_population']] = ww_population if word.search(ww_population) else "not collected"

            # metadata from NWSS samples file
            row[map2['collection_date']] = mapping['samples'][row[0]]['sample_collect_date'] if word.search(mapping['samples'][row[0]]['sample_collect_date']) else "not collected"
            row[map2['collection_time']] = mapping['samples'][row[0]]['sample_collect_time'] if word.search(mapping['samples'][row[0]]['sample_collect_time']) else "not collected"
            row[map2['ww_surv_target_1_conc']] = mapping['samples'][row[0]]['pcr_target_avg_conc'] if word.search(mapping['samples'][row[0]]['pcr_target_avg_conc']) else "not collected"

            # check collection date, change date format if necessary. Target is yyyy-mm-dd.
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[map2['collection_date']]) :
                # if date in format mm/dd/yyyy, change to yyyy-mm-dd
                if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", row[map2['collection_date']]) :
                    m, d, y = row[map2['collection_date']].split("/")
                    row[map2['collection_date']] = f"{y}-{int(m):02d}-{int(d):02d}"
                elif row[map2['collection_date']] != "not collected" :
                    logger.error("Date format not recognized (sample %s): %s",
                                 row[0], row[map2['collection_date']])
            

            ### addition mapping from reporting_jurisdiction to ww_surv_jurisdiction 
            row[map2['ww_surv_jurisdiction']] = mapping['samples'][row[0]]['reporting_jurisdiction']

            type = mapping['samples'][row[0]]['sample_type'] if mapping['samples'][row[0]]['sample_type'] else "not collected"

            duration = str(type.split("-")[0])

            # default to "not collected" and duration to zero
            row[map2['ww_sample_type']] = 'not collected'

            if re.search("composite|passive", type) :
                row[map2['ww_sample_type']] = 'composite'
            elif re.search("grab", type) :
                row[map2['ww_sample_type']] = 'grab'
                duration="0"
            else:
                # row[map2['ww_sample_type']] = 'missing'
                # logger.error("Can not identify sample type from: %s" , type)
                logger.error("Can not identify sample type from: %s. Using default: %s" , type, row[map2['ww_sample_type']])
                duration="not collected"


            row[map2['ww_sample_duration']] = duration

          else:
            logger.error("ID %s not in mapping, probably missing from %s." , row[0] , args.samples)
            # Set defaults using safe site lookup
            row[map2['collected_by']] = _site_field(sites, site_id, 'collected_by')
            row[map2['ww_population']] = _site_field(sites, site_id, 'ww_population')


            # metadata from NWSS samples file
            row[map2['collection_date']] = "not collected"
            row[map2['collection_time']] = "not collected"
            row[map2['ww_surv_target_1_conc']] = "not collected"

            type = mapping['samples'][row[0]]['sample_type'] if row[0] in mapping['samples'] else "not collected"

            # set default to "not collected" and duration to zero, type e.g. Moore 
            duration = "0"
            row[map2['ww_sample_type']] = "not collected"
            
            if not type == "not collected" :

                duration = str(type.split("-")[0]) if not type == "not collected" else 0
   

                if re.search("composite|passive", type) :
                    row[map2['ww_sample_type']] = 'composite'
                elif re.search("grab", type) :
                    row[map2['ww_sample_type']] = 'grab'
                    duration = "0"
                else:
                    # row[map2['ww_sample_type']] = 'missing' 
                    logger.error("Can not identify sample type from: %s. Using default: %s" , type, row[map2['ww_sample_type']])


            row[map2['ww_sample_duration']] = duration

        except (KeyError, IndexError, TypeError, ValueError) as e:
            # Enrichment failed for this row (missing key in samples/sites,
            # bad column count, malformed value). Row still has the required-
            # field defaults applied above, so we write it and continue.
            rows_crashed += 1
            exc_type = type(e).__name__
            logger.error("Enrichment failed for sample %s: %s: %s. "
                         "Row written with 'not collected' defaults.",
                         row[0] if row else "?", exc_type, e)

        if fh :
            fh.write("\t".join(row) + "\n")
        else:
            print("\t".join(row))

    if skipped_missing_site:
        logger.warning("Missing site IDs (referenced in template but absent from "
                       "SiteID.tsv): %s", sorted(skipped_missing_site))
    if rows_crashed:
        logger.warning("%d rows written with partial defaults due to enrichment "
                       "errors (previously would have truncated output).",
                       rows_crashed)
    logger.info("Biosample file: wrote %d rows from %d template rows.",
                len(data), len(data))
    if fh :
        fh.close()


def make_run_file(header=None, data=None, constants=None, mapping=None, samples=None, output=None) :
    logger.debug("Creating run file.")

    # assuming sample_name column is index 0
    sample_idx  = 0
    files_idx   = []

    for i,v in enumerate(header) :
        if re.search("filename", v) :
            files_idx.append(i)
            logger.debug("Found file column %s : %s", v , str(i))
 
        
    logger.debug("File columns: " + str(files_idx))

    # Print file
    fh = None
    if output :
        fh = open(output, "w")
    # Header
    if fh :
        fh.write("\t".join(header) + "\n")
    else:
        print("\t".join(header))

    for row in data:

        # ensure row has same length than header
        while len(row) < len(header) :
            row.append('')

        id = row[sample_idx]
        idx = 0

        # add sequence files
        if id in samples :
     
            if samples[id]['file'] :
                row[files_idx[idx]] = samples[id]['file']
                idx += 1
            if samples[id]['R1'] :
                row[files_idx[idx]] = samples[id]['R1'] 
                idx += 1
            if samples[id]['R2'] :
                row[files_idx[idx]] = samples[id]['R2'] 
                idx += 1
        else:
            logger.error("Can't find %s in file list.", id)

        # fill in constants
        for i,v in enumerate(row) :
            if not v :
                if header[i] in constants and constants[header[i]] is not None :
                    row[i] = constants[header[i]]
                else :
                    row[i] = ''

        if fh :
            fh.write("\t".join(row) + "\n")
        else:
            print("\t".join(row))
    if fh :
        fh.close()

def read_template(template=None):
    """Read template file; first column sample_name"""

    logger.info("Reading template " + str(template))

    mapping = None
    data = None
    const = {}

    if template and os.path.isfile(template) :
        with open(template) as f :

            found_header_row = False
            first_row        = False
            # store header information
            header = None
            data   = []
            constants = {}
            
            # read until header row - remember headers and position , read data 
            for line in f :
                # print(line)
                tmp     = line.rstrip().split("\t")
                columns = list(map( lambda x : x.lstrip("*") , tmp ))

                if not found_header_row :
                    if re.search("sample_name", columns[0] ) :
                        header = columns
                        found_header_row = True
                        first_row = True
                        logger.info("Header with " + str(len(header)) + " columns")
                elif first_row :
                    # get values from first row for template
                    for i,k in enumerate(header) :
                        # print(i,k)
                        constants[k] = columns[i]
                    first_row = False
                    data.append(columns)
                else :
                    data.append(columns)

            if not found_header_row :
                logger.error("Can not find row with sample_name")

    else:
        logger.error("No file " + str(run_template))

    return (header , data, constants)

def read_samples(file):
    logger.info("Reading sample metadata from " + str(file))

    md = { 
        'header': None ,
        'data'  : None ,
        'samples' : None
    }

    header = {}
    i2h = []
    data = []
    samples = {}
    error = False
    msg = ""

    with open(file) as f :
        h = f.readline()
        i2h = h.rstrip().split(",")
        for i,v in enumerate( i2h ) :
            header[v] = i

        md['header'] = header
        l = 1
        n_padded = 0
        for line in f :
            col = line.rstrip().split(",")
            # Pad short rows to header length so downstream indexing doesn't
            # IndexError when IDPH/CDPH CSVs have different column counts.
            if len(col) < len(i2h) :
                col = col + [""] * (len(i2h) - len(col))
                n_padded += 1
            data.append( col )

            samples[col[0]] = {}
            for i,v in enumerate(i2h) :
                samples[col[0]][ i2h[i] ] = col[i]

            # Flag rows with EXTRA columns beyond the header — data loss
            if len(i2h) < len(col) :
                error = True
                msg = f"Line {l}: {len(col)} columns > {len(i2h)} header columns; extra fields dropped"
            l += 1
        if n_padded :
            logger.warning("Padded %d rows to header width (samples CSV has "
                           "narrower rows than the widest source CSV)", n_padded)

    md['data'] = data
    md['samples'] = samples
    
    if error :
        logger.error(msg)

    return md

def read_run_template(run_template=None):
    """Read run template file"""

    logger.info("Reading run template " + str(run_template))

    mapping = None
    data = None
    const = {}

    if run_template and os.path.isfile(run_template) :
        with open(run_template) as f :

            found_header_row = False
            first_row        = False
            # store header information
            header = None
            data   = []
            constants = {}
            
            # read until header row - remember headers and position , read data 
            for line in f :
                # print(line)
                columns = line.rstrip().split("\t")

            

                if not found_header_row :
                    if re.search("sample_name", columns[0] ) :
                        header = columns
                        found_header_row = True
                        first_row = True
                        logger.info("Header with " + str(len(header)) + " columns")
                elif first_row :
                    # get values from first row for template
                    for i,k in enumerate(header) :
                        print(i,k)
                        constants[k] = columns[i]
                    first_row = False
                    data.append(columns)
                else :
                    data.append(columns)

            if not found_header_row :
                logger.error("Can not find row with sample_name")

    else:
        logger.error("No file " + str(run_template))

    return (header , data, constants)



def command_line_options():
    """Define and parse command line options"""
    parser = argparse.ArgumentParser(description='Command line options for creating SRA metadata file from template')
  
    parser.add_argument('--run-template', dest='run_template',
                    help='template file for a given run')
    parser.add_argument('--run-output', dest='run_output', default=None,
                    help='run file, created from --run-template and --sequence-dir')
    parser.add_argument('--biosample-template', dest='biosample_template',
                    help='biosample template file for a given run')
    parser.add_argument('--biosample-output', dest='biosample_output', default=None,
                    help='biosample file, created from --biosample-template and --sequence-dir')
    parser.add_argument('--sites', dest='sites', default=None,
                    help='sites mapping file, contains collected_by and ww_population')
    parser.add_argument('--mapping', dest='mapping', 
                    help='mapping file for constants in specified columns')
    parser.add_argument('--sequence-dir', dest='dir', default=None ,
                    help='directory containing sequences/samples to be included in the submission file')
    parser.add_argument('--samples', dest='samples', default=None ,
                    help='sample file, contains sample metadata; probably csv')
    parser.add_argument('--log-level', dest='level',
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                        help='logging level')

    args = parser.parse_args()
    logger.debug(args)
    return args

def main(args) :
    # logger.debug("Debug")
    # logger.info("Info")

    logger.setLevel(args.level)


    if args.samples :
        metadata = read_samples(args.samples)

    if args.run_template :
        fastq = read_sequence_dir(args.dir)
        samples = fastqs_to_samples(fastq)
        (header, data, const) = read_template(template=args.run_template)
        make_run_file(header=header, data=data, constants=const, samples=samples, mapping=None , output=args.run_output)

    if args.biosample_template :
        sites = read_site_ID(args.sites)
        (header, data, const) = read_template(template=args.biosample_template)
        make_biosample_file(header=header, data=data, constants=const,  mapping=metadata , output=args.biosample_output , sites=sites)


    


if __name__ == '__main__' :
    args = command_line_options()
  

    cfg = init( options=args)
    logger.debug(args)
    logger.debug("Template:\t" + str(args.run_template))

    # logger.setLevel("INFO")
    main(args)