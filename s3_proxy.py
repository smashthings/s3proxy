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
# Settings Class

class AppSettings():
  def __init__(self, targetBucket:str=None, awsRegion:str=None, awsProfile:str=None, awsAccessKey:str=None, awsSecretKey:str=None):
    self.targetBucket = targetBucket
    self.awsRegion = awsRegion
    self.awsAccessKey = awsAccessKey
    self.awsSecretKey = awsSecretKey
    self.awsProfile = awsProfile
    self.status = "Awaiting tests"

    if not self.targetBucket:
      self.status = "The bucket name was not provided!"
      self.Ready = False
      return
    if self.awsAccessKey and self.awsAccessKey:
      self.awsSession = boto3.Session(
        aws_access_key_id=self.awsAccessKey,
        aws_secret_access_key=self.awsSecretKey,
        region_name=self.awsRegion
        )
      self.status = "Session configured with keys"
    elif self.awsProfile:
      self.awsSession = boto3.Session(
        profile_name=self.awsProfile,
        region_name=self.awsRegion
        )
      self.status = f"Session configured with profile name '{awsProfile}'"

    self.awsAccountNumber = None
    self.s3Client = self.awsSession.client('s3')
    self.stsClient = self.awsSession.client('sts')
    self.Ready = False

  def check_access(self):
    if not self.targetBucket:
      Log(f"AppSettings.check_access(): Target bucket setting not provided!")
      return False
    res = self.check_aws_access()
    if res == False:
      return False
    res2 = self.check_bucket_access()
    if res2 == False:
      return False
    return True

  def check_aws_access(self):
    try:
      c = self.stsClient.get_caller_identity()
      self.awsAccountNumber = c.get('Account')
      return True
    except Exception as e:
      Log(f"AppSettings.check_aws_access(): Failed to call STS with stashed AWS session with the following exception:")
      self.status = "Failed STS call with exception"
      traceback.print_exc()
      return False

  def check_bucket_access(self):
    if not self.awsAccountNumber:
      res = self.check_aws_access()
      if not res:
        return False
    try:
      s3Res = self.s3Client.get_bucket_acl(Bucket=self.targetBucket)
      if not self.awsRegion:
        regionReq = self.s3Client.get_bucket_location(Bucket=self.targetBucket)
        self.awsRegion = regionReq['LocationConstraint']
      self.Ready = True
      self.status = "Ready to serve"
      return True
    except Exception as e:
      self.status = f"Failed S3 access call to bucket '{self.targetBucket}'"
      Log(f"AppSettings.check_bucket_access(): Failed to fetch the bucket ACL for bucket '{self.targetBucket}' with the following exception:")
      traceback.print_exc()
      return False
  def print_state(self):
    print(f'''State => {self.status}
Bucket => {self.targetBucket if self.targetBucket else '<none>'}
Region => {self.awsRegion if self.awsRegion else '<none>'}
AWS Profile => {self.awsProfile if self.awsProfile else '<none>'}
AWS Key ID => {self.awsAccessKey if self.awsAccessKey else '<none>'}
AWS Secret ID => {'************' if self.awsSecretKey else '<none>'}
''')

##############################################
# Variables

scriptDir = os.path.dirname(os.path.realpath(__file__))
allTemplates = {}
jenv = jinja2.Environment(loader=jinja2.BaseLoader())

LoadedAppSettings = AppSettings(
  targetBucket=os.getenv("TARGET_BUCKET") if "TARGET_BUCKET" in os.environ else None,
  awsRegion=os.getenv("AWS_DEFAULT_REGION") if "AWS_DEFAULT_REGION" in os.environ else None,
  awsAccessKey=os.getenv("AWS_ACCESS_KEY_ID") if "AWS_ACCESS_KEY_ID" in os.environ else None,
  awsSecretKey=os.getenv("AWS_SECRET_ACCESS_KEY") if "AWS_SECRET_ACCESS_KEY" in os.environ else None,
  awsProfile=os.getenv("AWS_PROFILE") if "AWS_PROFILE" in os.environ else None,
)
loaded = LoadedAppSettings.check_access()
if not loaded:
  Log(f"Main(): Failed to load application settings, will be serving a settings page until full settings are provided!")
  LoadedAppSettings.print_state()
else:
  Log(f'Running with settings:')
  LoadedAppSettings.print_state()

commonHeaders = {}

