#!/usr/bin/python3
import os
import subprocess
import json
import MySQLdb
import string
import random
import shutil
import os.path

import smtplib
from email.mime.text import MIMEText

from git import Repo
from git import Git

configFile = open('config.json')
configContent = configFile.read()
configFile.close()
config = json.loads(configContent)

def pwGen(size = 16, chars=string.ascii_letters + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))

def deployMysql(db, projectId):
	mysqlDb = 'web_%d' % projectId
	mysqlUser = 'web_%d' % projectId
	mysqlPassword = pwGen()
	
	mysqlCursor = db.cursor()

	try:	
		addDbQuery = 'CREATE DATABASE `%s` CHARSET utf8' % mysqlDb
		mysqlCursor.execute(addDbQuery)
		#GRANT ALL ON db1.* TO 'jeffrey'@'localhost';

		addUserQuery = 'GRANT ALL ON `%s`.* TO %%s@localhost IDENTIFIED BY %%s' % mysqlDb
		mysqlCursor.execute(addUserQuery, (mysqlUser, mysqlPassword))

		mysqlCursor.execute('FLUSH PRIVILEGES')

		insertDbData = 'INSERT INTO `database` (`name`, `user_database`, `password_database`, `project_id`) VALUES (%s, %s, %s, %s)'
		mysqlCursor.execute(insertDbData, [mysqlDb, mysqlUser, mysqlPassword, projectId])
		db.commit()
	except Exception as ex:
		print(ex)
		db.rollback()
		return None
	else:
		return [mysqlDb, mysqlUser, mysqlPassword]

def outputMysql(path, params):
	try:
		f = open('%s/db_params.php' % path, 'w')
		f.write("<?php\n")
		f.write("return array(\n")
		f.write("\t'type' => 'mysql',\n")
		f.write("\t'host' => 'localhost:3306',\n")
		f.write("\t'db' => '%s',\n" % params[0])
		f.write("\t'user' => '%s',\n" % params[1])
		f.write("\t'password' => '%s'\n" % params[2])
		f.write(");\n")
		f.close()
	except Exception as ex:
		print(ex)
		return False
	else:
		return True

def deployMail (domain, mailConfig, userAddress, subdomain, mysql):
	text = "Ваш проект выложен по адресу: http://%s.%s\n" % (subdomain, domain)
	if mysql != None:
		text += "\nПараметры MySQL:\n"
		text += "База данных: %s\n" % mysql[0]
		text += "Имя пользователя mysql: %s\n" % mysql[1]
		text += "Пароль: %s\n" % mysql[2]
		text += "Эта информация также продублирована в файле db_params.php в корне проекта.\n"
		text += "Для администрирования базы данных вы можете использовать веб-интерфейс: %s (доступен только из внутренней сети университета)\n" % mailConfig['dbadmin']
		
	msg = MIMEText(text.encode('utf-8'), 'plain', 'UTF-8')
		
	msg['Subject'] = 'Публикация на сервере ИТФ'
	msg['From'] = mailConfig['address']
	msg['To'] = userAddress

		
	server = smtplib.SMTP(mailConfig['smtp']['host'], mailConfig['smtp']['port'])
	server.ehlo()
	server.starttls()

	server.login(mailConfig['smtp']['login'], mailConfig['smtp']['password'])
	server.sendmail(mailConfig['address'], [userAddress], msg.as_string())
	server.quit()


def runScript(cmd, cwd):
	proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
	scriptOutput = proc.stdout.read()
	return scriptOutput.decode('utf8')

def postinstall(path):
	log = ''
	try:
		if (os.path.isfile('%s/composer.json' % path)):
			log += "Running composer install: %s\n" % runScript('composer install', path)
	except Exception as ex:
		print(ex)
		return None
	else:
		return log

path = config['path']

db = MySQLdb.connect(host=config['db']['host'], port=config['db']['port'], user=config['db']['user'], passwd=config['db']['password'], db=config['db']['db'], charset='utf8')

cursor = db.cursor()
queryProjectToDeploy = 'SELECT `project_id`, `git`, `subdomain`, `email_user`, `use_mysql` FROM `project` INNER JOIN `user` ON `project`.`user_id` = `user`.`user_id`  WHERE `status_project` = 1'
cursor.execute(queryProjectToDeploy)

for (projectId, gitLink, subdomain, email, useMysql) in cursor:
	if not subdomain:
		subdomain = 'p%d' % projectId
	projectPath = '%s/%s' % (path, subdomain)
	if Repo.clone_from(gitLink, projectPath):
		success = True
		mysqlParams = None
		if int(useMysql):
			print('Deploy mysql')
			mysqlParams = deployMysql(db, projectId)
			if mysqlParams != None:
				if not outputMysql(projectPath, mysqlParams):
					print('Error while creating db params file')
					success = False
			else:
				success = False
				print('Mysql add error')

#		installLog = postinstall(projectPath)
#		if installLog != None:
#			print(installLog)
#		else:
#			print('Error while postinstall running')

		if success:
			updateCursor = db.cursor()
			updateQuery = 'UPDATE `project` SET `status_project` = 2, `subdomain` = %s WHERE `project_id` = %s'
			updateCursor.execute(updateQuery, [subdomain, projectId])
			db.commit()

			deployMail(config['domain'], config['email'], email, subdomain, mysqlParams)
	
			print('add %s for %s' % (subdomain, email))
		else:
			print('Remove directory')
			shutil.rmtree('%s/%s' % (path, subdomain))
			exit(1)
			
	else:
		print('Error while clonnging')
		exit(1)


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
		try:
			repo = Repo(dirPath)
			origin = repo.remote('origin')
			assert origin.exists()

			currentCommit = repo.commit()
			result = origin.pull()[0]
			if currentCommit == result.commit:
				print('%s no update' % name)
			else:
				print('%s update' % name)
		except Exception as e:
			print(e)
#			scriptPath = '%s/%s/postinstall.sh' % (path, name)
#			if os.path.isfile(scriptPath) and os.access(scriptPath, os.X_OK):
#				# TODO add to `release`
#				print('postinstall script found')
#				print('===')
#				proc = subprocess.Popen([scriptPath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#				scriptOutput = proc.stdout.read()
#				print(scriptOutput.decode('utf8'))
#				print('===')
			# if composer: run `composer insatall`
			# if npm: run `npm install`
			# insert `release`
db.close()



