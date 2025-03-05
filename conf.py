
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

	'['   : 1,
	']'   : 2,
	'|'   : 3,

	'=$'  : 4,
	'=f'  : 5,
	'=t'  : 6,
	'=g'  : 7,
	'=.'  : 8,
	'>'   : 9,
	'<'   : 10,
	'>='  : 11,
	'<='  : 12,
	'!='  : 13,

	';'   : 20,
	' '   : 21,
	'>>'  : 22,

	'qry' : 256,
	'nam' : 257,
	'id'  : 258,
	'key' : 259,
	'tit' : 260,
	'of'  : 261,
	'all' : 262,
	'mix' : 263,


	'cor'  : 9999999
}

# Lazy population for now
K = {value: key for key, value in I.items()}
