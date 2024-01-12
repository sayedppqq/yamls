#!/bin/bash

echo "************************************************************"
echo "Setting up users..."
echo "************************************************************"

# create root user
nohup gosu mongodb mongo DBNAME --eval "db.createUser({user: 'admin', pwd: 'admin', roles:[{ role: 'root', db: 'admin' }]});"

# create app user/database
nohup gosu mongodb mongo DBNAME --eval "db.createUser({ user: 'myuser', pwd: 'myuser', roles: [{ role: 'readWrite', db: 'admin' }]});"

echo "************************************************************"
echo "Shutting down"
echo "************************************************************"
nohup gosu mongodb mongo admin --eval "db.shutdownServer();"
