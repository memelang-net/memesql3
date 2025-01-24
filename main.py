from conf import *
import sys
import os
import re
import db
import glob
import memelang

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))


#### SEARCH ####

def sql(qry_sql):
	rows = db.select(qry_sql, [])
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
	

#### ADD MEMES ####

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
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_MEME} (aid INTEGER, rid INTEGER, bid INTEGER, qnt DECIMAL(20,6)); CREATE UNIQUE INDEX {DB_TABLE_MEME}_arb_idx ON {DB_TABLE_MEME} (aid,rid,bid); CREATE INDEX {DB_TABLE_MEME}_rid_idx ON {DB_TABLE_MEME} (rid); CREATE INDEX {DB_TABLE_MEME}_bid_idx ON {DB_TABLE_MEME} (bid);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_NAME} (aid INTEGER, bid INTEGER, quo VARCHAR(511)); CREATE INDEX {DB_TABLE_NAME}_aid_idx ON {DB_TABLE_NAME} (aid); CREATE INDEX {DB_TABLE_NAME}_bid_idx ON {DB_TABLE_NAME} (bid); CREATE INDEX {DB_TABLE_NAME}_quo_idx ON {DB_TABLE_NAME} (quo);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_LOGI} (rid INTEGER, bid INTEGER, opr INTEGER, rid1 INTEGER, bid1 INTEGER); CREATE INDEX {DB_TABLE_NAME}_v1_idx ON {DB_TABLE_LOGI} (aid,rid);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_TABLE_MEME} TO {DB_USER};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_TABLE_NAME} TO {DB_USER};\""
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_TABLE_LOGI} TO {DB_USER};\""
	]

	for command in commands:
		print(command)
		os.system(command)


# Delete database table
def tabledel():
	commands = [
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_TABLE_MEME};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_TABLE_NAME};\""
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_TABLE_LOGI};\""
	]

	for command in commands:
		print(command)
		os.system(command)


def logitest():
	operators, operands = memelang.delace('a.rz:bz=1;a.rx:bx=1;.rx:bx[q=q].ry:by;.rz:bz[a.r]rj')
	print(operators, operands)
	memelang.logirb(operators, operands)
	print(memelang.interlace(operators, operands,{'newline':True}))



def memeprint(operators, operands):
	# Formatting the output
	br = f"+{'-' * 19}+{'-' * 19}+{'-' * 19}+{'-' * 18}+"

	size = 6
	length = len(operators)

	print(br)
	print(f"| {'A':<17} | {'R':<17} | {'B':<17} | {'Q':>16} |")
	print(br)

	if length<2: print(f"| {'No matching memes':<76} |")
		
	else:
		operands=list(map(str, operands))

		for i in range(1, length, size):
			if operators[i+1]==I["'"]:
				operands[i+1]= "'"+operands[i+1]
				
			aid_str=f"{operands[i+0][:17]:<17}"
			rid_str=f"{operands[i+1][:17]:<17}"
			bid_str=f"{operands[i+2][:17]:<17}"
			qnt_str = f"{operands[i+4].rstrip('0').rstrip('.')[:16]:>16}"
			print(f"| {aid_str} | {rid_str} | {bid_str} | {qnt_str} |")

	print(br+"\n")



if __name__ == "__main__":
	if sys.argv[1] == 'sql':
		sql(sys.argv[2])
	elif sys.argv[1] == 'query' or sys.argv[1] == 'qry' or sys.argv[1] == 'q' or sys.argv[1] == 'get' or sys.argv[1] == 'g':
		qry(sys.argv[2])
	elif sys.argv[1] == 'nameget' or sys.argv[1] == 'name' or sys.argv[1] == 'names':
		nameget(sys.argv[2])
	elif sys.argv[1] == 'file' or sys.argv[1] == 'import':
		putfile(sys.argv[2])
	elif sys.argv[1] == 'dbadd' or sys.argv[1] == 'adddb':
		dbadd()
	elif sys.argv[1] == 'tableadd' or sys.argv[1] == 'addtable':
		tableadd()
	elif sys.argv[1] == 'tabledel' or sys.argv[1] == 'deltable':
		tabledel()
	elif sys.argv[1] == 'coreadd' or sys.argv[1] == 'addcore':
		putfile(LOCAL_DIR+'/core.meme')
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