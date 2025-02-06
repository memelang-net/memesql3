from conf import *
from memelang import *
import sys
import os
import re
import glob
import memelang

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Execute and output an SQL query
def sql(qry_sql):
	rows = memelang.select(qry_sql, [])
	for row in rows:
		print(row)


# Search for memes from a memelang query string
def qry(mqry):
	sql, params = memelang.querify(mqry, DB_TABLE_MEME, False)
	params = memelang.identify(params)
	full_sql = memelang.morfigy(sql, params)

	print(f"\nSQL: {full_sql}\n")

	# Execute query
	memes = memelang.get(mqry+' qry.nam:key=1')
	memeprint(memes[0], memes[2])


# Read a meme file and save it
def putfile(file_path):
	operators, operands = memelang.read(file_path)
	operators, operands = memelang.put(operators, operands)
	memeprint(operators, operands)


#### DB ADMIN ####

# Add database and user
def dbadd():
	commands = [
		f"sudo -u postgres psql -c \"CREATE DATABASE {DB_NAME};\"",
		f"sudo -u postgres psql -c \"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}'; GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} to {DB_USER};\"",
		f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} to {DB_USER};\""
	]

	for command in commands:
		print(command)
		os.system(command)


# Add database table
def tableadd():
	commands = [
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_MEME} (val DECIMAL(20,6), oid SMALLINT, aid BIGINT, cid BIGINT, rid BIGINT, bid BIGINT, eid SMALLINT, wal DECIMAL(20,6)); CREATE UNIQUE INDEX {DB_TABLE_MEME}_alrb_idx ON {DB_TABLE_MEME} (aid,cid,rid,bid); CREATE INDEX {DB_TABLE_MEME}_rid_idx ON {DB_TABLE_MEME} (rid); CREATE INDEX {DB_TABLE_MEME}_bid_idx ON {DB_TABLE_MEME} (bid);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_NAME} (aid BIGINT, bid BIGINT, str VARCHAR(511)); CREATE INDEX {DB_TABLE_NAME}_aid_idx ON {DB_TABLE_NAME} (aid); CREATE INDEX {DB_TABLE_NAME}_bid_idx ON {DB_TABLE_NAME} (bid); CREATE INDEX {DB_TABLE_NAME}_str_idx ON {DB_TABLE_NAME} (str);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_TABLE_MEME} TO {DB_USER};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_TABLE_NAME} TO {DB_USER};\"",
	]

	for command in commands:
		print(command)
		os.system(command)


# Delete database table
def tabledel():
	commands = [
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_TABLE_MEME};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_TABLE_NAME};\"",
	]

	for command in commands:
		print(command)
		os.system(command)


def logitest():
	operators, operands = memelang.delace('a]rz:bz=1;a]rx:bx=1;rx[bx]ry:by=t;rz[bz]rj')
	print(operators, operands)
	memelang.expand(operators, operands)
	print(operators, operands)
	memelang.logify(operators, operands)
	print(memelang.interlace(operators, operands,{'newline':True}))



def memeprint(operators, operands):
	found = False
	length = len(operators)

	br = f"+{'-' * 25}+{'-' * 25}+{'-' * 25}+"
	print(f"{br}\n| {'A':<23} | {'D':<23} | {'B=V':<23} |\n{br}")

	cmds = memelang.cmdify(operators, operands)

	for cmd in cmds:
		for suboperators, suboperands in cmd:
			if suboperators[:5]==TACRB and suboperands[2] in (I['is'], 'is', I['of'], 'of'):
				found = True
				meme=list(map(str, suboperands))

				if suboperators[5]==I['D=I']: bq=meme[4]
				elif suboperators[5]==I['D=S']: bq='"'+meme[5]+'"'
				elif suboperators[5]==I['D=D']: bq=meme[5].rstrip('0').rstrip('.')+' '+meme[4]
				else: bq=OPR[suboperators[5]]['$beg']+' '+meme[5].rstrip('0').rstrip('.')+' '+meme[4]

				print(f"| {meme[1][:23]:<23} | {meme[3][:23]:<23} | {bq[:23]:<23} |")


	if not found: print(f"| {'No matching memes':<76} |")


	print(br)



if __name__ == "__main__":
	if sys.argv[1] == 'sql': sql(sys.argv[2])
	elif sys.argv[1] == 'query' or sys.argv[1] == 'qry' or sys.argv[1] == 'q' or sys.argv[1] == 'get' or sys.argv[1] == 'g': qry(sys.argv[2])
	elif sys.argv[1] == 'file' or sys.argv[1] == 'import': putfile(sys.argv[2])
	elif sys.argv[1] == 'dbadd' or sys.argv[1] == 'adddb': dbadd()
	elif sys.argv[1] == 'tableadd' or sys.argv[1] == 'addtable': tableadd()
	elif sys.argv[1] == 'tabledel' or sys.argv[1] == 'deltable': tabledel()
	elif sys.argv[1] == 'coreadd' or sys.argv[1] == 'addcore': putfile(LOCAL_DIR+'/core.meme')
	elif sys.argv[1] == 'recore':
		tabledel()
		tableadd()
		putfile(LOCAL_DIR+'/core.meme')
	elif sys.argv[1] == 'fileall' or sys.argv[1] == 'allfile':
		files = glob.glob(LOCAL_DIR+'/*.meme') + glob.glob(LOCAL_DIR+'/data/*.meme')
		for file in files:
			putfile(file)
	elif sys.argv[1] == 'logitest':
		logitest()
	else:
		sys.exit("MAIN.PY ERROR: Invalid command");