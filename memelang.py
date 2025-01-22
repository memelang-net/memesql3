import re
import html
import db
from conf import *

# Conbine SQL and parameters into a string
def morfigy(sql, params):
	new_query = sql
	for param in params:

		if isinstance(param, str): param = "'"+str(param).replace("'", "''")+"'"
		else: param = str(param)

		new_query = new_query.replace("%s", param, 1)
	return new_query


# Input: string "John Adams"
# Output: lowercase underscored string "john_adams"
def lowify(quo):
	return re.sub(r'__+', '_', re.sub(r'[^a-z0-9]', '_', quo.lower())).strip('_')


#### MEMELANG QUERY PARSING ####

# Input: Memelang string operator1operand1operator2operand2
# Output: [operator1, operator2, ...], [operand1, operand2, ...]
def delace(mqry):

	# Replace multiple spaces with a single space
	mqry = ' '.join(str(mqry).strip().split())

	# Remove spaces around operators
	mqry = re.sub(r'\s*([!<>=]+)\s*', r'\1', mqry)

	# Prepend zero before decimals, such as =.5 to =0.5
	mqry = re.sub(r'([<>=])(\-?)\.([0-9])', lambda m: f"{m.group(1)}{m.group(2)}0.{m.group(3)}", mqry)

	if mqry == '' or mqry == ';':
		raise Exception("Error: Empty query provided.")

	#if not mqry.endswith(';'): mqry+=';'

	mqry_chars = list(mqry)
	mqry_cnt = len(mqry_chars)

	operators = [OPER]
	operands = [MIX]
	operation = 0

	group_cnt = {I[':']: 0, I['.']: 0, I['=']: 0, I['[ba]']: 0}
	operator = None
	group = None
	opstr = ''

	i = 0
	while i < mqry_cnt:
		c = mqry_chars[i]
		operand = ''

		# Semicolon separates commands, space separates statements
		if c == ';' or c.isspace():

			# Assume is true
			if group_cnt[I['=']]==0:
				operation+=1
				operators.append(I['t'])
				operands.append(None)

			operation+=1
			operators.append(I[c])
			operands.append(None)

			operator = None
			group = None
			group_cnt = {I[':']: 0, I['.']: 0, I['=']: 0, I['[ba]']: 0}

			i += 1
			continue

		# Comment: skip until newline
		elif c == '/' and i+1 < mqry_cnt and mqry_chars[i+1] == '/':
			while i < mqry_cnt and mqry_chars[i] != '\n': i += 1
			i += 1
			continue

		# Operators
		elif c in OPR_CHR:

			# [xx]
			if c == '[':
				opstr = mqry[i:i+4]
				j=4

			else:
				opstr = ''
				j = 0
				while j < 3 and (i+j) < mqry_cnt:
					cc = mqry_chars[i+j]
					if cc in I and (j == 0 or OPR_CHR.get(cc) == 2):
						opstr += cc
						j += 1
					else: break

			operator = I[opstr]

			if operator not in OPR:
				raise Exception(f"Memelang parse error: Operator {opstr} not recognized at char {i} in {mqry}")

			# Short -> long
			if group_cnt[I['.']] > 0:
				if operator == I['.']: operator=I['[ba]']   # .R.R
				elif operator == I["'"]: operator=I['[bb]'] # 'R'R

			operation+=1
			operators.append(operator)
			operands.append(None)
			group = OPR[operator]['grp']
			group_cnt[group] += 1

			# error checks
			if group == I['.'] and group_cnt[I[':']] > 0:
				raise Exception(f"Memelang parse error: Errant R after B at char {i} in {mqry}")

			if group == I['='] and group_cnt[I['=']] > 1:
				raise Exception(f"Memelang parse error: Extraneous equality operator at char {i} in {mqry}")

			i += j
			continue

		# Double-quote string ="George Washtingon's Horse \"Blueskin\""
		elif c == '"':
			if operator != I['=']:
				raise Exception(f"Errant quote at char {i} in {mqry}")

			while i < mqry_cnt-1:
				i += 1
				ch = mqry_chars[i]
				if ch=='\\':
					i+=1
					operand += mqry_chars[i]
				elif ch=='"':
					i+=1
					break
				else:
					operand += ch

			operation+=1
			operators.append(I['$'])
			operands.append(operand)
			operator = None
			group = None
			continue

		# String/number following equal sign
		elif group == I['=']:

			while i < mqry_cnt and re.match(r'[a-z0-9_\.\-]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			if operand in ('t','f','g'):
				if operator != I['=']: raise Exception(f"Memelang parse error: {operand} not after =")

				operators[operation]=I[operand]
		
			# =tn for or-group
			elif operand.startswith('t'):
				if operator != I['=']: raise Exception(f"Memelang parse error: {operand} not after =")

				tm = re.match(r't(\d+)$', operand)
				if tm:
					operators[operation]=I['t']
					operation+=1
					operators.append(I['or'])
					operands.append(int(tm.group(1)))
				else: raise Exception(f"Memelang parse error: Unrecognized =Q at char {i} in {mqry}")

			# floating point number
			else:
				try:
					operation+=1
					operators.append(I['#'])
					operands.append(float(operand))
				except ValueError:
					raise Exception(f"Memelang parse error: Malformed number {operand} at char {i} in {mqry}")

			operator = None
			group = None
			continue

		else:
			while i < mqry_cnt and re.match(r'[a-z0-9_]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			# A string
			if group is None:
				operation+=1
				operators.append(I['@'])
				operands.append(operand)

			# String following R or B
			elif group in (I['.'], I[':']):
				operands[operation]=operand

			# String following [xx] is .R
			elif group == I['[ba]']:
				operation+=1
				operators.append(I['.'])
				operands.append(operand)

			else:
				raise Exception(f"Memelang parse error: Unexpected character '{mqry_chars[i]}' at char {i} in {mqry}")

			operator = None
			group = None
			continue

	return operators, operands


# Input: operators, operands
# Output: Memelang string operator1operand1operator2operand2
def interlace(operators, operands, interlace_set={}):
	mqry = ''

	if interlace_set.get('html'):
		mqry+='<code class="meme">'

	for i,operator in enumerate(operators):
		if i==0: continue
		opstr = OPR[operator]['shrt'] if interlace_set.get('short') else OPR[operator]['long']
		operand = operands[i]

		# Special cases
		if operator == I['#']:
			if '.' not in str(operand):
				operand = str(operand) + '.0'

		elif operator == I[';'] and interlace_set.get('newline'):
			opstr+="\n"

		# Append the interlaced expression
		if interlace_set.get('html'):
			if opstr:
				mqry += html.escape(opstr)
			if operand is not None:
			  mqry += '<var class="v' + str(operator) + '">' + html.escape(str(operand)) + '</var>'
		else:
			mqry += opstr + str(operand)

	if interlace_set.get('html'):
		mqry+='</code>'

	return mqry


# Input: operators, operands
# Output [[[operator, operator], [operand, operand]]]
def cmdify(operators: list, operands: list, cmdify_set={}, table=DB_TABLE_MEME):

	if operators[-1]!=I[';']:
		operators.append(I[';'])
		operands.append(None)

	cmds = []
	cmd = []
	state = [[], []]

	for i,operator in enumerate(operators):
		if i==0: continue
		if operator in (I[';'], I[' ']):
			if state[0]:

				# B'R:A -> A.R:B
				if cmdify_set.get('inverse') and state[0][:3] == [I['@'],I["'"],I[':']]:
					state[0][1]=I['.']
					state[1][0], state[1][2] = state[1][2], state[1][0]

				cmd.append(state)
				state = [[], []]

			if operator==I[';']:
				if cmd:
					cmds.append(cmd)
					cmd = []
		else:
			state[0].append(operator)
			state[1].append(operands[i])

	return cmds



#### MEMELANG-SQL CONVERSION ####

# Input: Memelang query string
# Output: SQL query string
def querify(mqry: str, meme_table=None, name_table=None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if name_table is None: name_table=DB_TABLE_NAME

	operators, operands = delace(mqry)

	if name_table: 
		operands = identify(operands, name_table)
		missings = [x for x in operands if isinstance(x, str)]
		if missings:
			raise Exception("Unknown keys: " + ", ".join(missings))

	cmds = cmdify(operators, operands)

	queries = []
	params = []

	for cmd in cmds:
		sql, val = subquerify(cmd, meme_table)
		queries.append(sql)
		params.extend(val)

	return [' UNION '.join(queries), params]


# Input: One mcmd memelang cmd array
# Output: One SQL query string
def subquerify(cmd: list, table='meme'):
	qry_set = {'all': False}
	true_groups = {}
	false_group = []
	get_statements = []
	or_groups = {}
	true_cnt = 0
	or_cnt = 0
	false_cnt = 0

	# Group statements logically
	for statement in cmd:
		if statement[0][0]==I['@'] and statement[1][0]==I['qry']:
			qry_set[statement[1][1]]=True
			continue

		# Trim trailing semi-colon
		if statement[0][-1]==I[';']:
			statement[0].pop()
			statement[1].pop()

		last_operator = statement[0][-1] if statement else None
		last_operand = statement[1][-1] if statement else None
		if not last_operator: continue

		# Handle =f (false)
		if last_operator == I['='] and last_operand == I['f']:
			false_cnt += 1
			# all but last mexpression
			false_group.append(statement)
			continue

		# Handle =g (get)
		if last_operator == I['='] and last_operand == I['g']:
			get_statements.append(statement)
			continue

		# Handle =tn (OR groups)
		if last_operator == I['or']:
			or_cnt += 1
			if not or_groups.get(last_operand):
				or_groups[last_operand]=[]
			or_groups[last_operand].append(statement)
			continue

		# Default: Add to true conditions
		if last_operator >= I['=']: tg=interlace(statement[0][:-1], statement[1][:-1])
		else: tg=interlace(statement[0], statement[1])

		if not true_groups.get(tg): true_groups[tg]=[]
		true_groups[tg].append(statement)
		true_cnt += 1

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and true_cnt == 0 and false_cnt == 0 and or_cnt == 0:
		return [f"SELECT * FROM {table}", []]

	params = []
	cte_sqls = []
	cte_outs = []
	sql_outs = []
	cte_cnt = -1

	# Process AND conditions (true_groups)
	for true_group in true_groups.values():
		wheres = []
		cte_cnt += 1
		# Each bid_group is a list of mstates
		for statement in true_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table)
			if not wheres:
				wheres.append(where_sql)
				params.extend(qry_params)
			else:
				wheres.append(where_sql[0:where_sql.find('qnt')-4])
				params.extend(qry_params[:-1])

		# If not the first CTE, link it to previous CTE
		if cte_cnt > 0:
			wheres.append(f"{select_sql[:6]} IN (SELECT aid FROM z{cte_cnt-1})")

		cte_sqls.append(f"z{cte_cnt} AS (SELECT {select_sql} {from_sql} WHERE {' AND '.join(wheres)})")
		cte_outs.append((cte_cnt, qry_depth))

	# Process OR groups
	# Each key in or_groups is an integer (the tn), or_groups[key] is a list of mstates
	for or_group in or_groups.values():
		cte_cnt += 1
		max_depth = 0
		or_selects = []
		for statement in or_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table)
			max_depth = max(max_depth, qry_depth)
			
			if cte_cnt > 0:
				where_sql += f" AND m0.aid IN (SELECT a0 FROM z{cte_cnt-1})"
			
			or_selects.append(f"SELECT {select_sql} {from_sql} WHERE {where_sql}")
			params.extend(qry_params)
		
		cte_sqls.append(f"z{cte_cnt} AS ({' UNION '.join(or_selects)})")
		cte_outs.append((cte_cnt, max_depth))

	# Process NOT conditions (false_group)
	if false_cnt:
		if true_cnt < 1:
			raise Exception('A query with a false statement must contain at least one non-OR true statement.')

		wheres = []
		for statement in false_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table, True)
			wheres.append(f"aid NOT IN (SELECT {select_sql} {from_sql} WHERE {where_sql})")
			params.extend(qry_params)

		fsql = f"SELECT aid FROM z{cte_cnt} WHERE " + ' AND '.join(wheres)
		cte_cnt += 1
		cte_sqls.append(f"z{cte_cnt} AS ({fsql})")


	# select all data related to the matching As
	if qry_set.get(I['all']):
		sql_outs.append(f"SELECT aid as a0, rid as r0, bid as b0, qnt as q0 FROM {table} m0 WHERE m0.aid IN (SELECT a0 FROM z{cte_cnt})")
		sql_outs.append(f"SELECT bid AS a0, rid{INVERSE} AS r0, aid AS b0, qnt AS q0 FROM {table} m0 WHERE m0.bid IN (SELECT a0 FROM z{cte_cnt})")

	else:
		for statement in get_statements:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table)
			sql_outs.append(f"SELECT {select_sql} {from_sql} WHERE {where_sql} AND m0.aid IN (SELECT a0 FROM z{cte_cnt})")
			params.extend(qry_params)

	for zmNum in cte_outs:
		zNum, mNum = zmNum

		cWhere=[];
		if zNum < cte_cnt:
			cWhere.append(f"a0 IN (SELECT a0 FROM z{cte_cnt})")

		m=0;
		while mNum>=m:
			#if m>0:
				#cWhere.append(f"a{m} IS NOT NULL AND r{m} NOT LIKE '?%'")

			sql_outs.append(f"SELECT DISTINCT a{m}, r{m}, b{m}, q{m} FROM z{zNum}" + ('' if len(cWhere)==0 else ' WHERE '+' AND '.join(cWhere) ))
			m+=1

	return ['WITH ' + ', '.join(cte_sqls) + ' ' + ' UNION '.join(sql_outs), params]


