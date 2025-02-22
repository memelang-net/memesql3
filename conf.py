
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Poseqres
DB_USER = 'memeuser'  # Username for MySQL/Poseqres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Poseqres
DB_NAME = 'memedb'  # Database name for MySQL/Poseqres
DB_TABLE_MEME='meme'
DB_TABLE_NAME='name'

# Global dictionary to cache key->id mappings
I = {

	'f'   : 0,
	't'   : 1,
	'g'   : 2,

	'@'   : 4,
	'['   : 5,
	']'   : 6,
	'=='  : 7,
	'"'   : 8,
	'.'   : 9,
	'#'   : 10,
	'?'   : 11,
	'||'  : 12,
	'&&'  : 13,

	';'   : 14,

	'#='  : 32,
	'='   : 33,
	'>'   : 34,
	'<'   : 35,
	'>='  : 36,
	'<='  : 37,
	'!='  : 38,

	'&'   : 50,

	'qry' : 200,
	'nam' : 201,
	'opr' : 202,
	'id'  : 203,
	'key' : 204,
	'tit' : 205,
	'is'  : 206,
	'of'  : 207,
	'unk' : 208,
	'all' : 209,
	'mix' : 210,

	'cor'  : 999999
}

K = {value: key for key, value in I.items()}
