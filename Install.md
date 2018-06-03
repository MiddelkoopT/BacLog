# BacLog Site Installation

These "executable documenation" instructions contain local
configuration as examples (user id's etc).  This documentation assumes
CentOS7. Please adapt to your local site.

## Server Setup

```
sudo yum install -y postresql-server python-psycopg2
sudo postgresql-setup initdb
```

Configure/lock down database then start.
```
sudo systemctl enable postgresql.service
sudo systemctl start postgresql.service
sudo systemctl status postgresql.service
```

Make current user DBA and create DB
```
sudo su postgres -c "createuser -d -s $USER"
createdb baclog
psql baclog < postgres.sql
```

Create or symlink a `local.ini` configuration file then run server/client.

```
python baclog.py &
python bacnode.py &
```

Read Log
```
psql baclog -c "select * from log;"
```
