import SimpleHTTPServer
import BaseHTTPServer
import subprocess
import datetime
import urllib
import base64
import signal
import json
import sys
import cgi
import os

def git_Add(filename, repo):
	action = ['add']
	params = [filename]
	call_git( action, params, repo )

def git_Commit(message, repo):
	action = ["commit"]
	params = ["-m", message]
	call_git( action, params, repo )

def git_Init(repo):
	action = ["init"]
	params = [repo]
	call_git( action, params )
	
def call_git( action, params, repo="." ):
	git = ['git']
	subprocess.call( git + action + params, cwd=repo )

def get_repoList(path):
	result = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
	return result

class HTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

	def split_query(self, path):
		path = self.path.split('?',1)[0]
		path = path.split('#',1)[0]
		leading_character = '/' if path[0] == '/' else ''
		path = os.path.normpath(urllib.unquote(path))
		words = path.split('/')
		return filter(None, words)

	def get_mimetype(self, filename):
		ctypes = {
			".html":"text/html",
			".gif":"image/gif",
			".png":"image/png",
			".js":"application/javascript",
			".css":"text/css",
			".m4v":"video/x-m4v"
		}
		
		base, ext = os.path.splitext(filename)
		ext = ext.lower()

		return ctypes.has_key(ext) and ctypes[ext] or "text/plain"

	def send_json_directory(self):
		directory = json.dumps( get_repoList(".") )
		self.send_response(200)
		self.send_header("Content-type", "application/json")
		self.send_header("Content-Length", len(directory))
		self.end_headers()
		self.wfile.write(directory)
	
	def send_ping(self):
		self.send_response(200)

	def send_file(self,query):
		filepath = os.path.join( os.getcwd(), *query )
		mimetype = self.get_mimetype(filepath)

		if not os.path.isfile(filepath):
			self.send_error(404, filepath + " " + "is not a file")
			return

		f = open(filepath,"rb")
		fs = os.fstat(f.fileno())
		self.send_response(200)
		self.send_header("Content-type", mimetype)
		self.send_header("Content-Length", str(fs.st_size))
		self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
		self.send_header("Cache-Control","no-cache")
		self.end_headers()
		self.copyfile(f, self.wfile)
		f.close()

	def do_GET(self):
		print( self.path )
		query = self.split_query(self.path)

		if len(query) == 0:
			query.append("editor.html");

		if query[0] == "list":
			self.send_json_directory()
		elif query[0] == "ping":
			self.send_ping()
		else:
			self.send_file(query)

	def do_PUT(self):
		query = self.split_query(self.path)
		filepath = os.path.join( os.getcwd(), *query )
		repopath, filename = os.path.split(filepath) 
		already_present = os.path.isfile(filepath)

		if not already_present:
			git_Init(repopath)

		f = open(filepath,"wb")
		size = int( self.headers['Content-Length'] )
		f.write( self.rfile.read(size) )
		f.close()

		git_Add(filename, repopath)
		git_Commit("-no message-", repopath)

		if already_present:
			self.send_response(200) #OK, modified
		else:
			self.send_response(201) #OK, created

def signal_handler(signal, frame):
	sys.exit(0)

def start_server():
	signal.signal(signal.SIGINT, signal_handler)
	server_address = ("127.0.0.1", 8080)
	print(server_address)
	server = BaseHTTPServer.HTTPServer(server_address, HTTPRequestHandler)
	server.serve_forever()

if __name__ == "__main__":
	start_server()
