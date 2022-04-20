#!/usr/bin/env python3

import boto3
import waitress
import flask
import jinja2
import mimetypes
import os

##############################################
# Helpers

def Log(message, quit:bool=False, quitWithStatus:int=1, AlwaysVerbose:bool=True):
  if AlwaysVerbose == False and VerboseSetting == False:
    return
  if type(message) is dict:
    logToFile(LoggingLocation, f'<{TimeStamp()}> - ' + "\n => ".join([k + ": " + str(message[k]) for k in message]))
  else:
    logToFile(LoggingLocation, f'<{TimeStamp()}> - {message}')

  if quit or quitWithStatus > 1:
    exit(1 * quitWithStatus)

def TimeStamp():
  return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")

def LoadTemplate(fileLocation:str):
  if not os.path.exists(fileLocation):
    raise Exception(f"Template file at location {fileLocation} does not exist!")
  fData = None
  with open(fileLocation) as f:
    fData = f.read()
  t = jinja2.Template(fData)
  return t


##############################################
# Variables

scriptDir = os.path.dirname(os.path.realpath(__file__))
allTemplates = {}
targetBucket = os.getenv("TARGET_BUCKET") if "TARGET_BUCKET" in os.environ else ""
awsRegion = os.getenv("AWS_REGION") if "AWS_REGION" in os.environ else ""

app_logging.Log("Checking for required environment variable settings:")

if targetBucket == "":
  Log("Did not find environment variable TARGET_BUCKET populated, exiting!", quit=True)

if awsRegion == "":
  Log("Did not find environment variable AWS_REGION populated, exiting!", quit=True)


##############################################
# Routing
RouteList = []

class RouteMapping():
  def __init__(self, route:str, handler, methods:list = [], wrappers:list = []):
    self.route = route.rstrip("/") if route != "/" else "/"
    self.methods = methods
    self.wrappers =  wrappers

    workingHandler = handler
    if self.wrappers:
      for w in self.wrappers:
        workingHandler = w(workingHandler)
    self.handler = workingHandler
    RouteList.append(self)

def LogResponses(res:flask.wrappers.Response):
  '''Logs basic details about completed requests and adds a UUID header for tracking. UUID header is S3Proxy-UUID'''

  res.headers['S3Proxy-UUID'] = uuid.uuid4()
  req = flask.request

  loggingDetails = {
    "type": "Response",
    "time": app_logging.TimeStamp(),
    "status": res.status_code,
    "clientIp": req.remote_addr,
    'routingExceptions': str(req.routing_exception) if req.routing_exception else "none",
    "origin": str(req.origin).lower(),
    "host": req.host,
    "fullPath": req.full_path,
    "ssl": "true" if req.is_secure else "false",
    "scheme": req.scheme
  }

  app_logging.Log(loggingDetails)
  return res

##############################################
# Handlers

def rHealthCheck():
  return {
    'status': 'online'
  }

def rStaticContent(path):
  res = flask.make_response()
  if not os.path.exists(path):
    res.status_code = 404
    res.content_type = "application/json"
    res.set_data(json.dumps(
      {
        'status': 404,
        'reason': f"Static content at '{path}' not found on this server"
      }))
    return res

  try:
    with open(path) as f:
      res.set_data(f.read())
    res.status_code = 200
    t = mimetypes.guess_type(path)
    res.content_type = t if t is not None else "application/octet-stream"
    return res
  except:
    res.status_code = 500
    res.content_type = "application/json"
    res.set_data(json.dumps(
      {
        'status': 500,
        'reason': f"Failed to read file at path '{path}', file exists but exception raised when attempting to return it"
      }))
    return res

def rIndexPage():
  return flask.render_template('index.html')

def rFetchObject(key:str):
  s3Client = boto3.client("s3")

  obj = s3.Object(targetBucket, key)
  if not obj:
    return 
  obj.get()['Body'].read().decode('utf-8') 

def rListObjects():
  s3Client = boto3.client("s3")

  obj = s3.Object(targetBucket, key)
  obj.get()['Body'].read().decode('utf-8') 

##############################################
# The full routing list
RouteMapping("/healthcheck", rHealthCheck, ["GET"])
RouteMapping("/", rConfigPage, ["GET"])
RouteMapping("/output.css", rStaticContent, ["POST"])

##############################################
# Main

s3Proxy = flask.Flask("s3Proxy")

app_logging.Log("Loading VCL Template...")
allTemplates["vcl"] = LoadTemplate(f"{scriptDir}/templates/default.vcl")
allTemplates["nginx"] = LoadTemplate(f"{scriptDir}/templates/nginx.conf")

app_logging.Log("Loading routes...")
for r in RouteList:
  s3Proxy.route(r.route, methods=r.methods)(r.handler)

s3Proxy.after_request(LogResponses)

app_logging.Log("Starting server...")
waitress.serve(s3Proxy, host="0.0.0.0", port=5000)
