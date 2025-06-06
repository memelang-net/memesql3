#!/usr/bin/env python3

import sys
import os
import re
import glob
import psycopg2
from conf import DB


###############################################################################
#                           CONSTANTS & GLOBALS
###############################################################################

AID = {}

# Global dictionary to cache key->id mappings

GID = 999 # Default graph ID
G = 1 # Virtual graph for names of operators

I = {
	'['   : 2,
	']'   : 3,
	'|'   : 4,
	'=$'  : 5,
	'=f'  : 6,
	'=t'  : 7,
	'=g'  : 8,
	'=.'  : 9,
	'>'   : 10,
	'<'   : 11,
	'>='  : 12,
	'<='  : 13,
	'!='  : 14,
	';'   : 20,
	' '   : 21,
	'>>'  : 22,
	'qry' : 65536,
	'all' : 65537,
	'nam' : 65538,
	'key' : 65539,
	'tit' : 65540,
	'cor' : 1048576
}

# Lazy population for now
K = {value: key for key, value in I.items()}

START = 2

# Each operator and its meaning
FUNC, FORM, OUT = 0, 1, 2
A, R, B, C, Q, OR = 'A', 'R', 'B', 'C', 'Q', 'OR'
NULL	= 1		# Null
KEY		= 2		# Integer ID or string KEY
DECIMAL	= 3		# Floating point number
INTEGER	= 4		# Floating point number
STRING	= 5		# String
OPR = {
	I[';']  : [A, KEY, "\n"],
	I[' ']  : [A, KEY, False],
	I['>>'] : [A, KEY, False],
	I['[']  : [R, KEY, False],
	I[']']  : [B, KEY, False],
	I['=t'] : [Q, NULL, False],
	I['=f'] : [Q, NULL, False],
	I['=g'] : [Q, NULL, False],
	I['=$'] : [Q, STRING, '="'],
	I['=.'] : [Q, DECIMAL, '='],
	I['>']  : [Q, DECIMAL, False],
	I['<']  : [Q, DECIMAL, False],
	I['>='] : [Q, DECIMAL, False],
	I['<='] : [Q, DECIMAL, False],
	I['!='] : [Q, DECIMAL, False],
	I['|']  : [OR, INTEGER, False],
}

# For decode()
INCOMPLETE, SEMICOMPLETE, COMPLETE = 1, 2, 3
OPSTR = {
	'!'   : [INCOMPLETE, False],
	'>'   : [SEMICOMPLETE, I['>']],
	'<'   : [SEMICOMPLETE, I['<']],
	'='   : [SEMICOMPLETE, I['=.']],
	'=t'  : [COMPLETE, I['=t']],
	'=f'  : [COMPLETE, I['=f']],
	'=g'  : [COMPLETE, I['=g']],
	'!='  : [COMPLETE, I['!=']],
	'>='  : [COMPLETE, I['>=']],
	'<='  : [COMPLETE, I['<=']],
	'['   : [COMPLETE, I['[']],
	']'   : [COMPLETE, I[']']],
	';'   : [COMPLETE, I[';']],
	' '   : [COMPLETE, I[' ']],
	'>>'  : [COMPLETE, I['>>']],
	'|'   : [COMPLETE, I['|']],
}


###############################################################################
#                       MEMELANG STRINGING PROCESSING
###############################################################################

