import urllib2
import base64
import json
import re
import math
import numpy as np
import lxml
from lxml import html
import requests
import sys
from bs4 import BeautifulSoup


#on input a query in url form and an account key
#output an json response from Bing (a list of top 10 relevant documents)
def get_query_result(query,accountKey):
	bingUrl = 'https://api.datamarket.azure.com/Bing/Search/Web?Query=%27' + query + '%27&$top=10&$format=Json'
	accountKeyEnc = base64.b64encode(accountKey + ':' + accountKey)
	headers = {'Authorization': 'Basic ' + accountKeyEnc}
	req = urllib2.Request(bingUrl, headers = headers)
	response = urllib2.urlopen(req)
	return json.loads(response.read())['d']['results']

# helper function for get_useful_page_content(url)
def get_fields_content(fields):
	p_page = ''
	for p in fields:
		p_page = p_page + str(p).strip() + '\n'

	p_page = re.sub(r'<(.*?)>', r' ', p_page).strip()
	p_page = re.sub(r'\[[0-9]+\]', r' ', p_page).strip()
	p_page = re.sub(r'(\t|( ))+', r' ', p_page).strip()

	temp_page = p_page
	p_page = ''

	for cp in re.findall(r'(.+?)\n',temp_page):
		cnt = 0
		tokens = re.findall(r'\w+',cp)
		for t in tokens:
			if (t not in stopWords) and (not t.isdigit()):
				cnt = cnt + 1
		if cnt >= 3:
			p_page = p_page + cp.strip() + '\n'

	return p_page

# scrape web pages, eliminating the tags, links, scripts, ...
def get_useful_page_content(url):
	print 'processing page content ...'
	page = requests.get(url).content.lower()

	soup = BeautifulSoup(page,"lxml")

	# get all paragraph fields
	p_page = get_fields_content(soup.find_all('p'))

	# If we already have enough content, exit. Otherwise, extract more data.
	if len(p_page) > 1000:
		return p_page

	a_page = get_fields_content(soup.find_all('a'))
	return p_page + '\n' + a_page;

# tokenize a string and eliminate stopwords and numbers
def tokenize(s):
	tokens = re.findall(r'\w+',s.lower())
	result = []
	for t in tokens:
		if (t not in stopWords) and (not t.isdigit()):
			result.append(t)
	return result

# return a set of all the words in string s
def get_vocabulary_vector(s):
	print 'indexing ...'
	return list(set(tokenize(s)))

# every token in s must be in the vocabulary_vector
# return the frequency vector of the words in s taken into account the length of the document
def get_freq_vector(s, vocabulary_vector):
	tokens = tokenize(s)
	token_cnt = {}
	num_tokens = 0
	for token in tokens:
		num_tokens = num_tokens + 1
		if token in token_cnt:
			token_cnt[token] = token_cnt[token] + 1
		else:
			token_cnt[token] = 1
	freq_vector = [0] * len(vocabulary_vector)
	for i in range(len(vocabulary_vector)):
		if vocabulary_vector[i] in token_cnt:
			freq_vector[i] = 1.0*token_cnt[vocabulary_vector[i]]/num_tokens
	return freq_vector

# add up the tf vectors for relevant docs and minus the tf vectors from the irrelevant docs
# normalized by number of relevant/irrelevant docs
def get_diff_vector(tf_matrix, label_vector):
	N = len(label_vector)
	n = len(tf_matrix[0])

	pos_cnt = 0
	neg_cnt = 0
	pos_vector = [0] * n
	neg_vector = [0] * n

	for i in range(N):
		if label_vector[i] == True:
			pos_cnt = pos_cnt + 1
			pos_vector = np.add(pos_vector,tf_matrix[i])
		else:
			neg_cnt = neg_cnt + 1
			neg_vector = np.add(neg_vector,tf_matrix[i])

	pos_vector = [1.0*x/pos_cnt for x in pos_vector]
	neg_vector = [1.0*x/neg_cnt for x in neg_vector]

	return np.subtract(pos_vector,neg_vector)

# doc_list is a list of strings (documents)
# return the weight matrix
def get_ranked_tokens(doc_list, label_vector):
	#number of documents, should be 10
	N = len(doc_list)
	#extract all words into a big vector
	tmp_doc = ' '.join(doc_list)
	vocabulary_vector = get_vocabulary_vector(tmp_doc)
	#total number of words
	n = len(vocabulary_vector)
	
	#term frequency
	tf = []

	for i in range(N):
		tf.append(get_freq_vector(doc_list[i], vocabulary_vector))

	diff_vector = get_diff_vector(tf, label_vector)