# Input: One Memelang statement array
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(statement, table='meme', aidOnly=False):

	params = []
	wheres = []
	joins = [f"FROM {table} m0"]
	selects = ['m0.aid AS a0','m0.rid AS r0','m0.bid AS b0','m0.qnt AS q0']
	m = 0
	opr='!='
	qnt='0'

	for i, operator in enumerate(statement[0]):
		operand = statement[1][i]

		# A
		if operator == I['@']:
			wheres.append(f'm{m}.aid=%s')
			params.append(operand)

		# R
		elif operator == I['.']:
			if operand is not None:
				wheres.append(f'm{m}.rid=%s')
				params.append(operand)

		# RI
		elif operator == I["'"]:
			# flip the prior A to a B
			selects[0] = f'm{m}.bid AS a{m}'
			selects[1] = f"m{m}.rid{INVERSE} AS r{m}"
			selects[2] = f'm{m}.aid AS b{m}'
			if i > 0:
				# the previous is presumably m0.aid=A
				wheres[0] = f'm{m}.bid=%s'
				params[0] = str(statement[1][i-1])

			if operand is not None:
				wheres.append(f'm{m}.rid=%s')
				params.append(operand)

		# B
		elif operator == I[':']:
			# inverse if previous was RI or BB
			if i > 0 and statement[0][i-1] in (I["'"], I['[bb]']):
				wheres.append(f'm{m}.aid=%s')
				params.append(operand)
			else:
				wheres.append(f'm{m}.bid=%s')
				params.append(operand)

		# equality operators
		elif operator >= I['='] and operator <= I['>']:
			opr = K[operator] 

		# decimal value
		elif operator == I['#']:
			if not opr: raise Exception('opr dec')
			qnt = float(operand)

		# is true
		elif operator == I['t']:
			opr='!='
			qnt='0'

		# is false
		elif operator == I['f']:
			opr='='
			qnt='0'


		# JOINS (BA, BB, RA, RB)
		else:
			lm = m
			m += 1

			wheres.append(f"m{lm}.qnt{NOTFALSE}")

			if operator == I['[ba]']:
				joins.append(f"JOIN {table} m{m} ON {selects[-2][:6]}=m{m}.aid")
				selects.append(f"m{m}.aid AS a{m}")
				selects.append(f"m{m}.rid AS r{m}")
				selects.append(f"m{m}.bid AS b{m}")
				selects.append(f"m{m}.qnt AS q{m}")
			elif operator == I['[bb]']:
				joins.append(f"JOIN {table} m{m} ON {selects[-2][:6]}=m{m}.bid")
				selects.append(f"m{m}.bid AS a{m}")
				selects.append(f"m{m}.rid{INVERSE} AS r{m}")
				selects.append(f"m{m}.aid AS b{m}")
				selects.append(f"(CASE WHEN m{m}.qnt = 0 THEN 0 ELSE 1 / m{m}.qnt END) AS q{m}")
			else:
				raise Exception('Error: unknown operator')

	# last qnt condition
	wheres.append(f"m{m}.qnt{opr}{qnt}")

	if aidOnly: selects = ['m0.aid AS a0']

	return [
		', '.join(selects),
		' '.join(joins),
		' AND '.join(wheres),
		params,
		m
	]


