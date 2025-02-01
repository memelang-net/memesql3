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
	if not table: table=DB_ALRBEQ
	result = select(f"SELECT MAX({col}) FROM {table}")
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


# Input aid, bid, str
# Delete one row from DB
def memecut (aid: int = 0, rid: int = 0, bid: int = 0, table: str = None):
	if not table: table=DB_ALRBEQ
	insert(f"DELETE FROM {table} WHERE aid={aid} AND rid={rid} AND bid={bid}")


# Input aid (optional), rid (optional), bid (optional)
# Delete multiple rows from DB
def memewip (aid: int = 0, rid: int = 0, bid: int = 0, table: str = None):
	if not table: table=DB_ALRBEQ
	conds = []
	if aid: conds.append(f"aid={aid}")
	if rid: conds.append(f"rid={rid}")
	if bid: conds.append(f"bid={bid}")

	if not conds: raise Exception('No conds')

	insert(f"DELETE FROM {table} WHERE " + ' AND '.join(conds), [])


# Input aid (optional), rid (optional), bid (optional)
# Select multiple rows from DB
def memeget (aid: int = 0, rid: int = 0, bid: int = 0, table=None):
	if not table: table=DB_ALRBEQ
	conds = []
	if aid: conds.append(f"aid={aid}")
	if rid: conds.append(f"rid={rid}")
	if bid: conds.append(f"bid={bid}")

	if not conds: raise Exception('No conds')

	return select(f"SELECT aid, rid, bid, NULL, qnt FROM {table} WHERE " + ' AND '.join(conds), [])


# Input aid, bid, str
# Delete one row from DB
def namecut (aid: int, bid: int, string: str, table: str = None):
	if not table: table=DB_ALRBEQ
	insert(f"DELETE FROM {table} WHERE aid=%s AND bid=%s AND str=%s", [int(aid), int(bid), string])


# Input aid, bid (optional)
# Delete multiple rows from DB
def namewip (aid: int, bid: int, table: str = None):
	if not table: table=DB_ALRBEQ
	if not aid: raise ValueError('aid')
	elif bid: insert(f"DELETE FROM {table} WHERE aid={aid} AND bid={bid}")
	else: insert(f"DELETE FROM {table} WHERE aid={aid}")


# Input aid, bid(optional)
# Output names from DB
def nameget(aid: int, bid: int = 0, table: str = None):
	if not table: table=DB_ALRBEQ
	aid=int(aid)
	bid=int(bid)
	return select(f"SELECT aid, {NAM}, bid, str FROM {table} WHERE aid={aid}" + (f" AND bid={bid}" if bid else ''))


# Input list of aids and list of bids
# Output names from DB
def namegets(aids: list = [], bids: list = [], strings: list = [], table: str = None):
	if not table: table=DB_ABS

	conds = []
	params = []
	if bids: 
		conds.append(f"bid IN ("+ ','.join(['%s'] * len(bids)) +")")
		params.extend(map(int, bids))
	if aids: 
		conds.append(f"aid IN ("+ ','.join(['%s'] * len(aids)) +")")
		params.extend(map(int, aids))
	if strings: 
		conds.append(f"str IN ("+ ','.join(['%s'] * len(strings)) +")")
		params.extend(map(str, strings))

	if not conds: raise Exception('No conds')

	return select(f"SELECT DISTINCT aid, bid, str FROM {table} WHERE " + ' AND '.join(conds), params)
