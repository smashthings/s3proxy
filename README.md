# s3proxy

s3proxy is a web interface for S3 buckets providing access to S3 objects with a web service rather than via the AWS Console, API calls or other methods.

**Use Cases**

- Access to assets in internal environments without using AWS API calls
- An internal asset server
- A faster interface than AWS S3, which seems to be getting slower and more annoying with time
- Quick S3 asset review without logging in (ie, using CLI credentials rather than a full login process)

## Configuration

This is a container centric application so is configured with two required environment variables.

TARGET_BUCKET => The name of the bucket to proxy
BUCKET_AWS_REGION => The region of the S3 bucket

For other optional configuration all the AWS environment variables apply as the s3proxy is using boto3 underneath, for example AWS_PROFILE will change the profile to use, etc.

Additionally you may want to set common headers for stuff like CORS. You can do this with a prefixed environment variable: **S3PROXYHEADER_**. So for allowing for GET, HEAD and OPTIONS requests from any origin:

> S3PROXYHEADER_Access_Control_Allow_Origin="*"
> S3PROXYHEADER_Access_Control_Allow_Methods="GET,HEAD,OPTIONS"
> S3PROXYHEADER_Access_Control_Max_Age="86400"

Underscores after S3PROXYHEADER_ are turned into hyphens.

## Routes

*/* \
The index page which provides the HTML page for human focused browsing. The buttons make calls to the inbuilt API to populate with data

*/templates/<path>* \
Contains static frontend content. Naming convention a hold over from Flask

*/get-objects* \
The API endpoint to get a json response listing objects and prefixes based on the prefix, delimiter and token provided

*/fetch/<path>* \
A direct proxy for the underlying s3 key. So if on the bucket that you configure there's an object under key 'first-level/second-level/object-you-want.thing' then you can access it via the proxy at https://domain.s3proxy.com/fetch/first-level/second-level/object-you-want.thing

*/healthcheck* \
A healthcheck

## Deployment

As a container driven application you can run this via the prebuilt image at smasherofallthings/s3proxy. Naturally, this lends itself well to Kubernetes and you can find jinja templates for manifests under the k8s directory in this repo.

