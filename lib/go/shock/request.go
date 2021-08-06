package shock

type Request struct {
	client Shock
	query  Query
}

func (s Shock) Request(query Query) *Request {
	var req Request
	req.client = s
	req.query = query
	return &req
}

func (r *Request) Next() *[]Node {
	nodes, _ := r.client.Get(r.query)
	r.query.Offset = r.query.Offset + r.query.Limit
	return nodes
}
