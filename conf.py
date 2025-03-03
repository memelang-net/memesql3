
# Database configurations
DB = {
	'host' : 'localhost',   # Host for Poseqres
	'user' : 'memeuser',    # Username for Poseqres
	'pswd' : 'memepswd',    # Password for Poseqres
	'name' : 'memedb',      # Database name for Poseqres
	'table_meme' :'meme',
	'table_name' :'name'
}

# Global dictionary to cache key->id mappings
I = {

	'f'   : 0,
	't'   : 1,
	'g'   : 2,

	'['   : 5,
	']'   : 6,
	'=='  : 7,
	'$'   : 8,
	'.'   : 9,
	'#'   : 10,
	'|'   : 11,
	'~'   : 12,

	';'   : 15,

	'#='  : 16,
	'='   : 17,
	'>'   : 18,
	'<'   : 19,
	'>='  : 20,
	'<='  : 21,
	'!='  : 22,

	' '   : 27,
	'>>'  : 28,

	'qry' : 200,
	'nam' : 201,
	'id'  : 202,
	'key' : 203,
	'tit' : 204,
	'of'  : 205,
	'all' : 206,
	'mix' : 207,

	'cor'  : 9999999
}

# Lazy population for now
K = {value: key for key, value in I.items()}
