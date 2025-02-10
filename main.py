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

	operators, operands = memelang.parse(mqry)
	print ("MEME:")
	print(operators)
	print(operands)
	print (memelang.deparse(operators, operands)+"\n")

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
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_MEME} (val DECIMAL(20,6), aid BIGINT, cid BIGINT, did BIGINT, bid BIGINT, wal DECIMAL(20,6), vop SMALLINT, wop SMALLINT); CREATE UNIQUE INDEX {DB_TABLE_MEME}_alrb_idx ON {DB_TABLE_MEME} (aid,cid,did,bid); CREATE INDEX {DB_TABLE_MEME}_did_idx ON {DB_TABLE_MEME} (did); CREATE INDEX {DB_TABLE_MEME}_bid_idx ON {DB_TABLE_MEME} (bid);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_NAME} (aid BIGINT, bid BIGINT, str VARCHAR(511)); CREATE UNIQUE INDEX {DB_TABLE_NAME}_aid_idx ON {DB_TABLE_NAME} (aid,bid,str); CREATE INDEX {DB_TABLE_NAME}_bid_idx ON {DB_TABLE_NAME} (bid); CREATE INDEX {DB_TABLE_NAME}_str_idx ON {DB_TABLE_NAME} (str);\"",
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
	operators, operands = memelang.parse('a]rz]bz=t;a]rx]bx=t;bx[rx]ry]by=t;bz[rz]rj]')

	print(operators, operands)
	print()
	memelang.sequence(operators, operands, 'expand')

	print(operators, operands)
	print()

	memelang.logify(operators, operands)
	print(memelang.deparse(operators, operands,{'newline':True}))



def memeprint(operators, operands):
	found = False

	br = f"+{'-' * 25}+{'-' * 25}+{'-' * 25}+"
	print(f"{br}\n| {'A':<23} | {'D':<23} | {'B=V':<23} |\n{br}")

	o=1
	olen=len(operators)
	while o<olen:
		if operators[o]!=I[';']: raise Exception(f'Operator counting error at {o} for {operators[o]}')
		slen=int(operands[o])
		o+=1

		if slen and operators[o:o+W]==VACDB and operands[o+C] in (I['is'], 'is', I['of'], 'of'):
				found = True
				meme=list(map(str, operands[o:o+slen]))

				if operators[o+W]==I['#']: bq=meme[B]
				elif operators[o+W]==I['$']: bq='"'+meme[W]+'"'
				elif operators[o+W]==I['.']: bq=meme[W].rstrip('0').rstrip('.')+' '+meme[B]
				else: bq=OPR[operators[o+W]]['$beg']+' '+meme[W].rstrip('0').rstrip('.')+' '+meme[B]

				print(f"| {meme[1][:23]:<23} | {meme[3][:23]:<23} | {bq[:23]:<23} |")

		o+=slen

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