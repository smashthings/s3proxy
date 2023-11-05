# s3proxy

s3proxy is a web interface for S3 buckets providing access to S3 objects with a web service rather than via the AWS Console, API calls or other methods.

**Use Cases**

- Access to assets in internal environments without using AWS API calls
- An internal asset server
- A faster interface than AWS S3, which seems to be getting slower and more annoying with time
- Quick S3 asset review without logging in (ie, using CLI credentials rather than a full login process)

## Configuration

If you don't provide any configuration then on start the server will ask you to provide the required credentials and target bucket:

<p align="center">
  <img src="./other/settings.png">
</p>

If you get any issues then you'll get friendly notifications telling you what went wrong, otherwise you'll get a link straight to your bucket

<p align="center">
  <img src="./other/bucket.png">
</p>

## Usage

Regular files are available to download with the `Download` links. "Directories" are not actually directories in S3 world, they're prefixes to object names. If there's a common prefix you'll get a `List` option rather than a download. When you click on that the page will repopulate with objects that only have that prefix.

It'll feel just like a file system browser but in the background there's that framing of prefixes vs directories.

#### Direct Proxying

Each object in the bucket can be accessible via `/fetch/<object-name>`. For example, if you had a company logo in your bucket at `s3://companybucket.com/company-images/logo.png` then after targeting s3-proxy to the bucket `companybucket.com` and giving it the required credentials you can hit `http://s3proxy.local/fetch/company-images/logo.png` and get your logo.



You can either provide access key + secret or mount a credentials file and provide a profile to use. If you're mounting your credentials and config files you'll need to target the path for your mount with the below AWS variables.

Aside from the settings page, you can preseed the container with the same relative combination of AWS variables.

## Variables

#### s3_proxy

```
TARGET_BUCKET => The name of the bucket to target. If you don't provide this as an environment variable to the container then you'll get the settings page
```

Additionally you may want to set common headers for stuff like CORS. You can do this with a prefixed environment variable: **S3PROXYHEADER_**. So for allowing for GET, HEAD and OPTIONS requests from any origin:

> S3PROXYHEADER_Access_Control_Allow_Origin="*"
> S3PROXYHEADER_Access_Control_Allow_Methods="GET,HEAD,OPTIONS"
> S3PROXYHEADER_Access_Control_Max_Age="86400"

Underscores after S3PROXYHEADER_ are turned into hyphens.

#### AWS

```
# Either:

AWS_ACCESS_KEY_ID => Your user key ID
AWS_SECRET_ACCESS_KEY => Your user secret

# -or-

AWS_DEFAULT_PROFILE => The AWS profile to use
AWS_SHARED_CREDENTIALS_FILE => The location where you've mounted your credentials file with the desired profile
AWS_CONFIG_FILE => The location where you've mounted your config file with the desired profile

# -and optionally-

AWS_DEFAULT_REGION => Set this to your bucket's region if you're having issues

```

## Deployment

As a container driven application you can run this via the prebuilt image at smasherofallthings/s3proxy. Naturally, this lends itself well to Kubernetes and you can find jinja templates for manifests under the k8s directory in this repo.

