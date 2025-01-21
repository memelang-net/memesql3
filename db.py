import psycopg2
from conf import *

#### POSTGRES QUERIES #####

def select(query: str, params: list = []):
	conn_str = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
	with psycopg2.connect(conn_str) as conn:
		cursor = conn.cursor()
		cursor.execute(query, params)
		rows=cursor.fetchall()
		return [list(row) for row in rows]


def insert(query: str, params: list = []):
	conn_str = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
	with psycopg2.connect(conn_str) as conn:
		cursor = conn.cursor()
		cursor.execute(query, params)


def selnum(query: str):
	result = select(query)
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


def maxnum(col: str = 'aid', table: str = None):
	if not table: table=DB_TABLE_NAME
	result = select(f"SELECT MAX({col}) FROM {table}")
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


#### MEME SQL ####

# Input data memes [[AID, RID, BID, QNT]]
# Insert rows into DB
def memeput (memes: list, table: str = None):
	if not memes: return
	if not table: table=DB_TABLE_MEME

	sql_inserts = []
	for meme in memes:
		if len(meme)!=5: continue

		aid=int(meme[0])
		rid=int(meme[1])
		bid=int(meme[2])
		qnt=1 if meme[4]==1 else float(meme[4])

		if rid==NAM: continue
		if meme[3] is not None: continue
		if not aid: raise ValueError(f"Empty aid")
		if not rid: raise ValueError(f"Empty rid")
		if not bid: raise ValueError(f"Empty bid")

		if rid%2: 
			rid+=1
			sql_inserts.append(f"({bid}, {rid}, {aid}, {qnt})")
		else:
			sql_inserts.append(f"({aid}, {rid}, {bid}, {qnt})")

	if sql_inserts:
		insert(f"INSERT INTO {table} (aid, rid, bid, qnt) VALUES " + ','.join(sql_inserts) + " ON CONFLICT DO NOTHING")


# Input aid, bid, quo
# Delete one row from DB
def memecut (aid: int = 0, rid: int = 0, bid: int = 0, table: str = None):
	if not table: table=DB_TABLE_MEME
	insert(f"DELETE FROM {table} WHERE aid={aid} AND rid={rid} AND bid={bid}")


# Input aid (optional), rid (optional), bid (optional)
# Delete multiple rows from DB
def memewip (aid: int = 0, rid: int = 0, bid: int = 0, table: str = None):
	if not table: table=DB_TABLE_MEME
	conds = []
	if aid: conds.append(f"aid={aid}")
	if rid: conds.append(f"rid={rid}")
	if bid: conds.append(f"bid={bid}")

	if not conds: raise Exception('No conds')

	insert(f"DELETE FROM {table} WHERE " + ' AND '.join(conds), [])


# Input aid (optional), rid (optional), bid (optional)
# Select multiple rows from DB
def memeget (aid: int = 0, rid: int = 0, bid: int = 0, table=None):
	if not table: table=DB_TABLE_MEME
	conds = []
	if aid: conds.append(f"aid={aid}")
	if rid: conds.append(f"rid={rid}")
	if bid: conds.append(f"bid={bid}")

	if not conds: raise Exception('No conds')

	return select(f"SELECT aid, rid, bid, qnt FROM {table} WHERE " + ' AND '.join(conds), [])


#### NAME SQL ####

# Input name memes [[AID, NAM=90, BID, QUO]]
# Insert rows into DB
def nameput (names: list, table: str = None):
	if not names: return
	if not table: table=DB_TABLE_NAME

	sql_inserts = []
	quo_inserts = []
	for name in names:
		if len(name)!=5: continue

		aid=int(name[0])
		rid=int(name[1])
		bid=int(name[2])

		if rid!=NAM: continue
		if not aid and name[4]!=A2K[0]: raise ValueError(f"Empty aid")
		if not bid: raise ValueError(f"Empty bid")

		sql_inserts.append(f"(%s, %s, %s)")
		quo_inserts.append(aid)
		quo_inserts.append(bid)
		quo_inserts.append(name[4])

	if sql_inserts:
		insert(f"INSERT INTO {table} (aid, bid, quo) VALUES " + ','.join(sql_inserts) + " ON CONFLICT DO NOTHING", quo_inserts)


