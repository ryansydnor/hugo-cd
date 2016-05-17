#!/usr/bin/env  python

from jinja2 import Environment, FileSystemLoader
import sys
import yaml
import boto3
import urllib
import os
import zipfile
import tarfile
import shutil
import subprocess

def walk_files_and(path, func):
    for root, dirs, files in os.walk(path):
        for file in files:
        	func(os.path.join(root, file))

def generate_zip_file(site_name):
	print "Generating Zip File."
	path = '/tmp/%s.zip' % site_name
	zipf = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
	# we don't want to zip the outer folder, just the contents
	os.chdir('lambda')
	walk_files_and('.', lambda p: zipf.write(p))
	zipf.close()
	os.chdir('..')
	print "Zip File Generated: %s" % path
	return path


def upload_zip_file(site_name, zip_path):
	print "Uploading Zip File to S3."
	bucket_name, obj_name = '%s-lambda-func' % site_name, '%s.zip' % site_name
	s3 = boto3.resource('s3')
	s3.create_bucket(Bucket=bucket_name)
	s3.Object(bucket_name, obj_name).put(Body=open(zip_path, 'rb'))
	print "Zip File uploaded to bucket %s as %s" % (bucket_name, obj_name) 
	return bucket_name, obj_name

def npm_install():
	print "Running NPM Install."
	print subprocess.check_output(['npm', 'install'], cwd='./lambda')

def download_hugo():
	hugo_version = "0.15"
	hugo_binary = "hugo_%s_linux_amd64" % hugo_version
	hugo_url = "https://github.com/spf13/hugo/releases/download/v%s/%s.tar.gz" % (hugo_version, hugo_binary)
	print "Downloading Hugo from: %s" % hugo_url
	urllib.urlretrieve(hugo_url, '/tmp/hugo.tar.gz')
	with open('/tmp/hugo.tar.gz', 'r') as h:
		tar = tarfile.open(fileobj=h, mode="r|*")
		tar.extractall('/tmp')
		tar.close()
	shutil.move('/tmp/%s/%s' % (hugo_binary, hugo_binary), './lambda/hugo')
	os.remove('/tmp/hugo.tar.gz')
	shutil.rmtree('/tmp/%s' % hugo_binary)
	print "Hugo extracted to lambda/"

def read_config(config_file_path):
	print "Reading config."
	with open(config_file_path) as f:
		config = yaml.safe_load(f)
	return config

def template_files(config):
	print "Templating Files."
	env = Environment(loader=FileSystemLoader('.'))
	
	def template_file(path):
		filename, file_extension = os.path.splitext(path)
		if file_extension == '.j2':
			template = env.get_template(path)
			print "Templating %s" % filename
			with open(filename, 'w') as rf:
				rf.write(template.render(**config))
	
	walk_files_and('lambda', template_file)

def create_cloudformation_stack(site_name, hosted_zone, subdomain, cert_id, lambda_bucket, lambda_key):
	client = boto3.client('cloudformation')
	with open ('./cloudformation.json', 'r') as t:
		template_body = t.read()

	params = {
		'StackName': site_name,
		'TemplateBody': template_body,
		'Parameters': [
				{
					"ParameterKey": "WebsiteS3Bucket",
					"ParameterValue": site_name,
					"UsePreviousValue": False
				},
				{
					"ParameterKey": "HostedZone",
					"ParameterValue": hosted_zone,
					"UsePreviousValue": False
				},
				{
					"ParameterKey": "LambdaS3Bucket",
					"ParameterValue": lambda_bucket,
					"UsePreviousValue": False
				},
				{
					"ParameterKey": "LambdaS3Key",
					"ParameterValue": lambda_key,
					"UsePreviousValue": False
				},
				{
					"ParameterKey": "IAMCertificateId",
					"ParameterValue": cert_id,
					"UsePreviousValue": False
				},
				{
					"ParameterKey": "SubDomain",
					"ParameterValue": subdomain,
					"UsePreviousValue": False
				}
			],
		'Capabilities': [
			'CAPABILITY_IAM'
		],
		'Tags': [
					{
						'Key': 'static-site-name',
						'Value': site_name
					}		
				]
	}
	print "Running cloudformation stack."
	message = "Cloudformation stack %s. Check AWS console for more info here: https://console.aws.amazon.com/cloudformation/home?#/stacks"
	try:
		response = client.create_stack(**params)
		print message % 'created'
	except Exception as e:
		if e.response['Error']['Code'] == 'AlreadyExistsException':
			response = client.update_stack(**params)
			print message % 'updated'
		else:
			print "Unexpected error occured."
			print e


def main(config_file_path):
	config = read_config(config_file_path)
	template_files(config)
	npm_install()
	download_hugo()
	path = generate_zip_file(config['stack_name'])
	bucket, key = upload_zip_file(config['stack_name'], path)
	create_cloudformation_stack(config['stack_name'], 
								config['hosted_zone'], 
								config.get('subdomain', ""),
								config.get('iam_certificate_id', ""), 
								bucket, 
								key)

if __name__ == '__main__':
	if len(sys.argv) < 2:
		raise ValueError("Please specify config path")
	config_file_path = sys.argv[1] 
	main(config_file_path)