for f in os.environ:
  if f[0:14] == "S3PROXYHEADER_":
    commonHeaders[f[14:].replace('_', "-")] = os.environ[f]

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
    "Bucket": LoadedAppSettings.targetBucket,
    "Delimiter": delimiter,
    "Prefix": prefix
  }
  if continueToken != "":
    reqSettings["ContinuationToken"] = continueToken
  res = LoadedAppSettings.s3Client.list_objects_v2(**reqSettings)
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
# Middleware

def mSettingsCheck():
  if LoadedAppSettings.Ready == False:
    Log(f"mSettingsCheck(): Found current LoadedAppSettings to not be ready:")
    LoadedAppSettings.print_state()
    return allTemplates["settings.html"].render(), False
  else:
    return None, True

##############################################
# Handlers

def rHealthCheck():
  return {
    'status': 'online'
  }

def rStaticContent(path:str=""):
  settingsRes, ok = mSettingsCheck()
  if not ok:
    return settingsRes
  if path == "":
    t = f'{scriptDir}/dist{flask.request.full_path.rstrip("?")}'
  else:
    t = f'{scriptDir}/dist/{path}'
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
  settingsRes, ok = mSettingsCheck()
  if not ok:
    return settingsRes
  return allTemplates["index.html"].render(bucket_name=LoadedAppSettings.targetBucket, region=LoadedAppSettings.awsRegion, account_number=LoadedAppSettings.awsAccountNumber)

def rFetchObject(key:str):
  settingsRes, ok = mSettingsCheck()
  if not ok:
    return settingsRes
  try:
    thing = LoadedAppSettings.s3Client.get_object(Bucket=LoadedAppSettings.targetBucket, Key=key)
    if not thing:
      return ResponseMaker(404, None, f"Static content at '{path}' not found on this bucket")
    res = flask.make_response()
    res.set_data(thing['Body'].read())
    res.content_type = thing['ContentType']
    res.headers.add("Access-Control-Allow-Origin", "*")
    res.headers.add("Access-Control-Request-Method", "GET")
    res.status_code = 200
    return res
  except Exception as e:
    traceback.print_exc()
    return ResponseMaker(500, None, f"Failed to fetch object at key '{key}', exception raised when attempting to handle it")
    return res

def rGetObjects():
  settingsRes, ok = mSettingsCheck()
  if not ok:
    return settingsRes
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

def rUpdateSettings():
  req = flask.request
  try:
    resBody = req.get_json(force=True)
    if not isinstance(resBody, dict):
      return ResponseMaker(400, None, reason=f"This endpoint only accepts a dictionary. Your body content is a {type(resBody)}")
    for k in resBody.keys():
      if k not in ('targetBucket',
        "awsProfile",
        "awsAccessKey",
        "awsSecretKey",
        "awsProfile",
        "awsRegion",
      ):
        return ResponseMaker(400, None, reason=f"Provided value '{k}' not an acceptable configuration!")
    newSettings = AppSettings(**resBody)
    ok = newSettings.check_access()
    if ok:
      global LoadedAppSettings
      LoadedAppSettings = newSettings
      Log(f"rUpdateSettings(): Configured a new set of updated settings!")
      LoadedAppSettings.print_state()
      return flask.redirect("/", 302)
    else:
      return ResponseMaker(400, None, reason=f"The configuration you provided failed either AWS or S3 access with the following error: '{newSettings.status}'")
    return ResponseMaker(200, v)
  except Exception as e:
    traceback.print_exc()
    return ResponseMaker(500, None, reason=f"Failed to update settings with error: {e}")


##############################################
# The full routing list
RouteMapping("/healthcheck", rHealthCheck, ["GET"])
RouteMapping("/", rIndexPage, ["GET"])
RouteMapping("/fetch/<path:key>", rFetchObject, ["GET"])
RouteMapping("/get-objects", rGetObjects, ["POST"])
RouteMapping("/settings", rUpdateSettings, ["POST"])

##############################################
# Main

s3Proxy = flask.Flask("s3Proxy")

if commonHeaders:
  @s3Proxy.after_request
  def commonResponseHeaders(res):
    for f in commonHeaders:
      res.headers[f] = commonHeaders[f]
    return res

Log("Loading all Templates...")
allTemplates["index.html"] = LoadTemplate(f"{scriptDir}/dist/index.html")
allTemplates["settings.html"] = LoadTemplate(f"{scriptDir}/dist/settings.html")
for f in allTemplates.keys():
  Log(f'- {f}')

Log("Loading routes...")
for r in RouteList:
  s3Proxy.route(r.route, methods=r.methods)(r.handler)
  Log(f'- {r.route}')

s3Proxy.after_request(LogResponses)

Log("Starting server...")
waitress.serve(s3Proxy, host="0.0.0.0", port=3000)