#### KEY-ID CONVERSION ####

# Input list of key strings ['george_washington', 'john_adams']
# Load key->aids in I and K caches
# I['john_adams']=123
# K[123]='john_adams'
def aidcache(keys, table=DB_TABLE_NAME):
	uncached_keys = [key for key in keys if key not in I]

	if not uncached_keys: return

	rows=db.namegets([], [KEY], uncached_keys, table)

	for row in rows:
		I[row[3]] = int(row[0])
		K[int(row[0])] = row[3]


# Input value is a list of strings ['a', 'b', 'c', 'd']
# Load key->aid
# Return the data with any keys with ids
def identify(keys: list, table=DB_TABLE_NAME):
	ids = []

	if not keys: return ids

	aidcache([key for key in keys if isinstance(key, str) and not key.isdigit()])

	for key in keys:
		if not isinstance(key, str): ids.append(key)
		elif key.isdigit(): ids.append(int(key))
		elif I.get(key): ids.append(I[key])
		else: ids.append(key)

	return ids


def identify1(val, table=DB_TABLE_NAME):
	ids = identify([val], table)
	return ids[0] if isinstance(ids[0], int) else False


# Input value is a list of ints [123,456,789]
# Load aid->key
# Return the data with any aids replaced with keys
def namify(operands: list, bids: list, table=DB_TABLE_NAME):
	missings=[]

	output = {}
	for bid in bids:
		output[bid]=[bid]

	matches = []
	for i,operand in enumerate(operands):
		if isinstance(operand, int) or (isinstance(operand, str) and operand.isdigit()):
			operands[i] = int(operands[i])
			matches.append(operands[i])

	names = db.namegets(matches, bids)

	namemap = {}
	for name in names:
		if not namemap.get(name[0]): namemap[int(name[0])]={}
		namemap[int(name[0])][int(name[2])]=name[3]

	for i,operand in enumerate(operands):
		if i==0: continue
		for bid in bids:
			if isinstance(operand, int):
				if namemap.get(operand) and namemap[operand].get(bid): output[bid].append(namemap[operand][bid])
				else: output[bid].append(False)
			else:
				output[bid].append(operand)

	return list(output.values())


