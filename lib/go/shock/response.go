package shock

type Response struct {
	limit, offset, total_count int
	query                      Query
	client                     Shock
}