# Input aid, bid, quo
# Delete one row from DB
def namecut (aid: int, bid: int, quo: str, table: str = None):
	if not table: table=DB_TABLE_NAME
	insert(f"DELETE FROM {table} WHERE aid=%s AND bid=%s AND quo=%s", [int(aid), int(bid), quo])


# Input aid, bid (optional)
# Delete multiple rows from DB
def namewip (aid: int, bid: int, table: str = None):
	if not table: table=DB_TABLE_NAME
	if not aid: raise ValueError('aid')
	elif bid: insert(f"DELETE FROM {table} WHERE aid={aid} AND bid={bid}")
	else: insert(f"DELETE FROM {table} WHERE aid={aid}")


# Input aid, bid(optional)
# Output names from DB
def nameget(aid: int, bid: int = 0, table: str = None):
	if not table: table=DB_TABLE_NAME
	aid=int(aid)
	bid=int(bid)
	return select(f"SELECT aid, {NAM}, bid, quo FROM {table} WHERE aid={aid}" + (f" AND bid={bid}" if bid else ''))


# Input list of aids and list of bids
# Output names from DB
def namegets(aids: list = [], bids: list = [], quos: list = [], table: str = None):
	if not table: table=DB_TABLE_NAME

	conds = []
	params = []
	if bids: 
		conds.append(f"bid IN ("+ ','.join(['%s'] * len(bids)) +")")
		params.extend(map(int, bids))
	if aids: 
		conds.append(f"aid IN ("+ ','.join(['%s'] * len(aids)) +")")
		params.extend(map(int, aids))
	if quos: 
		conds.append(f"quo IN ("+ ','.join(['%s'] * len(quos)) +")")
		params.extend(map(str, quos))

	if not conds: raise Exception('No conds')

	return select(f"SELECT DISTINCT aid, {NAM}, bid, quo FROM {table} WHERE " + ' AND '.join(conds), params)


#### LOGI SQL ####

def logiput (logis: list, table: str = None):
	if not logis: return
	if not table: table=DB_TABLE_LOGI

	sql_inserts = []
	for logi in logis:
		sql_inserts.append('('+ ','.join(list(map(int, logi))) +')')

	if sql_inserts:
		db.insert(f"INSERT INTO {table} (v1, v2, opr, v3, v4) VALUES " + ','.join(sql_inserts) + " ON CONFLICT DO NOTHING")


def logicut (v1: int, v2: int, opr: int, v3: int, v4: int, table: str = None):
	if not table: table=DB_TABLE_LOGI
	db.insert(f"DELETE FROM {table} WHERE v1={v1} AND v2={v2} AND opr={opr} AND v3={v3} AND v4={v4}")


def logiwip (v: int, table: str = None):
	db.insert(f"DELETE FROM {table} WHERE v1={v} OR v2={v} OR v3={v} OR v4={v}")


def logigets(memes: list, table: str = None):
	if not table: table = DB_TABLE_LOGI

	wheres = []
	iwheres = []

	# Build WHERE clauses for any row in `memes` that matches `itm`
	for aid, rid, bid, qnt in memes:
		rid = int(rid)
		bid = int(bid)
		wheres.append(f"(v1={rid} AND v2={bid})")
		iwheres.append(f"(v3={rid} AND v4={bid})")

	# If nothing matched, no reason to run a query
	if not wheres: return

	# Construct the query safely in one expression
	query = (
		f"SELECT v1, v2, opr, v3, v4 FROM {table} WHERE " + ' OR '.join(wheres) +
		f" UNION " +
		f"SELECT v3, v4, opr-1, v1, v2 FROM {table} WHERE " + ' OR '.join(iwheres)
	)

	# Fetch data
	return db.select(query)