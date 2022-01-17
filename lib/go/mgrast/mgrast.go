package mgrast

import (
	"anl-seq-service/shock"
	"fmt"
	"strings"
	"time"
)

const nodeType string = "inbox"
const seqFacility string = "Argonne Sequencing Center"

func Upload(project_id string, project string, file string, user string, client shock.Shock) {

	// create attributes
	fmt.Println("In Upload")

	// create query
	q_project_id := ""
	if project_id != "" {
		q_project_id += "project_id=" + project_id
	}
	q_project := ""
	if project != "" {
		q_project = "project=" + project
	}
	q_file := ""
	if file != "" {
		q_file = "name=" + file
	}

	elems := []string{q_project_id, q_project, q_file}
	query := strings.Join(elems, "&")

	var q shock.Query
	q.Query = query
	q.Limit = 10
	q.Offset = 0

	fmt.Printf("URL for node request %s\n", q.Query)
	req := client.Request(q)

	// get node ids for project and project_id
	for {
		nodes := req.Next()

		if nodes == nil || len(*nodes) == 0 {
			break
		}

		for i, n := range *nodes {
			// v := SeqFile{}
			// jsonbody, _ := json.Marshal(n.Attributes)
			// json.Unmarshal(jsonbody, &v)

			fmt.Printf("%v\t%s\t%s\t%v\n", i, n.Id, n.File.Name, n.File.Size)

			var attr struct {
				Node_type  string   `json:"type"`
				User_id    string   `json:"id"`
				User_login string   `json:"user"`
				User_email string   `json:"email"`
				Origin     string   `json:"origin"`
				Tag        []string `json:"tag"`
			}

			// Using time.Now() function.
			dt := time.Now()
			fmt.Println("Current date and time is: ", dt.String())

			attr.User_login = user
			attr.User_id = "mgu26992"
			attr.Node_type = nodeType
			attr.Origin = seqFacility
			attr.Tag = []string{"ANL", seqFacility, "date:" + dt.String()}

			// node_id := "177d2a0a-43ee-4bf7-8281-749353f96df6"

			copy, _ := client.CopyNode(n.Id)
			fmt.Printf("Setting attributes for %s\n", copy.Id)
			client.SetAttributes(copy.Id, attr)
			client.SetOwner(copy.Id, attr.User_login)
			client.SetRWD(copy.Id, attr.User_login)
			client.ComputeStats(copy.Id)

		}

		q.Offset = q.Offset + q.Limit

	}

}
