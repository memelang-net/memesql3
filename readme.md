# memesql3

These Python scripts receive [Memelang v3](https://memelang.net/03/) queries, convert them to SQL, then execute them on a Postgres database. 

## Memelang v3

Memelang traverses a knowledge graph using only three novel operators: 
* `]` indicates a node
* `[` indicates an edge
* `-` "inverses" an edge

The basic syntax of Memelang is that some node `A` has some edge relation `R` with some node `B` which equals a true, false, or quantity value `Q`.

	A[R]B=Q

	// "It is true that John Adams attended Harvard"
	john_adams[college]harvard=t

	// List all relations (edges and connected nodes) of John Adams
	john_adams

	// List all colleges that John Adams attended
	john_adams[college]

	// List all people (nodes) that attended Harvard
	[college]harvard

Read the [full documentation here](https://memelang.net/03/).


## Tables

Relations/edges are stores in the `meme` table:

	CREATE TABLE meme (
	 aid BIGINT, 
	 rid BIGINT, 
	 bid BIGINT, 
	 eql SMALLINT, 
	 qnt DECIMAL(20,6)
	);


| Column | Description                                                                           |
|-------:|:--------------------------------------------------------------------------------------|
| aid  | **A** node ID of the relation (john_adams).                                                       |
| rid  | **R** edge ID (college, spouse).                                    |
| bid  | **B** node ID of the relation (harvard).                                                        |
| eql  | Operator ID, typically `=`, but can be `<`, `>`, `<=`, etc. |
| qnt  | **Quantity** (0 = false, 1 = true, or other numeric values). |


Names are stored in the `name` table:

	CREATE TABLE name (
	 aid BIGINT, 
	 bid BIGINT, 
	 str VARCHAR(511)
	);

| Column | Description                                                                |
|-------:|:---------------------------------------------------------------------------|
| aid  | Numeric ID (matching the `aid` in the `meme` table).                       |
| bid  | Numeric ID representing the **type** of name (e.g., full name, short name).|
| str  | The actual **string name** for the entity (e.g., "John Adams").            |


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
	sudo systemctl start postgresql
	sudo systemctl enable postgresql
	
	# Download files
	git clone https://github.com/memelang-net/memesql3.git memesql
	cd memesql

	# Configure the conf.py file according for your Postgres settings
	# Create database and tables
	sudo python3 ./main.py install

	# (Optional) load example presidents data
	python3 ./main.py file ./presidents.meme


## Example CLI Usage

Execute a query:

	# python3 ./main.py get "john_adams[spouse"

Outputs:

	john_adams[spouse]abigail_adams=t


## License

Free public use under the [Memelicense](https://memelicense.net/). Copyright 2025 HOLTWORK LLC. Patent pending. Contact info@memelang.net.