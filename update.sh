#!/bin/bash
rootDir='/var/www'
for d in `ls -1 $rootDir`;
do
        cd $rootDir/$d
        if [ -d .git ]
        then
                git pull origin master
                git reset --hard origin/master
                if [ -x $rootDir/$d/postinstall.sh ]
                then
                    $rootDir/$d/postinstall.sh
                fi
        fi
done

