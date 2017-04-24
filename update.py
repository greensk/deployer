#!/usr/bin/python3
import os
import subprocess
import json
import MySQLdb

from git import Repo
from git import Git

configFile = open('config.json')
configContent = configFile.read()
configFile.close()
config = json.loads(configContent)
print(config)

path = config['path']

db = MySQLdb.connect(host=config['db']['host'], port=config['db']['port'], user=config['db']['user'], passwd=config['db']['password'], db=config['db']['db'], charset='utf8')

cursor = db.cursor()
queryProjectToDeploy = 'SELECT `project_id`, `git`, `subdomain`, `email_user` FROM `project` INNER JOIN `user` ON `project`.`user_id` = `user`.`user_id`  WHERE `status_project` = 1'
cursor.execute(queryProjectToDeploy)

for (projectId, gitLink, subdomain, email) in cursor:
	if not subdomain:
		subdomain = 'p%d' % projectId
#	print(Git().clone(gitLink, '%s/%s' % (path, subdomain)))
	if Repo.clone_from(gitLink, '%s/%s' % (path, subdomain)):

		updateCursor = db.cursor()
		updateQuery = 'UPDATE `project` SET `status_project` = 2, `subdomain` = %s WHERE `project_id` = %s'
		updateCursor.execute(updateQuery, [subdomain, projectId])
		db.commit()

		print('add %s for %s' % (subdomain, email))
	else:
		print('Error while clonnging')


# INSTALL section
# DB projects
# status = 1
# git clone
# add http server host
# if mysql:
#	add user mysql
#	add db mysql
#	add permission
#	add `database` record
#	send password to user
# if composer: run `composer install`
# if npm: run `npm install`
# update project status
# add release
# send email

dirs = os.listdir(path)
# UPDATE section
# DB projects
# status = 2
for name in dirs:
	dirPath = "%s/%s" % (path, name)
	gitPath = "%s/%s/.git" % (path, name)
	# update git url
	if os.path.isdir(dirPath) and os.path.isdir(gitPath):
		repo = Repo(dirPath)
		origin = repo.remote('origin')
		assert origin.exists()

		currentCommit = repo.commit()
		result = origin.pull()[0]
		if currentCommit == result.commit:
			print('%s no update' % name)
		else:
			print('%s update' % name)
			scriptPath = '%s/%s/postinstall.sh' % (path, name)
			if os.path.isfile(scriptPath) and os.access(scriptPath, os.X_OK):
				# TODO add to `release`
				print('postinstall script found')
				print('===')
				proc = subprocess.Popen([scriptPath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
				scriptOutput = proc.stdout.read()
				print(scriptOutput.decode('utf8'))
				print('===')
			# if composer: run `composer insatall`
			# if npm: run `npm install`
			# insert `release`
db.close()



