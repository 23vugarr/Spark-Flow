from sparkscr.core.QueryBuilder import QueryBuilder

qbuilder = QueryBuilder("./tests")

sch = qbuilder.read_sql_jinja("test.sql")
print(sch)
print(sch.query)

# wth = qbuilder.read_sql_file("./tests/test.sql")
# print(wth)