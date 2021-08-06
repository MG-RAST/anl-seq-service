package config

import (
	"flag"
	"log"
	"os"
)

var (
	warnlog  = log.New(os.Stderr, "[ warn  ]", log.Ltime|log.Lshortfile)
	infolog  = log.New(os.Stderr, "[ info  ]", log.Ltime)
	buildlog = log.New(os.Stderr, "[ build ]", log.Ltime|log.Lshortfile)
	errlog   = log.New(os.Stderr, "[ error ]", log.Ltime|log.Lshortfile)
	debuglog = log.New(os.Stderr, "[ debug ]", log.Ltime|log.Lshortfile)
)

const OWNER string = "ANL-SEQ-Core"

type s3cfg struct {
	Endpoint   string
	SecretKey  string
	AccessKey  string
	Bucket     string
	ObjectName string
}

type Config struct {
	S3    s3cfg
	Shock struct {
		dataDir  string
		cacheDir string
		Url      string
		Token    string
	}
	Debug   bool
	Verbose bool
	Logger  struct {
		Error *log.Logger
		Debug *log.Logger
		Info  *log.Logger
	}
}

func Load() Config {

	cfg := Config{}

	cfg.Logger.Info = log.New(os.Stdout, "[ info  ]", log.Ltime)
	cfg.Logger.Debug = log.New(os.Stderr, "[ debug  ]", log.Ltime)
	cfg.Logger.Error = log.New(os.Stderr, "[ error  ]", log.Ltime)

	cfg.S3.Endpoint = os.Getenv("S3_ENDPOINT_URL")
	cfg.S3.AccessKey = os.Getenv("S3_ACCESS_KEY")
	cfg.S3.SecretKey = os.Getenv("S3_SECRET_KEY")
	cfg.S3.Bucket = os.Getenv("S3_BUCKET")

	cfg.Shock.dataDir = os.Getenv("SHOCK_DATA_DIR")
	cfg.Shock.cacheDir = os.Getenv("SHOCK_CACHE_DIR")

	debugPtr := flag.Bool("debug", false, "Enable debugging")
	verbosePtr := flag.Bool("verbose", false, "Descriptive output")
	// dataPathPtr := flag.String("data-path", ".", "Base path for Shock data directory")
	// uploadFilePtr := flag.String("file", "", "Upload file")
	s3bucketPtr := flag.String("bucket", "", "S3 bucket name")
	cacheDirPtr := flag.String("cache-dir", "", "Local cache directory")
	dataDirPtr := flag.String("data-dir", "", "Local data directory")
	shockHostPtr := flag.String("shock-host", "https://shock.mg-rast.org", "Shock host")
	shockTokenPtr := flag.String("shock-token", "", "Shock auth token")

	objectNamePtr := flag.String("object-name", "", "Target object name in s3 store")

	flag.Parse()

	if *s3bucketPtr != "" {
		cfg.S3.Bucket = *s3bucketPtr
	}

	if *cacheDirPtr != "" {
		cfg.Shock.cacheDir = *cacheDirPtr
	}

	if *dataDirPtr != "" {
		cfg.Shock.dataDir = *dataDirPtr
	}

	cfg.S3.ObjectName = *objectNamePtr
	cfg.Debug = *debugPtr
	cfg.Verbose = *verbosePtr

	cfg.Shock.Url = *shockHostPtr
	cfg.Shock.Token = *shockTokenPtr

	if cfg.Debug {
		debuglog.Printf("Config: %s\n", cfg)
	}

	return cfg
}
