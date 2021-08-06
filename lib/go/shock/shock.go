package shock

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"mime/multipart"
	"net/http"
	"strings"
)

type Attributes interface{}

type Envelope struct {
	Err         string
	Limit       int
	Offset      int
	Total_count int
	Status      int
	Data        []Node
}

type EnvelopeSingleNode struct {
	Err         string
	Limit       int
	Offset      int
	Total_count int
	Status      int
	Data        Node
}

type SeqFile struct {
	Group      string // "unaligned3",
	Name       string // "PCH49_CGATGT_L003_R1_001.fastq.gz",
	Owner      string // "ANL-SEQ-Core",
	Project    string // "PCH",
	Project_id string // "121010_SN1035_0118_AC0YM6ACXX",
	Sample     string // "PCH49",
	Type       string //"run-folder-archive-fastq"
}

type Node struct {
	Id      string // "9850883e-1f01-490e-a41e-f5d61ef667a3",
	Version string // "4de4edd6377fb7013f005ac1d098070f",
	File    struct {
		Name     string // "PCH49_CGATGT_L003_R1_001.fastq",
		Size     int    // 1056052030,
		Checksum struct {
			Md5 string // "85981458e4cec412b8b54cd63067b212"
		}
		Format        string
		Virtual       bool
		Virtual_parts []interface{}
		Created_on    string // "2019-11-21T02:12:44.976Z",
		Locked        interface{}
	}
	Attributes    interface{}
	indexes       []interface{}
	version_parts interface{}

	tags          []interface{}
	linkage       []interface{}
	priority      int
	created_on    string // "2019-11-21T02:12:45.028Z",
	last_modified string // "0001-01-01T00:00:00Z",
	expiration    string // "0001-01-01T00:00:00Z",
	Type          string // "basic",
	parts         []interface{}
	Locations     []struct {
		Id     string
		Stored bool
	}

	restore bool
}

type Shock struct {
	URL    string
	Token  string
	Client *http.Client
}

type Query struct {
	Query  string
	Offset int
	Limit  int
}

func (q Query) url(base_url string) string {
	var url string

	url = base_url + "/node?query&owner=ANL-SEQ-Core"

	if q.Query != "" {
		url = url + "&" + q.Query
	}
	if q.Limit > 0 {
		url += fmt.Sprintf("&limit=%v", q.Limit)
	}
	if q.Offset > 0 {
		url += fmt.Sprintf("&offset=%v", q.Offset)
	}

	return url
}

func New(url, token string) Shock {

	var sc Shock

	sc.Client = &http.Client{}
	sc.URL = url
	sc.Token = token

	return sc
}

func (s Shock) Get(query Query) (nodes *[]Node, err error) {
	// url := s.URL + "/node/" + "?query&owner=ANL-SEQ-Core&" + query + "&offset=" + fmt.Sprint(offset) + "&limit=" + fmt.Sprint(limit)
	//project_id=121010_SN1035_0118_AC0YM6ACXX&project=PCH"

	url := query.url(s.URL)
	fmt.Println(url)

	req, err := http.NewRequest("GET", url, nil)
	req.Header.Add("Authorization", "mgrast "+s.Token)
	response, err := s.Client.Do(req)

	if err != nil {
		return
	}
	var body []byte
	body, err = ioutil.ReadAll(response.Body)

	// var f interface{}
	var e Envelope
	err = json.Unmarshal(body, &e)

	// fmt.Println(string(body))
	// fmt.Println(e.Data)
	// fmt.Println(e.Total_count)

	if err != nil {
		fmt.Printf("Error: %v", err)
	}

	// for i, n := range f.(map[string]interface{}) {
	nodes = &e.Data

	for _, n := range *nodes {
		v := SeqFile{}
		jsonbody, _ := json.Marshal(n.Attributes)
		json.Unmarshal(jsonbody, &v)

		// fmt.Printf("%v\n", n.Attributes)
		// fmt.Printf("%v\n", string(jsonbody))
		// fmt.Printf("%v\t%v\n", i, v)

		// fmt.Printf("%v\t%s %s\t%s\t%v\t%v\n", i, n.Id, v.Project_id, v.Project, n.File.Name, n.File.Size)

	}
	return nodes, err
}

func (s Shock) SetRWD(node_id string, user string) (err error) {

	// adding user to acls
	// curl -X PUT http://<host>[:<port>]/node/<node_id>/acl/[ all | read | write | delete ]?users=<user-ids_or_uuids>
	url := fmt.Sprintf("%s/node/%s/acl/all?users=%s", s.URL, node_id, user)

	req, _ := http.NewRequest("PUT", url, nil)

	// req.Header.Set("Content-Type", "")
	req.Header.Add("Authorization", "mgrast "+s.Token)

	response, err := s.Client.Do(req)

	if err != nil {
		return
	}
	var body []byte
	body, err = ioutil.ReadAll(response.Body)

	fmt.Printf("Set acls: %s\n", body)

	return
}