# Input: Memelang string "operator1operand1operator2operand2"
# Output: [operator1, operand1, operator2, operand2, ...]
def decode(memestr: str) -> list:

	memestr = re.sub(r'\s*//.*$', '', memestr, flags=re.MULTILINE).strip() # Remove comments
	if len(memestr) == 0: raise Exception("Error: Empty query provided.")

	tokens = [G, G]
	parts = re.split(r'(?<!\\)"', ';'+memestr)
	for p, part in enumerate(parts):

		# Quote
		if p%2==1:
			if OPR[tokens[-2]][FUNC] != Q: raise Exception('Errant quote')
			tokens[-2], tokens[-1] = I['=$'], part
			continue

		# Memelang code
		part = re.sub(r'[;\n]+', ';', part)					# Newlines are semicolons
		part = re.sub(r'\s+', ' ', part)					# Remove multiple spaces
		part = re.sub(r'\s*([#;!<>=\|]+)\s*', r'\1', part)	# Remove spaces around operators
		part = re.sub(r';+', ';', part)						# Remove multiple semicolons
		part = re.sub(r';+$', '', part)						# Remove ending ;

		# Split by operator characters
		strtoks = re.split(r'([#;\[\]\|!><=\s:])', part)
		tlen = len(strtoks)
		t = 0
		while t<tlen:
			strtok=strtoks[t]

			# Skip empty
			if len(strtok)==0: pass

			# Operator
			elif OPSTR.get(strtok):

				# We might want to rejoin two sequential operator characters
				# Such as > and =
				completeness, operator = OPSTR[strtok]
				if completeness!=COMPLETE:
					for n in (1,2):
						if t<tlen-n and len(strtoks[t+n]):
							if OPSTR.get(strtok+strtoks[t+n]):
								completeness, operator = OPSTR[strtok+strtoks[t+n]]
								t+=n
							break
					if completeness==INCOMPLETE: raise Exception(f"Invalid strtok {strtok}")

				tokens += [operator, None]

			# Key/Integer/Decimal
			else:
				if tokens[-1]!=None: raise Exception(f'Sequence error {tokens[-2]} {tokens[-1]} {strtok}')
				if not re.search(r'[a-zA-Z0-9]', strtok): raise Exception(f"Unexpected '{strtok}' in {memestr}")
				if OPR[tokens[-2]][FORM]==DECIMAL: tokens[-1] = float(strtok)
				elif re.match(r'-?[0-9]+', strtok): tokens[-1] = int(strtok)
				else: tokens[-1] = strtok

			t+=1

	return tokens


# Jump to next statement in tokens
def nxt(tokens: list, beg: int = 2) -> int:
	olen=len(tokens)
	if beg>olen-2: return -1
	elif tokens[beg]!=I[';']: raise Exception(f'Operator counting error at {beg} for {tokens[beg]}')

	end = beg
	while end<olen-2:
		end+=2
		if tokens[end]==I[';']: return end
	return olen


# Compare two Memelang token lists
# False is wildcard
# TO DO: This needs its own Metamemelang query language
def tokfit (atoks: list, btoks: list) -> bool:
	if len(atoks)!=len(btoks): return False
	for p, btok in enumerate(btoks):
		if btok==False: continue
		elif p%2==0 and isinstance(btok, str):
			if OPR[atoks[p]][FUNC]!=btok: return False
		elif atoks[p]!=btok: return False
	return True


# Input: list of integers [operator, operand]
# Output: one big integer
def pack(tokens: list) -> int:
	tlen = len(tokens)
	if tlen%2: raise ValueError('Odd token count')
	
	operator_bitmask = (1<<7)-1
	operand_bitmask = (1<<57)-1
	bigint = 1<<63 # Version 0001

	for t in range(tlen-1, 2, -2):
		operand, operator = tokens[t], tokens[t-1]
		
		if operand is None: operand=0
		elif OPR[operator][FORM]==DECIMAL: operand=int(operand*1000000)

		if not (0<=operator<127): raise ValueError(f'operator range {operator}')
		if not (-1<<56<=operand<1<<56): raise ValueError(f'operand range {operand}')
		bigint = (bigint<<64)|(((operator&operator_bitmask)<<57)|(operand&operand_bitmask))

	return bigint


# Input: one big integer
# Output: list of integers [operator, operand]
def unpack(bigint: int) -> list:
	if bigint<1<<63:raise ValueError
	pairs=[G, G]
	while bigint>1<<63:
		chunk = bigint&((1<<64)-1);
		bigint >>= 64
		operator = chunk>>57;
		operand = chunk&((1<<57)-1)
		if operand >= (1<<56): operand-=1<<57
		
		if operand==0: operand=None
		elif OPR[operator][FORM]==DECIMAL: operand=float(operand/1000000)

		pairs += [operator, operand]
	if bigint != (1<<63): raise ValueError('Version error')
	return pairs


