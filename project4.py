import socket
import threading
import os
import getopt
import sys
import re
import time
import datetime

BUFFER_SIZE = 1024
NUM_USERS = 10

#the help menu for the command line args
def usage():
	print(''' -h: This menu.
 --port [port]: The port the server should run on. Default = 8080
 --docroot [directory]: The directory the server should look for requested files. Default = directory the server is run from.
 --log [file]: A file for log messages to be written to. Default = standard out.''')

#set the default values
port = 8080
docroot = 'home directory'
log = 'standard output'

try:
	opts, val = getopt.getopt(sys.argv[1:],'hp:o',['port=','docroot=','log=',])
except getopt.GetoptError as err:
	usage()
	sys.exit(1)

#check the command line args
for opt, arg in opts:
	if opt in ('-p','--port'):
		port = int(arg)
	elif opt in ('-d','--docroot'):
		docroot = arg
	elif opt in ('l','--log'):
		log = arg
	elif opt == '-h':
		usage()

print('PORT   	:', port)
print('DOCROOT	:', docroot)
print('LOG    	:', log)

#Make sure the directory is valid
if docroot == 'home directory':
	docroot = os.getcwd()
elif not os.path.isdir(docroot):
	print("Directory not found. Using current directory")
	docroot = os.getcwd()

#create the socket
sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockfd.bind(('',port)) 

def Socket_Thread():

	# create the socket we are going to recieve from
	connected_socket, addr = sockfd.accept()
	status = 404
	while True:

		#our HTTP request
		data = connected_socket.recv(BUFFER_SIZE)
		message = data.decode()
		output(("*** Request ***\n" + message), log)
		file_location = docroot
		file_name = ""

		if "GET" in message:
			
			#get the file name from the request
			temp = re.search('GET /(.*)HTTP',message)
			file_name = temp.group(1).strip() 

			print(file_name)

			#check to make sure they are staying in the current directory
			#security implementation
			if '/' in file_name:
				status = 404
				file_name = "404.html"
				file_location = docroot + "/" + file_name
			else:
				#create the file path
				file_name = "/" + file_name
				file_location = docroot + file_name

				#check if the file exists
				if os.path.exists(file_location):
					status = 200
				else:
					status = 404
					file_name = "404.html"
					file_location = docroot + "/" + file_name
		else:
			#unsupported HTTP request
			status = 501
			file_name = "501.html"
			file_location = docroot + "/" + file_name

		#file to send has been determined log and send the response
		log_output = log_value(status, file_location, message)

		#write to the log
		output(("*** Response ***\n" + log_output), log)

		#send the response
		respond(log_output,connected_socket,file_name)

#Creates the HTTP header
def log_value(status, file_location, message):

	log_output = ""
	response = ""
	last_modified = str(time.ctime(os.path.getmtime(file_location))).strip()

	#check if modified
	if 'If-Modified-Since' in message:
		temp = re.search('If-Modified-Since: (.*)\r\n',message)
		file_last_mod = temp.group(1).strip() 
		if file_last_mod == last_modified:
			status = 304

	#make the status code
	status_code = ""
	if status == 304:
		status_code = "Not Modified"
	elif status == 404:
		status_code = "Not Found"
	elif status == 501:
		status_code = "Not Implemented"
	elif status == 200:
		status_code = "OK"

	#update the status
	log_output = log_output + "HTTP/1.1 " + str(status) + " " +status_code + "\r\n"

	#update date
	date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
	log_output = log_output + "Date: " + date + "\r\n"

	#add the last modified feild if it isnt an error
	if status != 501 and status != 404:
		log_output = log_output + "Last-Modified: " + last_modified + "\r\n"

	#update size (file size)
	size = str(os.path.getsize(file_location))
	log_output = log_output + "Content-Length: " + size + "\r\n"

	#content type
	#html txt jpg pdf
	content = ""
	if file_location.endswith('.txt'):
		content = "txt"
	elif file_location.endswith('.jpg'):
		content = "jpg"
	elif file_location.endswith('.pdf'):
		content = "pdf"
	elif file_location.endswith('.html'):
		content = "html"
	log_output = log_output + "Content-Type: " + content + "\r\n"

	#connection type if 501 connection = keep-alive
	if status == 501:
		connection = "keep-alive"
	else:
		temp = re.search('Connection: (.*)\r\n',message)
		connection = temp.group(1).strip()
	log_output = log_output + "Connection: " + connection + "\r\n"

	return(log_output)

#creates and writes the logging info
def output(log_output, log_file):

	#If it is std out, print
	if log_file == 'standard output':
		print(log_output)
	#If it is a log  file, open and print it there
	else:
		f = open("./"+log_file,"a")
		f.write(log_output+"\n")
	return

#Creates and sendss the response
def respond(log_output, connected_socket, file_name):
	
	#Open the file to send
	with open("./" + file_name, "rb") as f:
		file = f.read()

	#Create the HTTP response
	resp = log_output + "\r\n"
	resp_in_b = str.encode(resp) + file

	#send the HTTP response
	connected_socket.send(resp_in_b)
	
	return

#allow for up to ten users
sockfd.listen(NUM_USERS)
for itr in range(NUM_USERS):
	#create the socket thread, make sure daemon is false, so we can keep running
	sock_thread = threading.Thread(target = Socket_Thread)
	sock_thread.daemon = False
	sock_thread.start()