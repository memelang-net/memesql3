# memesql3

These Python scripts receive [Memelang v3](https://memelang.net/03/) queries, convert them to SQL, then execute them on a Postgres database. Free public use under the [Memelicense](https://memelicense.net/).  Copyright 2025 HOLTWORK LLC. Patent pending. Contact info@memelang.net.


## Files

* *conf.py* database configurations
* *core.meme* core memelang id-keys to be loaded into the database
* *main.py* CLI interface for queries and testing
* *memelang.py* library to decode Memelang queries and execute in Postgres
* *presidents.meme* example Memelang data for the U.S. presidents


## Installation

Installation on Ubuntu:

	# Install packages
	sudo apt install -y git postgresql python3 python3-psycopg2
	systemctl start postgresql
	systemctl enable postgresql
	
	# Download files
	git clone https://github.com/memelang-net/memesql3.git memesql
	cd memesql

	# Configure the db.py file according for your Postgres settings
	# Create database and tables
	sudo python3 ./main.py install

	# (Optional) load example presidents data
	python3 ./main.py file ./presidents.meme


## Example CLI Usage

Execute a query:

	# python3 ./main.py get "john_adams[spouse"

Outputs:

	QUERY:     john_adams[spouse;
	OPERATORS: ['opr', ';', '-]', '[', ';']
	OPERANDS:  [210, 2.5, 'john_adams', 'spouse', 0.5]
	SQL: WITH z1 AS (SELECT m0.aid AS a0, ... AS acdb FROM meme m0 WHERE m0.aid=1000025 AND m0.did=1000023) SELECT acdb FROM z1

	RESULTS:
	john_adams[spouse]abigail_adams=t;