# we reduce the weight of highly frequent verbs
	for i in range(n):
		if vocabulary_vector[i] in verbFreq:
			diff_vector[i] = diff_vector[i]*1.0/verbFreq[vocabulary_vector[i]]

	result = [x for (y,x) in sorted(zip(diff_vector,vocabulary_vector),reverse=True)]
	return result

# return the top 2 most relevant words that is not already in the query
def get_augmented_tokens(query, doc_list, label_vector):
	target_length = len(query) + 2
	ranked_tokens = get_ranked_tokens(doc_list, label_vector)

	result = list(query)
	for q in ranked_tokens:
		if q not in query:
			result.append(q)
			if len(result) == target_length:
				break

	# used up all tokens but still cannot find 2 more
	if len(result) != target_length:
		return None

	ranks = [0] * target_length

	for i in range(target_length):
		if result[i] not in ranked_tokens:
			ranks[i] = target_length
		else:
			ranks[i] = ranked_tokens.index(result[i])

	result = [x for (y,x) in sorted(zip(ranks,result),reverse=False)]
	return result

# load stop words into a set
def loadStopWords():
	words = set()
	with open('stopwords.txt') as f:
		for line in f:
			words.add(line.strip().lower())
	return words

# load verb frequency into a dictionary
def loadVerbFrequencies():
	verbFreq = {}
	with open('verb.txt') as f:
		for line in f:
			tokens = line.split(' ')
			if tokens[0].isalnum() and int(tokens[2]) > 1:
				verbFreq[tokens[0]] = int(tokens[2])
	return verbFreq

reload(sys)
sys.setdefaultencoding("utf-8")

stopWords = loadStopWords()
verbFreq = loadVerbFrequencies()

accountKey = sys.argv[1]
target_precision = float(sys.argv[2])
query = sys.argv[3].split(' ')
current_precision = 0.0

while True:
	if target_precision <= 0.0:
		print 'Desired precision reached, done'
		break
	print 'Parameters:'
	print 'Client key = ' + accountKey
	print 'Query = ' + ' '.join(query)
	print 'Precision = ' + str(target_precision)
	print 'URL: ' + 'https://api.datamarket.azure.com/Bing/Search/Web?Query=%27' + '%20'.join(query) + '%27&$top=10&$format=Json'
	results = get_query_result('%20'.join(query),accountKey)
	print 'Total no of results: ' + str(len(results))
	if len(results) != 10:
		print 'Less than 10 results. Exit'
		break
	print 'Bing Search Results:\n========================'
	relevant_count = 0
	for i in range(len(results)):
		print 'Result ' + str(i+1) + '\n[\nURL: ' + results[i]['Url'] + '\nTitle: ' + results[i]['Title'] + '\nSummary: ' + results[i]['Description'] + '\n]'
		print ''
		get_input_success = False
		while get_input_success == False:
			user_input = raw_input('Relevant (Y/N)?')
			if user_input.lower() == 'y':
				results[i]['relevant'] = True
				get_input_success = True
				relevant_count = relevant_count + 1
			elif user_input.lower() == 'n':
				results[i]['relevant'] = False
				get_input_success = True
		current_precision = relevant_count/10.0
	print '========================\nFEEDBACK SUMMARY'
	print 'Query: ' + ' '.join(query)
	print 'Precision: ' + str(current_precision)
	if current_precision == 0.0:
		print 'Current precision is zero. Exit.'
		break
	if current_precision >= target_precision:
		print 'Desired precision reached, done'
		break
	else:
		print 'Still below the desired precision of ' + str(target_precision)
		augmented_tokens = get_augmented_tokens(query,
				[results[i]['Description'].lower()+results[i]['Title'].lower()+get_useful_page_content(results[i]['Url']) for i in range(10)],
				[results[i]['relevant'] for i in range(10)])
		if augmented_tokens is not None:
			added_tokens = set(augmented_tokens) - set(query)
			query = augmented_tokens
			print 'Augmenting by: ' + ' '.join(list(added_tokens))
		else:
			print 'No tokens can be added. Exit.'
			break