# Input: tokens [operator1, operand1, operator2, operand2, ...]
# Output: Memelang string "operator1operand1operator2operand2"
def encode(tokens: list, fset={}) -> str:
	memestr = ''
	for o in range(START, len(tokens), 2):
		if o>START or tokens[o]!=I[';']: memestr += K[tokens[o]] if OPR[tokens[o]][OUT]==False else OPR[tokens[o]][OUT]
		if OPR[tokens[o]][FORM] == STRING: memestr += str(tokens[o+1]) + '"'
		elif OPR[tokens[o]][FORM] != NULL and tokens[o+1] is not None: memestr += str(tokens[o+1])
	return memestr


###############################################################################
#                        DATABASE HELPER FUNCTIONS
###############################################################################

def select(sql: str, params: list = []) -> list:
	with psycopg2.connect(f"host={DB['host']} dbname={DB['name']} user={DB['user']} password={DB['pass']}") as conn:
		cursor = conn.cursor()
		cursor.execute(sql, params)
		rows=cursor.fetchall()
		return [list(row) for row in rows]


def insert(sql: str, params: list = []):
	with psycopg2.connect(f"host={DB['host']} dbname={DB['name']} user={DB['user']} password={DB['pass']}") as conn:
		cursor = conn.cursor()
		cursor.execute(sql, params)


def aggnum(col: str = 'aid', agg: str = 'MAX', table: str = None) -> int:
	if not table: table=DB['table_meme']
	result = select(f"SELECT {agg}({col}) FROM {table}")
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


def selectin(cols: dict = {}, table: str = None) -> list:
	if not table: table=DB['table_meme']

	conds = []
	params = []

	for col in cols:
		conds.append(f"{col} IN ("+ ','.join(['%s'] * len(cols[col])) +")")
		params.extend(cols[col])

	if not conds: return []

	return select(f"SELECT DISTINCT * FROM {table} WHERE " + ' AND '.join(conds), params)


# Conbine SQL and parameters into a string
def morfigy(sql: str, params: list) -> str:
    for param in params:
        rep = param.replace("'", "''") if isinstance(param, str) else str(param)
        sql = sql.replace("%s", rep, 1)
    return sql


# Input: string "John Adams"
# Output: lowercase underscored string "john_adams"
def slugify(string: str) -> str:
	return re.sub(r'__+', '_', re.sub(r'[^a-z0-9]', '_', string.lower())).strip('_')


###############################################################################
#                           KEY <-> ID CONVERSIONS
###############################################################################

