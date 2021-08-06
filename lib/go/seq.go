package main

// Data movement tool between Shock and S3 service
// Config:
// Shock has two local storage locations,
// - data dir
// - cache dir
// S3 data is stored in multiple buckets based on the service the shock data belongs to

// S3 to Shock
// 1. Get node id and create download path (node directory) in cache dir
// 2. Download node into node directory under the cache
// 3. Create symlink to node in corresponding node dir under data

import (
	"anl-seq-service/config"
	"anl-seq-service/mgrast"
	s "anl-seq-service/shock"
	"flag"
	"fmt"
	"time"
	// "github.com/minio/minio-go/v7"
)

// GO111MODULE=on go get github.com/minio/minio-go/v7

var shock s.Shock

func main() {

	// TEST

	// Endpoint := "127.0.0.1:9000" // "172.17.0.3:9000" //
	// AccessKey := "minioadmin"
	// SecretKey := "minioadmin"
	// useSSL := false

	// wordPtr := flag.String("word", "foo", "a string")
	// numbPtr := flag.Int("numb", 42, "an int")
	// boolPtr := flag.Bool("fork", false, "a bool")

	cfg := config.Load()
	shock := s.New(cfg.Shock.Url, cfg.Shock.Token)

	if flag.NArg() < 1 {
		cfg.Logger.Info.Fatalln("Missing action: get, put, ls , import, export, mgrast")
	} else {
		if flag.NArg() >= 1 {
			if flag.Arg(0) == "get" {
				// errlog.Fatalf("Option %s not implemented", flag.Arg(0))
				fmt.Println(flag.Arg(0))
				var q s.Query
				shock.Get(q)
			} else if flag.Arg(0) == "put" {

			} else if flag.Arg(0) == "ls" {
				if flag.NArg() == 1 {
					shock.Ls("", "", "")
				} else if flag.NArg() == 2 {
					shock.Ls(flag.Arg(1), "", "")
				} else if flag.NArg() == 3 {
					shock.Ls(flag.Arg(1), flag.Arg(2), "")
				} else if flag.NArg() == 4 {
					shock.Ls(flag.Arg(1), flag.Arg(2), flag.Arg(3))
				}
			} else if flag.Arg(0) == "export" {

			} else if flag.Arg(0) == "import" {

			} else if flag.Arg(0) == "mgrast" {
				if flag.NArg() == 1 {
					fmt.Printf("Missing option for %s. Valid options 'upload'\n", flag.Arg(0))
				} else {
					fmt.Printf("Working on implementing %s %s.\n", flag.Arg(0), flag.Arg(1))

					if flag.NArg() == 2 {
						fmt.Printf("Missing arguments:  %s %s <inbox/user name> <project_id> <project>. \n", flag.Arg(0), flag.Arg(1))
						return
					}

					var user_login, project, project_id string

					if flag.NArg() >= 4 {
						user_login = flag.Arg(2)
					}
					if flag.NArg() >= 4 {
						project_id = flag.Arg(3)
					}
					if flag.NArg() >= 5 {
						project = flag.Arg(4)
					}

					fmt.Printf("Command: %s %s %s %s\n", flag.Arg(0), flag.Arg(1), project, project_id)
					mgrast.Upload(project_id, project, "", user_login, shock)

				}
			} else if flag.Arg(0) == "test" {
				fmt.Println("TEST")
				var attr struct {
					Node_type  string   `json:"type"`
					User_id    string   `json:"id"`
					User_login string   `json:"name"`
					User_email string   `json:"email"`
					Origin     string   `json:"origin"`
					Tag        []string `json:"tag"`
				}

				// Using time.Now() function.
				dt := time.Now()
				fmt.Println("Current date and time is: ", dt.String())

				attr.User_id = "mgu26992"
				attr.User_login = "owenss"
				attr.Node_type = "inbox"
				attr.Origin = "Argonne Sequencing Center"
				attr.Tag = []string{"ANL", "Argonne Sequencing Center", "date:" + dt.String()}

				node_id := "177d2a0a-43ee-4bf7-8281-749353f96df6"
				copy, _ := shock.CopyNode(node_id)
				fmt.Printf("Setting attributes for %s\n", copy.Id)
				shock.SetAttributes(copy.Id, attr)
				shock.SetRWD(copy.Id, attr.User_login)

			} else {
				fmt.Printf("Option %s not implemented.\n", flag.Arg(0))
				// cfg.errlog.Fatalf("Option %s not implemented", flag.Arg(0))

			}
		} else {
			// errlog.Fatalf("Missing arguments for %s", flag.Arg(0))
		}
	}

}
