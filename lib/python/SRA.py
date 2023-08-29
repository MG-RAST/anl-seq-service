import logging
import argparse
import sys
import os
import re
import glob
import pysftp

logging.basicConfig(format='%(levelname)s %(asctime)s\t%(message)s', level=logging.INFO)


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

            for line in f:
                parts = line.rstrip().split("\t")
                sites[parts[0]] = { 
                                    header[1]   : parts[1] ,
                                    header[2]   : parts[2]
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

        k = "file"
        v = None

        if "R1" in parts or "R2" in parts:
            logger.debug("Found R1 or R2 in %s.", f)
            k = parts[2]
            v = f
       
        if not ID in samples :
            samples[ID] = sample
    
        samples[ID][k]=v

    logger.info("Found %s samples" , len(samples.keys()))
    return samples

def make_biosample_file(header=None, data=None, constants=None, mapping=None, samples=None, sites=None, output=None) :
    logger.debug("Creating biosample file.")

    # assuming sample_name column is index 0
    sample_idx  = 0
    idx   = []

    map2 = {}

    # find columns
    for i,v in enumerate(header) :
        if re.search("filename|sample_name|collection_date|collection_time|collection_site_id|collected_by|ww_population|ww_sample_type|ww_sample_duration|ww_surv_system_sample_id|ww_surv_target_1_conc", v) :
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
        
        if not row[map2['ww_surv_system_sample_id']] :
            row[map2['ww_surv_system_sample_id']] = row[map2['sample_name']]
        else:
            logger.debug("Found existing ww_surv_system_sample_id:\t" + row[map2['ww_surv_system_sample_id']] )

        if row[0] in mapping['samples'] :
            # fill in collected_by and ww_population based on sites file
            row[map2['collected_by']] = sites[row[map2["collection_site_id"]]]['collected_by']
            row[map2['ww_population']] = sites[row[map2["collection_site_id"]]]['ww_population']

            # metadata from NWSS samples file
            row[map2['collection_date']] = mapping['samples'][row[0]]['sample_collect_date']
            row[map2['collection_time']] = mapping['samples'][row[0]]['sample_collect_time']
            row[map2['ww_surv_target_1_conc']] = mapping['samples'][row[0]]['pcr_target_avg_conc']

            type = mapping['samples'][row[0]]['sample_type']

            duration = str(type.split("-")[0]) + "H"

            if re.search("composite|passive", type) :
                row[map2['ww_sample_type']] = 'composite'
            elif re.search("grab", type) :
                row[map2['ww_sample_type']] = 'grab'
            else:
                row[map2['ww_sample_type']] = 'missing'
                logger.error("Can not identify sample type from: %s" , type)


            row[map2['ww_sample_duration']] = duration 

        else:
            logger.error("ID %s not in mapping, probably missing from %s." , row[0] , args.samples)


        if fh :
            fh.write("\t".join(row) + "\n")
        else:
            print("\t".join(row))


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

    with open(file) as f :
        h = f.readline()
        i2h = h.rstrip().split(",")
        for i,v in enumerate( i2h ) :
            header[v] = i
            

        md['header'] = header
        l = 1
        for line in f :
            col = line.rstrip().split(",")
            data.append( col )

            samples[col[0]] = {}
            for i,v in enumerate(i2h) :
                samples[col[0]][ i2h[i] ] = col[i]
            
            # Cross check nr headers vs nr rows
            if len(i2h) < len(col) :
                error = True
                msg = "Mismatch number of columns in header row versus number of columns in data rows"
                # logger.warning("Number of header columns does not match columns in row %i." , l) 
            l += 1

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



def upload_fastqs(user="IL_NWSS", password=None, source=None , url="eft.cdc.gov" , dest="/Data/Test/", run_file=None, biosample_file=None ) :

    port = 22

    fastqs = []
    if run_file :
        with open(run_file) as r :
            
            # Find filename columns
            header=[]
            header_row = r.readline() 
            header_columns = header_row.rstrip().split("\t")
            for i,v in enumerate(header_columns) :
                if re.search("filename", v ) :
                    header.append(i)
            logger.debug("Found filename header: %s" , header)   

            # Find files from filename columns
            for line in r :
                columns = line.rstrip().split("\t")
                for i in header :
                    if columns[i] :
                        fastqs.append(columns[i])
                    else:
                        # logger.warning("No value in filename column %s" , str(i))
                        pass


    try:
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        sftp = pysftp.Connection(host=url ,port=port, username=user, password=password, cnopts=cnopts)
        print("connection established successfully")

        if sftp.isdir(dest) :
            with sftp.cd(dest):
                logger.debug("Changed into %s" , dest)
                # for f in sftp.listdir():
                #     print(f)
        
                for f in fastqs :
                    # upload
                    file_path = f
                    if os.path.isdir(source) :
                        file_path = source + "/" + f
                    
                    # upload
                    if os.path.isfile(file_path) :
                        logger.info("Uploading %s" , file_path)
                        sftp.put(file_path, preserve_mtime=True)

        else :
            logger.error("No such directory %s at %s" , dest, url )

        if run_file and os.path.isfile(run_file) :
            logger.debug("Uploading run file: %s" , run_file)
            sftp.put(run_file, preserve_mtime=True)
        else :
            logger.error("Missing run file for upload")
        
        if biosample_file and os.path.isfile(biosample_file) :
            logger.debug("Uploading biosample file: %s" , biosample_file)
            sftp.put(biosample_file, preserve_mtime=True)
        else :
            logger.error("Misisng biosample file for upload")

        sftp.close()

    except:
        print('failed to establish connection to targeted server')
    pass


def command_line_options():
    """Define and parse command line options"""
    parser = argparse.ArgumentParser(description='Command line options for creating SRA metadata file from template')
  
    parser.add_argument('--run-template', dest='run_template', 
                    help='template file for a given run')
    parser.add_argument('--run-output', dest='run_output', default=None, 
                    help='run file, created from --run-template and --sequence-dir')
    parser.add_argument('--run-file', dest='run_file', default=None, 
                    help='Upload run file, created from --run-template and --sequence-dir. Same as --run-output')
    parser.add_argument('--biosample-template', dest='biosample_template', 
                    help='biosample template file for a given run')
    parser.add_argument('--biosample-output', dest='biosample_output', default=None, 
                    help='biosample file, created from --biosample-template and --sequence-dir')
    parser.add_argument('--biosample-file', dest='biosample_file', default=None, 
                    help='upload biosample file, created from --biosample-template and --sequence-dir , same as --biosample-output')
    parser.add_argument('--sites', dest='sites', default=None, 
                    help='sites mapping file, contains collected_by and ww_population')
    parser.add_argument('--mapping', dest='mapping', 
                    help='mapping file for constants in specified columns')
    parser.add_argument('--sequence-dir', dest='dir', default=None ,
                    help='directory containing sequences/samples to be included in the submission file')
    parser.add_argument('--samples', dest='samples', default=None ,
                    help='sample file, contains sample metadata; probably csv')
    parser.add_argument('--log-level', dest='level', choices=["DEBUG", "INFO" , "WARNINGS" , "ERROR"], default="INFO" ,
                    help='sample file, contains sample metadata; probably csv')
    parser.add_argument('--upload', dest='upload', default=False , action="store_true",
                    help='enable to upload sequence files, requires run file')
    parser.add_argument('--upload-dir', dest='upload_dir',  default="/Data/Prod/" ,
                    help='path on ftp site')
    parser.add_argument('--upload-url', dest='upload_url',  default="eft.cdc.gov" ,
                    help='path on ftp site')
    parser.add_argument('--user', dest='user',  default=None ,
                    help='user for ftp')
    parser.add_argument('--password', dest='password', default=None ,
                    help='password for ftp user')
    

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
        if not args.run_file :
            args.run_file = args.run_output

    if args.biosample_template :
        sites = read_site_ID(args.sites)
        (header, data, const) = read_template(template=args.biosample_template)
        make_biosample_file(header=header, data=data, constants=const,  mapping=metadata , output=args.biosample_output , sites=sites)
        if not args.biosample_file :
            args.biosample_file = args.biosample_output

    if args.upload :
        if args.user and args.password and args.dir :
            folder = args.upload_dir
            upload_fastqs(user=args.user, password=args.password, source=args.dir , url=args.upload_url , dest=args.upload_dir, run_file=args.run_file, biosample_file=args.biosample_file)

        else :
            logger.error("Missing user, password or url for upload.")


    


if __name__ == '__main__' :
    logger = logging.getLogger(__name__)
    
    args = command_line_options()
  

    cfg = init( options=args)
    logger.debug(args)
    logger.debug("Template:\t" + str(args.run_template))

    # logger.setLevel("INFO")
    main(args)