func (s Shock) SetOwner(node_id string, user string) (err error) {

	// adding user to acls
	// curl -X PUT http://<host>[:<port>]/node/<node_id>/acl/[ all | read | write | delete ]?users=<user-ids_or_uuids>
	url := fmt.Sprintf("%s/node/%s/acl/owner?users=%s", s.URL, node_id, user)

	req, _ := http.NewRequest("PUT", url, nil)

	// req.Header.Set("Content-Type", "")
	req.Header.Add("Authorization", "mgrast "+s.Token)

	response, err := s.Client.Do(req)

	if err != nil {
		return
	}
	var body []byte
	body, err = ioutil.ReadAll(response.Body)

	fmt.Printf("Set acls: %s\n", body)

	return
}

func (s Shock) ComputeStats(node_id string) (err error) {

	// adding user to acls
	// curl -X PUT http://<host>[:<port>]/node/<node_id>/acl/[ all | read | write | delete ]?users=<user-ids_or_uuids>
	url := fmt.Sprintf("https://api.mg-rast.org/inbox/stats/%s", node_id)

	req, _ := http.NewRequest("GET", url, nil)

	// req.Header.Set("Content-Type", "")
	req.Header.Add("Authorization", "mgrast "+"VR8Lc4BuhbBiQ7QYR567awZd3") // user.Token

	response, err := s.Client.Do(req)

	if err != nil {
		return
	}
	var body []byte
	body, err = ioutil.ReadAll(response.Body)

	fmt.Printf("Computing stats: %s\n", body)

	return
}

func (s Shock) SetAttributes(node_id string, a Attributes) {

	// curl -X PUT -F "attributes=@<path_to_json>" http://<host>[:<port>]/node/<node_id>

	// marshal attributes to json
	j, err := json.Marshal(a)
	if err != nil {
		panic(err)
	}

	// fmt.Println(a)
	// fmt.Println("JSON: " + string(j))

	// Create request
	node_url := fmt.Sprintf("%s/node/%s", s.URL, node_id)
	// req, _ := http.NewRequest("PUT", node_url, bytes.NewBuffer(j))

	// New multipart writer.
	request_body := &bytes.Buffer{}
	writer := multipart.NewWriter(request_body)
	fw, err := writer.CreateFormField("attributes_str")
	_, err = io.Copy(fw, strings.NewReader(string(j)))
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	// Close multipart writer.
	writer.Close()

	req, _ := http.NewRequest("PUT", node_url, bytes.NewReader(request_body.Bytes()))
	// req, err := http.NewRequest("POST", "http://localhost:8080/employee", bytes.NewReader(body.Bytes()))

	// form := url.Values{}
	// form.Add("attributes_str", string(j))
	// req.PostForm = form

	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Add("Authorization", "mgrast "+s.Token)
	// req.Header.Set("Content-Length", strconv.FormatInt(string.(string(j)), 10))

	response, err := s.Client.Do(req)

	if response.StatusCode != http.StatusOK {
		log.Printf("Request failed with response code: %d", response.StatusCode)
	}
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	// Read response body
	var body []byte
	body, err = ioutil.ReadAll(response.Body)
	// fmt.Println(string(body))

	// Get node
	var e EnvelopeSingleNode
	err = json.Unmarshal(body, &e)

	// fmt.Printf("Response: %v\n", e)

	return
}

func (s Shock) CopyNode(node_id string) (node *Node, err error) {
	// url := s.URL + "/node/" + "?query&owner=ANL-SEQ-Core&" + query + "&offset=" + fmt.Sprint(offset) + "&limit=" + fmt.Sprint(limit)
	//project_id=121010_SN1035_0118_AC0YM6ACXX&project=PCH"
	// fmt.Printf("Copying %s\n", node_id)

	// Create multipart body
	request_body := &bytes.Buffer{}

	// Add data to body
	writer := multipart.NewWriter(request_body)
	fw, err := writer.CreateFormField("copy_data")
	_, err = io.Copy(fw, strings.NewReader(node_id))
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	writer.Close()

	node_url := fmt.Sprintf("%s/node", s.URL)

	req, _ := http.NewRequest("POST", node_url, bytes.NewReader(request_body.Bytes()))
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Add("Authorization", "mgrast "+s.Token)

	response, err := s.Client.Do(req)

	if err != nil {
		fmt.Printf("Error: %v", err)
		return
	}
	var body []byte
	body, err = ioutil.ReadAll(response.Body)

	if err != nil {
		fmt.Printf("Error: %v", err)
	} else {
		fmt.Println(string(body))
	}

	// var f interface{}
	var e EnvelopeSingleNode
	err = json.Unmarshal(body, &e)

	if err != nil {
		fmt.Printf("Error: %v", err)
	}

	// for i, n := range f.(map[string]interface{}) {
	node = &e.Data

	fmt.Printf("Parent: %s\tCopy: %s %s %s\n", node_id, node.Id, node.Type, node.File.Name)

	return node, err
}

func (s Shock) Ls(project_id string, project string, file string) {

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

	var q Query
	q.Query = query
	q.Limit = 50
	q.Offset = 0

	for {
		nodes, _ := s.Get(q)

		if len(*nodes) == 0 {
			break
		}

		for i, n := range *nodes {
			v := SeqFile{}
			jsonbody, _ := json.Marshal(n.Attributes)
			json.Unmarshal(jsonbody, &v)

			fmt.Printf("%v\t%s/%s/%v/%v\t%v\n", i, v.Project_id, v.Project, v.Sample, n.File.Name, n.File.Size)
		}

		q.Offset = q.Offset + q.Limit

	}

}
