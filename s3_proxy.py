#!/usr/bin/env python3

import boto3
import waitress
import flask
import jinja2
import mimetypes
import datetime
import os
import uuid
import json
import traceback

##############################################
# Helpers

def Log(message, quit:bool=False, quitWithStatus:int=1, AlwaysVerbose:bool=True):
  if AlwaysVerbose == False and VerboseSetting == False:
    return
  if type(message) is dict:
    print(f'<{TimeStamp()}> - ' + "\n => ".join([k + ": " + str(message[k]) for k in message]))
  else:
    print(f'<{TimeStamp()}> - {message}')

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
  t = jenv.from_string(fData)
  return t

def FmtSize(num, suffix='B'):
  for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
    if abs(num) < 1024.0:
      return "%3.1f%s%s" % (num, unit, suffix)
    num /= 1024.0
  return "%.1f%s%s" % (num, 'Yi', suffix)

def ResponseMaker(statusCode:int, data, reason:str=""):
  if statusCode > 399 and reason == "":
    raise Exception(f"responseMaker(): Received an error status code without a reason, statusCode: '{statusCode}', reason: '{reason}', data '{data}'")
  returning = {
    "status": statusCode
  }
  if data:
    returning["response"] = data
  
  if reason:
    returning["reason"] = reason

  return (json.dumps(returning), statusCode)

##############################################
# Variables

scriptDir = os.path.dirname(os.path.realpath(__file__))
allTemplates = {}
targetBucket = os.getenv("TARGET_BUCKET") if "TARGET_BUCKET" in os.environ else ""
awsRegion = os.getenv("BUCKET_AWS_REGION") if "BUCKET_AWS_REGION" in os.environ else ""
awsAccountNumber = boto3.client('sts').get_caller_identity().get('Account')
jenv = jinja2.Environment(loader=jinja2.BaseLoader())

Log(f'''Running with settings:
- Bucket Name => {targetBucket}
- AWS Region => {awsRegion}
- AWS Account Number => {awsAccountNumber}''')

s3Client = boto3.client("s3", region_name=awsRegion)

Log("Checking for required environment variable settings:")

if targetBucket == "":
  Log("Did not find environment variable TARGET_BUCKET populated, exiting!", quit=True)

if awsRegion == "":
  Log("Did not find environment variable BUCKET_AWS_REGION populated, exiting!", quit=True)


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
    "time": TimeStamp(),
    "status": res.status_code,
    "clientIp": req.remote_addr,
    'routingExceptions': str(req.routing_exception) if req.routing_exception else "none",
    "origin": str(req.origin).lower(),
    "host": req.host,
    "fullPath": req.full_path,
    "ssl": "true" if req.is_secure else "false",
    "scheme": req.scheme
  }

  Log(loggingDetails)
  return res

def GetObjects(prefix:str="", continueToken:str="", delimiter:str="/"):
  reqSettings = {
    "Bucket": targetBucket,
    "Delimiter": delimiter,
    "Prefix": prefix
  }
  if continueToken != "":
    reqSettings["ContinuationToken"] = continueToken
  res = s3Client.list_objects_v2(**reqSettings)
  pruned = {
    "objs": [],
    "token": ""
  }
  if "CommonPrefixes" in res:
    for f in res['CommonPrefixes']:
      pruned['objs'].append({
        "name": f["Prefix"],
        "last_modified": "-",
        "size": "-",
        "link": f"javascript:window.s3Proxy.functions.setPrefix('{f['Prefix']}');window.s3Proxy.functions.getObjects()"
      })
  if "Contents" in res:
    for f in res['Contents']:
      if f["Key"] != prefix:
        pruned['objs'].append({
          "name": f["Key"],
          "last_modified": f["LastModified"].strftime("%Y-%m-%d %H:%M:%S"),
          "size": FmtSize(f["Size"]),
          "link": f"/fetch/{f['Key']}"
        })

  if 'IsTruncated' in res and res['IsTruncated'] and 'NextContinuationToken' in res:
    pruned['token'] = res["NextContinuationToken"]
  
  return pruned

##############################################
# Handlers

def rHealthCheck():
  return {
    'status': 'online'
  }

def rStaticContent(path:str=""):
  if path == "":
    t = f'{scriptDir}/templates{flask.request.full_path.rstrip("?")}'
  else:
    t = f'{scriptDir}/templates/{path}'
  if not os.path.exists(t):
    return ResponseMaker(404, None, f"Static content at '{t}' not found on this server")
  try:
    res = flask.make_response()
    with open(t, "rb") as f:
      res.set_data(f.read())
    res.status_code = 200
    t = mimetypes.guess_type(t)
    res.content_type = t if t is not None else "application/octet-stream"
    return res
  except Exception as e:
    traceback.print_exc()
    return ResponseMaker(500, None, f"Failed to read file at path '{t}', file exists but exception raised when attempting to return it")

def rIndexPage():
  return allTemplates["index.html"].render(bucket_name=targetBucket, region=awsRegion, account_number=awsAccountNumber)

def rFetchObject(key:str):
  try:
    thing = s3Client.get_object(Bucket=targetBucket, Key=key)
    if not thing:
      return ResponseMaker(404, None, f"Static content at '{path}' not found on this bucket")
    res = flask.make_response()
    res.set_data(thing['Body'].read())
    res.content_type = thing['ContentType']
    res.status_code = 200
    return res
  except Exception as e:
    traceback.print_exc()
    return ResponseMaker(500, None, f"Failed to fetch object at key '{key}', exception raised when attempting to handle it")
    return res

def rGetObjects():
  req = flask.request
  try:
    resBody = req.get_json(force=True)
    v = GetObjects(
      prefix=resBody['prefix'] if 'prefix' in resBody else "",
      delimiter=resBody['delimiter'] if 'delimiter' in resBody else "/",
      continueToken=resBody['token'] if 'token' in resBody else ""
      )    
    return ResponseMaker(200, v)
  except Exception as e:
    traceback.print_exc()
    return ResponseMaker(500, None, reason=f"Failed to parse json in request with error {e}")

##############################################
# The full routing list
RouteMapping("/healthcheck", rHealthCheck, ["GET"])
RouteMapping("/", rIndexPage, ["GET"])
RouteMapping("/templates/<path>", rStaticContent, ["GET"])
RouteMapping("/fetch/<path:key>", rFetchObject, ["GET"])
RouteMapping("/get-objects", rGetObjects, ["POST"])
RouteMapping("/favicon.ico", rStaticContent, ["GET"])

##############################################
# Main

s3Proxy = flask.Flask("s3Proxy")

Log("Loading all Templates...")
allTemplates["index.html"] = LoadTemplate(f"{scriptDir}/templates/index.html")
for f in allTemplates.keys():
  Log(f'- {f}')

Log("Loading routes...")
for r in RouteList:
  s3Proxy.route(r.route, methods=r.methods)(r.handler)
  Log(f'- {r.route}')

s3Proxy.after_request(LogResponses)

Log("Starting server...")
waitress.serve(s3Proxy, host="0.0.0.0", port=5000)
