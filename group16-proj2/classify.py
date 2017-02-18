import json
import urllib2
import base64
import sys
import numpy as np
import os
from subprocess import call
import re
import collections

from subprocess import Popen, PIPE, STDOUT


def probe(siteURL, query, accountKey):
	bingUrl = 'https://api.datamarket.azure.com/Data.ashx/Bing/SearchWeb/v1/Composite?Query=%27site%3a'+siteURL+'%20'+query+'%27&$top=4&$format=Json'
	accountKeyEnc = base64.b64encode(accountKey + ':' + accountKey)
	headers = {'Authorization': 'Basic ' + accountKeyEnc}
	req = urllib2.Request(bingUrl, headers = headers)
	response = urllib2.urlopen(req)
	return json.loads(response.read())['d']['results'][0]

# return a sample dictionary which maps node name to a set of URLs
def classify(siteURL, tes, tec, accountKey):
	print "Classifying..."
	category = []
	sample = {}
	rootSample = set()
	coverage = {}
	specificity = {}
	total = 0
	for name in root.keys():
		count = 0
		for q in root[name]['query']:
			result = probe(siteURL, q, accountKey)
			count = count+int(result['WebTotal'])
			for data in result['Web']:
				# if not data['Url'].endswith('.pdf'):
				rootSample.add(data['Url'])
		coverage[name] = count
		total = total + count
	classified = False
	for name in root.keys():
		specificity[name] = coverage[name]/float(total)
		print "Specificity for category:"+name+" is "+str(specificity[name])
		print "Coverage for category:"+name+" is "+str(coverage[name])
		if coverage[name]>=tec and specificity[name]>=tes:
			childcategory, childSample = classifyChild(accountKey,siteURL, tes, tec, name, specificity[name])
			category = category+childcategory
			sample[name] = childSample
			rootSample.union(childSample)
	sample['Root'] = rootSample
	if not category:
		category.append('Root')
	print "Classification:"
	for s in category:
		print s
	return sample


def classifyChild(accountKey,siteURL, tes, tec, parentName, parentSpec):
	node = root[parentName]['children']
	category = []
	nodeSample = set()
	coverage = {}
	specificity = {}
	total = 0
	for name in node.keys():
		count = 0
		for q in node[name]:
			result = probe(siteURL, q, accountKey)
			count = count+int(result['WebTotal'])
			for data in result['Web']:
				# if not data['Url'].endswith('.pdf'):
				nodeSample.add(data['Url'])
		coverage[name] = count
		total = total + count
	for name in node.keys():
		specificity[name] = (coverage[name]/float(total))*parentSpec
		print "Specificity for category:"+name+" is "+str(specificity[name])
		print "Coverage for category:"+name+" is "+str(coverage[name])
		if coverage[name]>=tec and specificity[name]>=tes:
			category.append("Root/"+parentName+"/"+name)
	if not category:
		category.append("Root/"+parentName)
	return category,nodeSample


def add_to_doc_freq(page_content, doc_freq):
	# ref_idx = page_content.find('\nReferences\n')
	# if ref_idx >= 0:
	# 	page_content = page_content[0:ref_idx]
	# page_content = page_content.lower()
	# page_content = re.sub(r'\[(.*?)\]', r' ', page_content).strip()
	# result = re.findall(r'[a-z]+',page_content)
	# result = set(result)

	result = page_content.split()
	for r in result:
		if r in doc_freq:
			doc_freq[r] = doc_freq[r] + 1
		else:
			doc_freq[r] = 1


def extract(sample,host):
	print "Extracting topic content summaries..."

	# np.save('sample.npy', sample)

	page = ''

	for nodeName in sample.keys():
		print "Creating Content Summary for:" + nodeName
		doc_freq = {}
		i = 1
		for url in sample[nodeName]:
			print "Getting page: " + url
			print str(i) + '/' + str(len(sample[nodeName]))
			print ''
			i = i + 1
			# cmd = 'lynx --dump ' + url
			# p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
			# stdout, stderr = p.communicate()

			cmd = 'java getWordsLynx ' + url
			p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
			stdout, stderr = p.communicate()

			if stderr:
				stdout = ' '

			add_to_doc_freq(stdout,doc_freq)


		od = collections.OrderedDict(sorted(doc_freq.items()))

		target = open(nodeName + '-' + host + '.txt', 'w')
		target.truncate()

		for j in od:
			target.write(j + '#' + str(od[j]) + '\n')

		target.close()


computers =['cpu','java','module','multimedia','perl','vb','agp%20card','application%20windows','applet%20code','array%20code','audio%20file','avi%20file','bios','buffer%20code','bytes%20code','shareware','card%20drivers','card%20graphics','card%20pc','pc%20windows']
health = ['acupuncture','aerobic','aerobics','aids','cancer','cardiology','cholesterol','diabetes','diet','fitness','hiv','insulin','nurse','squats','treadmill','walkers','calories%20fat','carb%20carbs','doctor%20health','doctor%20medical','eating%20fat','fat%20muscle','health%20medicine','health%20nutritional','hospital%20medical','hospital%20patients','medical%20patient','medical%20treatment','patients%20treatment']
sports = ['laker','ncaa','pacers','soccer','teams','wnba','nba','avg%20league','avg%20nba','ball%20league','ball%20referee','ball%20team','blazers%20game','championship%20team','club%20league','fans%20football','game%20league']
hardware = ['bios','motherboard','board%20fsb','board%20overclocking','fsb%20overclocking','bios%20controller%20ide','cables%20drive%20floppy']
programming = ['actionlistener','algorithms','alias','alloc','ansi','api','applet','argument','array','binary','boolean','borland','char','class','code','compile','compiler','component','container','controls','cpan','java','perl']
diseases = ['aids','cancer','dental','diabetes','hiv','cardiology','aspirin%20cardiologist','aspirin%20cholesterol','blood%20heart','blood%20insulin','cholesterol%20doctor','cholesterol%20lipitor','heart%20surgery','radiation%20treatment']
fitness = ['aerobic','fat','fitness','walking','workout','acid%20diets','bodybuilding%20protein','calories%20protein','calories%20weight','challenge%20walk','dairy%20milk','eating%20protein','eating%20weight','exercise%20protein','exercise%20weight']
soccer = ['uefa','leeds','bayern','bundesliga','premiership','lazio','mls','hooliganism','juventus','liverpool','fifa']
basketball = ['nba','pacers','kobe','laker','shaq','blazers','knicks','sabonis','shaquille','laettner','wnba','rebounds','dunks']

root = {}
root['Computers'] = {'query':computers,'children':{'Hardware':hardware, 'Programming':programming}}
root['Health'] = {'query':health, 'children':{'Diseases':diseases, 'Fitness':fitness}}
root['Sports'] = {'query':sports, 'children':{'Soccer':soccer, 'Basketball':basketball}}

reload(sys)
# sys.setdefaultencoding("utf-8")

# accountKey = 'kFRQoklsXI8ce9XIoxcYBscDK9eUfx6usx5NXKGCjgU'
accountKey = sys.argv[1]
tes = float(sys.argv[2])
tec = int(sys.argv[3])
host = sys.argv[4]


cmd = 'javac getWordsLynx.java'
p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
p.communicate()

# if(os.path.exists('sample.npy')):
# 	sample = np.load('sample.npy').item()
# 	extract(sample,host)
# else:
sample = classify(host, tes, tec, accountKey)
extract(sample,host)





