# pg2mysql
Simple scripts for converting a Postgres DB to MySQL db.

### Note
Now its working in semi-auto mode and work may surprise

### Comment
This script was created by a specific need for migrating a particular Postgres DB to MySQL and worked ok for this particular scenario.

The other tools that I found online for this kind of tasks were not working the way I needed so wrote this scripts.

There are some things to pay attention and have in mind before using it:

- The main script is the BASH script: Maybe all could be solved inside the Python script, but for me it was faster this way because I only wanted the Python script output SQL sentences without knowing anything about MySQL.
- The BASH script must be called from the server where the MySQL is running and I assume that "root" is the user. See the BASH script for the callings on the mysql program.
- The Data Types from Postgres to MySQL may be incomplete. I only converted the types that was present in my DB. If later on other DBs should be migrated, I will add support for missing types. If some type is not covered, it will be outputed as *FIXME*.
- The logging information and docs inside code could be improved a lot. I just didn't have time to do it. 
- The code asume that the /tmp folder exists, and there will be exported all data as CSV.
- The connection to Postgres is opened as READONLY.
- The export is enconding using UTF-8, and the MySQL db es created with the same enconding. Have a look at the BASH script.
- The MySQL engine is fixed to InnoDB

And the more important thing is to open both scripts and do a simple revision to understand how it work before run them. 

Hope it will be useful. That's the reason for making it public on GitHub.

### Install dependencies
```bash
pip install -r requirements.txt
```

### Example
```bash
> python2 ./pg2mysql.py -?
usage: pg2mysql.py [-?] [-h HOST] [-p PORT] [-d DBNAME] [-s SCHEMA] [-U USER]
                   [-W PASSWORD]

optional arguments:
  -?, --help
  -h HOST, --host HOST  Specifies the host name of the machine on which the
                        server is running. If the value begins with a slash,
                        it is used as the directory for the Unix-domain
                        socket.
  -p PORT, --port PORT  Specifies the TCP port or the local Unix-domain socket
                        file extension on which the server is listening for
                        connections. Defaults to 5432.
  -d DBNAME, --dbname DBNAME
                        Specifies the name of the database to connect to.
  -s SCHEMA, --schema SCHEMA
                        Specifies the name of the schema to dump.
  -U USER, --user USER  Connect to the database as the user username instead
                        of the default.
  -W PASSWORD, --password PASSWORD
                        Connect to the database with specified password.

> python2 ./pg2mysql.py -h postgres -s schema_name > /tmp/schema.sql # save db schema to /tmp/schema.sql
```

### Contribute
* If you found a bug, please let my know it via issue
* Pull Requests are welcome!
