# Serverless Continuous Delivery and Hosting for Hugo

![Hugo](https://raw.githubusercontent.com/spf13/hugo/master/docs/static/img/hugo-logo.png)

If you're interested in hosting a [Hugo](https://gohugo.io/) generated website but don't want to worry about setting up a bunch of pesky infrastructure, look no further! This starter kit will get you up and running in Amazon Web Services in no time. It utilizes AWS CloudFormation to provision a continuous delivery pipeline that will update your website on every commit to your repository.

This is achieved by provisioning the following infrastructure in AWS:

1. S3 Bucket to host your static files
2. Cloudfront Content Delivery Network
3. Lambda Function to run Hugo and publish output
4. API Gateway that listens to your GitHub events and triggers the Lambda

# How do I get started?

	pip install -r requirements.txt
	./deploy.py /path/to/my/.hugo-cd.yml

This script will:
 1. Replace some variables in the lambda function package
 2. Zip it up and upload it to s3 
 3. Run the `cloudformation.json` stack 

*You'll have to check your [CloudFormation Console](https://console.aws.amazon.com/cloudformation/home#stacks?filter=active) to check in on the status. Unfortunately, running the stack from scratch takes around 30 minutes (the majority of that time is waiting for CloudFront to propogate content to it's edge locations).*

*I'm assuming you've already set up the [AWS CLI](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-set-up.html).*

Once the stack is complete, you'll want to create a new WebHook on your GitHub repo. Point it to the "WebhookEndpoint" value (found in the "Stack Detail" view). No password is required.

# Configuration

If you're wondering where that configuration above came from and what it should contain, look no further! I personally keep the
configuration file in the root of my Hugo site directory. Feel free to keep it wherever you want. Now, for the contents...

```YAML
# used to drive AWS resource naming. enter all caveats associated with AWS resource naming here.
# most notably, it must be lowercase alphanumeric.
stack_name: thebbs

# the final URL generated will take the form <subdomain><hosted_zone>
hosted_zone: example.com

# optional value. defaults to empty string. if specified, please include trailing .
subdomain: ""

# repo to pull your site from
git_url: https://github.com/myuser/myrepo

# path to the root Hugo sources folder inside your git archive
# to test, download https://github.com/myuser/myrepo/master/archive.zip
path_to_site: myrepo-master/

# this is an optional value. defaults to cloudfront's cert.
iam_certificate_id: ASCAJE7VY5QEFGQNNK2EG
```

## TODO:

1. Add support for Route53 Hosted Zones.
1. Figure out better integration between AWS and GitHub.
  1. Is there a way to git clone? I want to avoid pulling the .zip into the lambda function.
  1. Secure API Gateway endpoint. We can wait for GitHub to add the functionality, or do some magic to utilize GitHub's secret parameter.
  1. Filter events in lambda function. Right now we build on every event in the repo. It'd be nice to only build on commits to master.
1. Generate SSL Certificate for the stack. Perhaps integration with AWS Certificate Manager. Perhaps LetsEncrypt.
1. (low priority) Add CloudFront Origin Access Identity to further lock down S3 resources
1. Parameterize git branch
1. Clean up lambda function
  1. Provide better feedback/logs to the caller
  1. Factor the JS more cleanly
