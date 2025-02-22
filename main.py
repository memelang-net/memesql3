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
	operators, operands = memelang.decode(mqry)
	print ("QUERY:    ", memelang.encode(operators, operands))
	print("OPERATORS:", [K[op] for op in operators])
	print("OPERANDS: ", operands)

	sql, params = memelang.querify(mqry, DB_TABLE_MEME, False)
	params = memelang.identify(params)
	full_sql = memelang.morfigy(sql, params)
	print(f"SQL: {full_sql}\n")

	# Execute query
	print(f"RESULTS:")
	memes = memelang.get(mqry+' qry]nam]key')
	memelang.out(memes[0], memes[2])


# Read a meme file and save it
def putfile(file_path):
	operators, operands = memelang.read(file_path)
	operators, operands = memelang.put(operators, operands)
	memelang.out(operators, operands)


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
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_MEME} (aid BIGINT, rid BIGINT, bid BIGINT, eql SMALLINT, qnt DECIMAL(20,6)); CREATE UNIQUE INDEX {DB_TABLE_MEME}_aid_idx ON {DB_TABLE_MEME} (aid,rid,bid); CREATE INDEX {DB_TABLE_MEME}_rid_idx ON {DB_TABLE_MEME} (rid); CREATE INDEX {DB_TABLE_MEME}_bid_idx ON {DB_TABLE_MEME} (bid);\"",
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


def qrytest():
	queries=[
		'george_washington',
		'george_washington]',
		'george_washington[',
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
		']adyear',
		'[year]adyear',
		'[birth[year]adyear',
		']adyear=1732',
		']adyear>=1900',
		'[year]adyear>1800',
		'[birth[year]adyear<=2000',
		'[spouse]',
		'[spouse] [child]',
		'[birth[year]adyear>=1800 [birth[year]adyear<1900',
		'[spouse [child [birth[year]adyear<1900',
		'george_washington; john_adams',
		'george_washington;; john_adams;;',
	]
	errcnt=0

	for mqry in queries:
		print('First Query:  ', mqry)
		operators, operands = memelang.decode(mqry)
		print('Operators:', [K[op] for op in operators])
		print('Operands:', operands)
		mqry2 = memelang.encode(operators, operands)
		print('Second Query: ', mqry2)
		sql, params = memelang.querify(mqry, DB_TABLE_MEME, False)
		print('SQL: ', memelang.morfigy(sql, params))
		c1=memelang.count(mqry)
		c2=memelang.count(mqry2)
		print ('First Count:  ', c1)
		print ('Second Count: ', c2)

		if not c1 or c1!=c2:
			print()
			print('*** COUNT ERROR ABOVE ***')
			errcnt+=1

		print()
	print("ERRORS:", errcnt)
	print()



if __name__ == "__main__":
	if sys.argv[1] == 'sql': sql(sys.argv[2])
	elif sys.argv[1] == 'query' or sys.argv[1] == 'qry' or sys.argv[1] == 'q' or sys.argv[1] == 'get' or sys.argv[1] == 'g': qry(sys.argv[2])
	elif sys.argv[1] == 'file' or sys.argv[1] == 'import': putfile(sys.argv[2])

	elif sys.argv[1] == 'dbadd' or sys.argv[1] == 'adddb': dbadd()
	elif sys.argv[1] == 'tableadd' or sys.argv[1] == 'addtable': tableadd()
	elif sys.argv[1] == 'tabledel' or sys.argv[1] == 'deltable': tabledel()
	elif sys.argv[1] == 'coreadd' or sys.argv[1] == 'addcore': putfile(LOCAL_DIR+'/core.meme')

	elif sys.argv[1] == 'qrytest': qrytest()

	elif sys.argv[1] == 'install':
		dbadd()
		tableadd()
		putfile(LOCAL_DIR+'/core.meme')

	elif sys.argv[1] == 'reinstall':
		tabledel()
		tableadd()
		putfile(LOCAL_DIR+'/core.meme')
		if sys.argv[2]=='-presidents': putfile(LOCAL_DIR+'/presidents.meme')

	elif sys.argv[1] == 'fileall' or sys.argv[1] == 'allfile':
		files = glob.glob(LOCAL_DIR+'/*.meme') + glob.glob(LOCAL_DIR+'/data/*.meme')
		for file in files:
			putfile(file)
	else:
		sys.exit("MAIN.PY ERROR: Invalid command");