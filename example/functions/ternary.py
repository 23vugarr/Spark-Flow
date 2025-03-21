def ternary(col_name, match, res1, res2):
    return f"CASE WHEN {col_name} = {match} THEN {res1} ELSE {res2} END" 