# Input list of key strings ['george_washington', 'john_adams']
# Load key->aids in I and K caches
# I['john_adams']=123
# K[123]='john_adams'
def identify(tokens: list, gids: list[int] = []) -> list:
	if not gids: gids = [GID]
	allaids=I
	for gid in gids:
		if not AID.get(gid): AID[gid]={}
		for q, a in AID[gid].items(): allaids.setdefault(q, a)

	tlen = len(tokens)
	if not tlen: return tokens

	lookups={}
	tokids=[G, gids[-1]]

	for t in range(START, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		if isinstance(operand, str) and OPR[operator][FORM]==KEY:
			operand=operand.lstrip('-')
			if not allaids.get(operand): lookups[operand]=1

	if lookups:
		rows=selectin({'qnt':lookups.keys(), 'rid':[I['nam']], 'bid':[I['key']], 'gid':gids}, DB['table_name'])
		for row in rows: AID[int(row[0])][row[4]] = int(row[1])

		# must keep gid order
		for gid in gids:
			for q, a in AID[gid].items(): allaids.setdefault(q, a)

	for t in range(START, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		tokids.append(operator)
		if operand is None: tokids.append(operand)
		elif isinstance(operand, str) and OPR[operator][FORM]==KEY:
			iid = allaids.get(operand.lstrip('-'),0)*(-1 if operand.startswith('-') else 1)
			if iid == 0: raise Exception(f"identify error {operand}")
			tokids.append(iid)
		else: tokids.append(operand)

	return tokids


def keyify(tokens: list, gids: list[int] = []) -> list:
	if not gids: gids = [GID]
	allstrs=K
	for gid in gids:
		if not AID.get(gid): AID[gid]={}
		for q, a in AID[gid].items(): allstrs.setdefault(a, q)

	tlen = len(tokens)
	if not tlen: return tokens

	lookups={}
	tokeys=[G, gids[-1]]

	for t in range(START, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		if operand is None: continue

		elif isinstance(operand, int) and OPR[operator][FORM]==KEY:
			operand=abs(operand)
			if not allstrs.get(operand): lookups[operand]=1

	if lookups:
		rows=selectin({'aid':lookups.keys(), 'rid':[I['nam']], 'bid':[I['key']], 'gid':gids}, DB['table_name'])
		for row in rows: AID[int(row[0])][row[4]] = int(row[1])

		# must keep gid order
		for gid in gids:
			for q, a in AID[gid].items(): allstrs.setdefault(a, q)

	for t in range(START, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		tokeys.append(operator)
		if operand is None: tokeys.append(operand)
		elif isinstance(operand, int) and OPR[operator][FORM]==KEY:
			sign=''
			if operand<0:
				sign='-'
				operand*=-1
			tokeys.append(sign+allstrs[operand])
		else: tokeys.append(operand)

	return tokeys


# Run decode() and identify()
def idecode(memestr: str, gids: list[int] = []) -> list:
	return identify(decode(memestr), gids)


# Run keyify() and encode()
def keyencode(tokens: list, gids: list[int] = []) -> str:
	return encode(keyify(tokens, gids))


###############################################################################
#                         MEMELANG -> SQL QUERIES
###############################################################################

# Input: tokens
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(tokens: list, gids: list[int] = [], fset={}) -> tuple[str, list]:
	if not gids: gids = [GID]

	joins=[{
		'inv' : False,
		'sel' : {A:True, R:True, B:False, Q:False},
		'whr' : {'gid': gids, C: I['=.']}
	}]

	olen=len(tokens)
	for o in range(0, olen, 2):
		operator, operand = tokens[o], tokens[o+1]
		func, form = OPR[operator][FUNC], OPR[operator][FORM]

		# Chained [R[R or ]B]B or [R][R
		if o>2 and (func == R or (func == B and OPR[tokens[o-2]][FUNC] == B)):
			joins.append({
				'inv' : False,
				'sel' : {},
				'whr' : {'gid': gids, C: I['=.']}
			})

		if func in (A,R,B):
			if isinstance(operand, int) and operand<=0: joins[-1]['inv']=True
			if operand is not None: joins[-1]['whr'][func]=abs(operand)
			joins[-1]['sel'][func]=True

		elif func == Q:
			joins[-1]['whr'][C]=operator
			if operand is not None: joins[-1]['whr'][Q]=operand

	# Always select last B=Q
	joins[-1]['sel'][B]=True
	joins[-1]['sel'][Q]=True

	froms, wheres, params = [], [], []
	aselect, select, fbcol = '', '', ''
	for m, join in enumerate(joins):
		inv = join['inv']
		tbl = DB['table_meme']
		acol = 'bid' if inv else 'aid'
		bcol = 'aid' if inv else 'bid'
		rcol = 'rid*-1' if inv else 'rid'
		lbcol = fbcol
		fbcol = bcol
		qpre = ''

		if join['whr'][C]==I['=$']: 
			cpr=' LIKE '          # String comparison
			qpre='"'              # Prepend QNT with a double quote
			tbl=DB['table_name']  # Change to name table
			fbcol='aid'          # forward the AID
		elif join['whr'][C]==I['=.']: cpr='='
		else: cpr=K[join['whr'][C]]

		# FROM table SELECT aid
		if m==0: 
			froms.append(f" FROM {tbl} m{m}")
			aselect=f"m{m}.{acol} as a0"
			select=f"concat_ws(' ', ';', m{m}.{acol}"
		# JOIN
		else: 
			froms.append(f" JOIN {tbl} m{m} ON m{m-1}.{lbcol}=m{m}.{acol}")

		# SELECT rid, bid, qnt
		select+=f", {I['[']}, m{m}.{rcol}"
		if join['sel'].get(B): select+=f", {I[']']}, m{m}.{bcol}"
		if join['sel'].get(Q): select+=f", COALESCE('{join['whr'][C]} {qpre}' || m{m}.qnt::text)"

		# WHERE gid
		if len(join['whr']['gid'])==1: wheres.append(f"m{m}.gid={int(join['whr']['gid'][0])}")
		else: wheres.append(f"m{m}.gid IN ("+','.join(str(int(gid)) for gid in join['whr']['gid'])+")")

		# WHERE aid, rid, bid, qnt
		for xfunc, xcpr, xcol in ((A,'=',acol),(R,'=','rid'),(B,'=',bcol),(Q,cpr,'qnt')): # harcode rid
			if join['whr'].get(xfunc):
				wheres.append(f"m{m}.{xcol}{xcpr}%s")
				params.append(join['whr'][xfunc])


	return ('SELECT '
		+ aselect + ('' if fset.get('aidselect') else f", {select}) AS arbq")
		+ ' '.join(froms)
		+ ' WHERE ' + (' AND '.join(wheres))
	), params


# Input: Memelang query string
# Output: SQL query string
def querify(tokens: list, gids: list[int] = []) -> tuple[str, list]:

	ctes, selects, params = [], [], []
	cte_beg, cte_end = 0, 0

	beg = 0
	end = START
	while (end := nxt(tokens, (beg := end)))>0: # Split by ;

		trues={}
		skip = False
		cte_beg = cte_end
		not_params = []
		not_where = ''
		ret_selects = []

		for o in range(beg, end, 2): # Split by ' '
			if OPR[tokens[o]][FUNC] == A and tokens[o+1] == I['qry']:
				skip=True

			elif o==end-2 or OPR[tokens[o+2]][FUNC]==A:
				if tokens[o] == I['=f']: # False
					qry_select, qry_params = selectify(tokens[beg:o+2], gids, {'aidselect':True})
					not_where += f" AND m0.aid NOT IN ({qry_select})"
					not_params.extend(qry_params)

				elif tokens[o] == I['=g']: # Get
					qry_select, qry_params = selectify(tokens[beg:o+2], gids)
					ret_selects.append(f"{qry_select} AND a0 IN (SELECT a0 FROM ZLAST)")
					params.extend(qry_params)

				elif not skip: # True or Quantity
					gnum = tokens[o+1] if tokens[o] == I['|'] else 1000+o
					if not trues.get(gnum): trues[gnum]=[]
					trues[gnum].append([beg, o+2])

				skip=False
				beg=o+2

		for gnum in trues:
			or_selects = []
			for beg1, end1 in trues[gnum]:
				qry_select, qry_params = selectify(tokens[beg1:end1], gids)

				if cte_end==cte_beg:
					qry_select += not_where
					qry_params.extend(not_params)

				else: qry_select+=f" AND m0.aid IN (SELECT a0 FROM z{cte_end})"

				or_selects.append(qry_select)
				params.extend(qry_params)

				# FIX LATER
				# Also get inverse for A query
				if (end1-beg1) == 2 and OPR[tokens[beg1]][FUNC] == A and tokens[beg1+1] is not None:
					qry_select, qry_params = selectify([I[';'], tokens[beg1+1]*-1], gids)
					or_selects.append(qry_select)
					params.extend(qry_params)
					qry_select, qry_params = selectify([I[';'], tokens[beg1+1], I['=$'], '%'], gids)
					or_selects.append(qry_select)
					params.extend(qry_params)

			cte_end += 1
			ctes.append(f"z{cte_end} AS ({' UNION '.join(or_selects)})")

		for cte_cnt in range(cte_beg, cte_end):
			ret_selects.append(f"SELECT arbq FROM z{cte_cnt+1}" + ('' if cte_cnt+1 == cte_end else f" WHERE a0 IN (SELECT a0 FROM ZLAST)"))

		selects.extend([ret_select.replace('ZLAST', f"z{cte_end}") for ret_select in ret_selects])

	sql = 'WITH ' + ', '.join(ctes) + " SELECT string_agg(arbq, ' ') AS arbq FROM (" + ' UNION '.join(selects) + ')'

	return sql, params


# Input: Memelang string
# Saves to DB
# Output: Memelang string
def put (memestr: str, gids: list[int] = []) -> str:
	meme_table=DB['table_meme']
	name_table=DB['table_name']

	if not gids: gids = [GID]
	gid=gids[-1]
	if gid not in AID: AID[gid]={}

	tokens = decode(memestr)
	olen = len(tokens)

	sqls = {meme_table:[], name_table:[]}
	params = {meme_table:[], name_table:[]}

	# NEW KEY NAMES

	newkeys = {}

	# Pull out string keys
	for o in range(START, olen, 2):
		operand = tokens[o+1]
		form = OPR[tokens[o]][FORM]

		if form == STRING: 
			if o>=8 and tokfit(tokens[o-6:o+2], [A, False, R, I['nam'], B, I['key'], I['=$'], False]):
				newkeys[tokens[o+1].lower()] = tokens[o-5]

		elif form == KEY and isinstance(operand, str):
			iid = AID[gid].get(operand.lstrip('-'),0)*(-1 if operand.startswith('-') else 1)
			if iid != 0: tokens[o+1]=iid
			else: 
				quo = tokens[o+1].lstrip('-').lower()
				if not newkeys.get(quo): newkeys[quo] = 0.5

	# Unique check keys
	rows=selectin({'gid':[gid], 'rid':[I['nam']], 'bid':[I['key']], 'qnt':newkeys.keys()}, DB['table_name'])
	for row in rows:
		quo=row[4]
		if newkeys.get(quo):
			if int(row[1]) == int(newkeys[quo]) or isinstance(newkeys[quo], float): newkeys.pop(quo, 0)
			else: raise Exception(f"Duplicate key {quo} for new {newkeys[quo]} and old {row[1]}")

	# Write new keys
	aidmax = aggnum('aid', 'MAX', name_table) or I['cor']
	for quo in newkeys:

		if re.search(r'[^a-z0-9_]', quo) or not re.search(r'[a-z]', quo):
			raise Exception(f'Invalid key {quo}')

		kid = int(newkeys[quo])
		if not kid:
			aidmax += 1
			kid = aidmax
		elif kid<=I['cor']: raise Exception(f'Invalid id number {kid}')

		AID[gid][quo]=kid
		sqls[name_table].append("(%s,%s,%s,%s,%s)")
		params[name_table].extend([gid, kid, I['nam'], I['key'], quo])

	# Swap missing keys for new IDs
	tokens=identify(tokens, gids)
	
	# NEW MEMES

	end=START
	while (end := nxt(tokens, (beg := end)))>0:
		if end-beg==0: continue

		# A[R]B ..
		elif tokfit(tokens[beg:beg+6], [A, False, R, False, B, False]):

			# Invert R
			if tokens[beg+3]<0:
				tokens[beg+3]*=-1
				tokens[beg+1], tokens[beg+5] = tokens[beg+5], tokens[beg+1]

			# A[R]B;
			if end == beg+6:
				params[meme_table].extend([gid, tokens[beg+1], tokens[beg+3], tokens[beg+5], None])
				sqls[meme_table].append('(%s,%s,%s,%s,%s)')	

			# A[nam]B = "String"
			elif tokens[beg+6] == I['=$']:
				if tokens[beg+5]!=I['key']:
					params[meme_table].extend([gid, tokens[beg+1], I['nam'], tokens[beg+5], tokens[beg+7]])
					sqls[meme_table].append('(%s,%s,%s,%s,%s)')

			# A[R]B=Q and A[R]B=t
			elif tokens[beg+6] in (I['=t'], I['=.']):
				params[meme_table].extend([gid, tokens[beg+1], tokens[beg+3], tokens[beg+5], tokens[beg+7]])
				sqls[meme_table].append('(%s,%s,%s,%s,%s)')

			else: raise Exception('Could not put tokens: ' + keyencode(tokens[beg:end], [gid]))

		# TO DO: WRITE TO IMPL TABLE

		else: raise Exception('Could not put tokens: ' + keyencode(tokens[beg:end], [gid]))

	for tbl in params:
		if params[tbl]: insert(f"INSERT INTO {tbl} VALUES " + ','.join(sqls[tbl]) + " ON CONFLICT DO NOTHING", params[tbl])

	return keyencode(tokens, [gid])


# Input: Memelang query string
# Output: Memelang results string
def query(memestr: str = None, gids: list[int] = []) -> str:
	if not gids: gids = [GID]

	tokens = idecode(memestr, gids)
	sql, params = querify(tokens, gids)
	res = select(sql, params)

	if not res or not res[0] or not res[0][0]: return ''

	tokens=[G, gids[-1]]

	strtoks=res[0][0].split()
	for tok in strtoks:
		if tok==';': tokens.append(I[';'])
		elif tok.startswith('"'): tokens.append(tok[1:])
		elif '.' in tok: tokens.append(float(tok))
		else: tokens.append(int(tok))

	return keyencode(tokens, gids)


# Input: Memelang query string
# Output: Integer count of resulting memes
def count(memestr: str, gids: list[int] = []) -> int:
	if not gids: gids = [GID]
	tokens = idecode(memestr, gids)
	sql, params = querify(tokens, gids)
	res=select(sql, params)
	return 0 if not res or not res[0] or not res[0][0] else res[0][0].count(';')


###############################################################################
#                                  CLI
###############################################################################

# Execute and output an SQL query
def cli_sql(qry_sql):
	rows = select(qry_sql, [])
	for row in rows: print(row)


# Execute and output a Memelang query
def cli_query(memestr):
	tokens = decode(memestr)
	print ("TOKENS:", tokens)
	print ("QUERY:", encode(tokens))

	tokens = idecode(memestr)
	sql, params = querify(tokens)
	full_sql = morfigy(sql, params)
	print(f"SQL: {full_sql}\n")

	# Execute query
	print(f"RESULTS:")
	print(query(memestr))
	print()
	print()


# Read a meme file and save it to DB
def cli_putfile(file_path):
	with open(file_path, 'r', encoding='utf-8') as f: print(put(f.read()))
	

# Test various Memelang queries
def cli_qrytest():
	queries=[
		'george_washington',
		' george_washington]',
		'george_washington[ ',
		'george_washington',
		'george_washington[',
		'george_washington[]',
		'george_washington[opt]',
		'george_washington[birth',
		'george_washington[birth]',
		'george_washington[birth[year',
		'george_washington[birth[year]',
		'george_washington[birth[year]adyear',
		'george_washington[birth[[',
		'george_washington[birth[[]',
		'george_washington[birth[][]',
		'martha_washington[-spouse]',
		'martha_washington[-spouse',
		'martha_washington[-spouse[birth[',
		'martha_washington[-spouse][birth[',
		']adyear',
		']adyear=t',
		'[year]adyear',
		'[birth[year]adyear',
		']adyear=1732',
		']adyear>=1900',
		'[year]adyear>1800',
		'[birth[year]adyear<=2000',
		'[spouse]',
		'[spouse] [child]',
		'[birth[year]adyear>=1800 [birth][year]adyear<1900',
		'[spouse [birth[year]adyear>=1900|1 [birth][year]adyear<1800|1',
		'[spouse [child [birth[year]adyear<1900',
		'george_washington; john_adams',
		'george_washington;; john_adams;; ; thomas_jefferson;',
	]
	errcnt=0

	for memestr in queries:
		print('Tokens:', decode(memestr))
		print('Query 1:', memestr)
		memestr2=memestr

		for i in range(2,4):
			memestr2 = keyencode(unpack(pack(idecode(memestr2)))).replace("\n", ";")
			print(f'Query {i}:', memestr2)

		tokens = idecode(memestr)
		sql, params = querify(tokens)
		print('SQL: ', morfigy(sql, params))
		
		c1=count(memestr)
		c2=count(memestr2)
		print ('First Count:  ', c1)
		print ('Second Count: ', c2)

		if not c1 or c1!=c2 or c1>200:
			print()
			print('*** COUNT ERROR ABOVE ***')
			errcnt+=1

		print()
	print("ERRORS:", errcnt)
	print()


# Add database and user
def cli_dbadd():
	commands = [
		f"sudo -u postgres psql -c \"CREATE DATABASE {DB['name']};\"",
		f"sudo -u postgres psql -c \"CREATE USER {DB['user']} WITH PASSWORD '{DB['pass']}'; GRANT ALL PRIVILEGES ON DATABASE {DB['name']} to {DB['user']};\"",
		f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {DB['name']} to {DB['user']};\""
	]

	for command in commands:
		print(command)
		os.system(command)


# Add database table
def cli_tableadd():
	commands = [
		f"sudo -u postgres psql -d {DB['name']} -c \"CREATE TABLE {DB['table_meme']} (gid BIGINT, aid BIGINT, rid BIGINT, bid BIGINT, qnt DOUBLE PRECISION, PRIMARY KEY (gid,aid,rid,bid)); CREATE INDEX {DB['table_meme']}_rid_idx ON {DB['table_meme']} (rid); CREATE INDEX {DB['table_meme']}_bid_idx ON {DB['table_meme']} (bid);\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"CREATE TABLE {DB['table_impl']} (gid BIGINT, rid1 BIGINT, bid1 BIGINT, cpr1 SMALLINT, qnt1 DOUBLE PRECISION, rid2 BIGINT, bid2 BIGINT, cpr2 SMALLINT, qnt2 DOUBLE PRECISION); CREATE UNIQUE INDEX {DB['table_impl']}_aid_idx ON {DB['table_impl']} (gid,rid1,bid1); CREATE INDEX {DB['table_impl']}_bid_idx ON {DB['table_impl']} (bid1);\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"CREATE TABLE {DB['table_name']} (gid BIGINT, aid BIGINT, rid BIGINT, bid BIGINT, qnt VARCHAR(511), PRIMARY KEY (gid,aid,rid,bid)); CREATE UNIQUE INDEX {DB['table_name']}_qnt_idx ON {DB['table_name']} (qnt);\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB['table_meme']} TO {DB['user']};\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB['table_name']} TO {DB['user']};\"",
	]

	for command in commands:
		print(command)
		os.system(command)


# Delete database table
def cli_tabledel():
	commands = [
		f"sudo -u postgres psql -d {DB['name']} -c \"DROP TABLE {DB['table_meme']};\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"DROP TABLE {DB['table_name']};\"",
	]
	for command in commands:
		print(command)
		os.system(command)

if __name__ == "__main__":
	LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

	cmd = sys.argv[1]
	if cmd == 'sql': cli_sql(sys.argv[2])
	elif cmd in ('query','qry','q','get','g'): cli_query(sys.argv[2])
	elif cmd in ('file','import'): cli_putfile(sys.argv[2])
	elif cmd in ('dbadd','adddb'): cli_dbadd()
	elif cmd in ('tableadd','addtable'): cli_tableadd()
	elif cmd in ('tabledel','deltable'): cli_tabledel()
	elif cmd == 'qrytest': cli_qrytest()
	elif cmd == 'install':
		cli_dbadd()
		cli_tableadd()
	elif cmd == 'reinstall':
		cli_tabledel()
		cli_tableadd()
		if len(sys.argv)>2 and sys.argv[2]=='-presidents': cli_putfile(os.path.join(LOCAL_DIR,'presidents.meme'))
	elif cmd in ('fileall','allfile'):
		files = glob.glob(LOCAL_DIR+'/*.meme') + glob.glob(LOCAL_DIR+'/data/*.meme')
		for f in files: cli_putfile(f)
	else: sys.exit("Invalid command")
