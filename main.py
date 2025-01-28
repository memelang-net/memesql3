from conf import *
import sys
import os
import re
import db
import glob
import memelang

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Execute and output an SQL query
def sql(qry_sql):
	rows = db.select(qry_sql, [])
	for row in rows:
		print(row)


# Search for memes from a memelang query string
def qry(mqry):
	sql, params = memelang.querify(mqry, DB_AIRBEQ, False)
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
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_AIRBEQ} (aid BIGINT, iid BIGINT, rid BIGINT, bid BIGINT, eid SMALLINT, qnt DECIMAL(20,6)); CREATE UNIQUE INDEX {DB_AIRBEQ}_airb_idx ON {DB_AIRBEQ} (aid,iid,rid,bid); CREATE INDEX {DB_AIRBEQ}_rid_idx ON {DB_AIRBEQ} (rid); CREATE INDEX {DB_AIRBEQ}_bid_idx ON {DB_AIRBEQ} (bid);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_ABS} (aid BIGINT, bid BIGINT, str VARCHAR(511)); CREATE INDEX {DB_ABS}_aid_idx ON {DB_ABS} (aid); CREATE INDEX {DB_ABS}_bid_idx ON {DB_ABS} (bid); CREATE INDEX {DB_ABS}_str_idx ON {DB_ABS} (str);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_AIRBEQ} TO {DB_USER};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_ABS} TO {DB_USER};\"",
	]

	for command in commands:
		print(command)
		os.system(command)


# Delete database table
def tabledel():
	commands = [
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_AIRBEQ};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_ABS};\"",
	]

	for command in commands:
		print(command)
		os.system(command)


def logitest():
	operators, operands = memelang.delace('a.rz:bz=1;a.rx:bx=1;bx\'rx.ry:by=t;bz\'rz.rj')
	print(operators, operands)
	memelang.airbeqify(operators, operands)
	print(operators, operands)
	memelang.logirb(operators, operands)
	print(memelang.interlace(operators, operands,{'newline':True}))



def memeprint(operators, operands):
	found = False
	length = len(operators)

	br = f"+{'-' * 19}+{'-' * 19}+{'-' * 19}+{'-' * 18}+"
	print(f"{br}\n| {'A':<17} | {'R':<17} | {'B':<17} | {'Q':>16} |\n{br}")

	cmds = memelang.cmdify(operators, operands)

	for cmd in cmds:
		for suboperators, suboperands in cmd:
			if suboperators[:4]==AIRB and suboperands[1] in (I['is'], 'is'):
				found = True
				if suboperators[4]==I['=']:
					if suboperands[4]==I['t']: suboperands[4]='TRUE'
					elif suboperands[4]==I['f']: suboperands[4]='FALSE'
				meme=list(map(str, suboperands))
				print(f"| {meme[0][:17]:<17} | {meme[2][:17]:<17} | {meme[3][:17]:<17} | {meme[4].rstrip('0').rstrip('.')[:16]:>16} |")


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
	elif sys.argv[1] == 'fileall' or sys.argv[1] == 'allfile':
		files = glob.glob(LOCAL_DIR+'/*.meme') + glob.glob(LOCAL_DIR+'/data/*.meme')
		for file in files:
			putfile(file)
	elif sys.argv[1] == 'recore':
		tabledel()
		tableadd()
		putfile(LOCAL_DIR+'/core.meme')
	elif sys.argv[1] == 'logitest':
		logitest()
	else:
		sys.exit("MAIN.PY ERROR: Invalid command");