# Input a Memelang query string
# Replace keys with aids
# Execute in DB
# Return results (optionally replacing aids with keys with statement "qry.nam:key=1")
def get(mqry, meme_table=DB_TABLE_MEME, name_table=DB_TABLE_NAME):
	output=[[OPER], [ID]]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, meme_table)	
	memes = db.select(sql, params)

	for meme in memes:
		ops = FLOT_OPS + [I[';']]
		meme = [int(meme[0]), int(meme[1]), int(meme[2]), None, float(meme[3]), None]
		
		if meme[1]%2:
			meme[1] += 1
			ops[1] = I["'"]

		if meme[4] in (0,1):
			ops[4] = meme[4]

		output[0].extend(ops)
		output[1].extend(meme)

	if namekeys:
		names = namify(output[1], namekeys, name_table)
		output.extend(names)

	return output


# Return meme count of above results
def count(mqry, meme_table=DB_TABLE_MEME, name_table=DB_TABLE_NAME):
	sql, params = querify(mqry, meme_table)
	return len(db.select(sql, params))


# Input meme array
# Write to DB
def put (operators: list, operands: list, meme_table=DB_TABLE_MEME, name_table=DB_TABLE_NAME):
	if not operators: return

	# Load IDs
	aidcache(operands)

	missings={}
	key_memes=[]
	suboperators=[]
	suboperands=[]
	for i, operator in enumerate(operators):
		if i==0: continue
		elif operator == I[' ']: raise Exception('space')

		elif operator != I[';']:
			operand=operands[i]

			# Missing keys with no associated ID
			if OPR[operator]['frm']=='aid':
				if isinstance(operand, int): pass
				elif isinstance(operand, str) and operand.isdigit(): operand=int(operand)
				elif I.get(operand): operand=I[operand]
				elif operator in (I['.'],I["'"]): missings[operand]=-1
				elif not missings.get(operand): missings[operand]=1

			suboperators.append(operator)
			suboperands.append(operand)

		# Keys with associated ID
		else:
			if suboperators==NAME_OPS:
				if suboperands[2]==KEY:
					missings[suboperands[4]]=0
					key_memes.append([int(suboperands[0]), NAM, KEY, None, suboperands[4]])

			suboperators=[]
			suboperands=[]

	# Missing keys with no associated ID
	if missings:
		aid = db.maxnum('aid', name_table) or I['cor']
		for key, val in missings.items():
			aid +=1
			if val==0: continue
			if val==-1 and aid%2: aid+=1
			key_memes.append([aid, NAM, KEY, None, key])

	# Write keys and reload
	if key_memes:
		db.nameput(key_memes)
		aidcache(operands)

	# Pull out names and trues
	name_memes=[]
	true_memes=[]
	suboperators=[]
	suboperands=[]
	for i, operator in enumerate(operators):
		if i==0: continue

		elif operator != I[';']:
			operand=operands[i]
			if OPR[operator]['frm']=='aid':
				if isinstance(operand, int): pass
				elif isinstance(operand, str) and operand.isdigit(): operand=int(operand)
				elif I.get(operand): operand=I[operand]
				else: raise Exception(f"missing {operand}")

			suboperators.append(operator)
			suboperands.append(operand)

		else:
			if suboperators==NAME_OPS:
				if suboperands[2]!=KEY: name_memes.append(suboperands)
			elif suboperators==TRUE_OPS: true_memes.append(suboperands+[TRUQNT])
			elif suboperators==FLOT_OPS: true_memes.append(suboperands)
			else: raise Exception(f"Unknown operators: "+ ' '.join(suboperators))

			suboperators=[]
			suboperands=[]

	if name_memes: db.nameput(name_memes)
	if true_memes: db.memeput(true_memes)

	return operators, operands


# Remove name statement from query
def dename(s: str):
	terms = re.split(r'\s+', s)
	extracted_terms = []
	remaining_terms = []

	pattern = re.compile(r'^([a-z0-9_]+)?\.(nam)(?:\:([a-z0-9_]+))?(?:=([0-9]+))?$')

	for term in terms:
		m = pattern.match(term)
		if m: extracted_terms.append(m.groups()[2])
		else: remaining_terms.append(term)

	nameaids = identify(list(set(extracted_terms)))

	# Reconstruct the remaining string
	remaining_string = ' '.join(remaining_terms)
	return remaining_string, nameaids


#### MEME FILE ####

def read (file_path):
	output = [[OPER],[MIX]]
	with open(file_path, 'r', encoding='utf-8') as f:
		for ln, line in enumerate(f, start=1):

			if line.strip() == '' or line.strip().startswith('//'):
				continue

			line = re.sub(r'\s*//.*$', '', line, flags=re.MULTILINE)

			operators, operands = delace(line)

			if len(operators)<2: continue

			# End with semi colon
			elif operators[-1]!=I[';']:
				operators.append(I[';'])
				operands.append(None)
			
			output[0].extend(operators[1:])
			output[1].extend(operands[1:])

	return output[0], output[1]


def write (file_path, operators: list, operands: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(interlace(operators, operands, {'newline':True}))