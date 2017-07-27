#!/usr/bin/python
import requests
import sys
import csv
import configparser
import logging
import json
import re
import xml.etree.ElementTree as ET

# Returns the API key
def get_key():
	return config.get('Params', 'apikey')

# Returns the Alma API base URL
def get_base_url():
	return config.get('Params', 'baseurl')

# Returns the bib record MARC tag that we are getting data FROM
def get_marc_field():
	return config.get('Params', 'marc_tag')

# Gets the holding record MARC tag that we are moving data TO
def get_target_marc_field():
	return config.get('Params', 'target_marc_tag')

# Return holding API url
def get_holding_url(mms_id,holding_id):
	return get_base_url() + "bibs/" + mms_id + '/holdings/' + holding_id + '?apikey=' + get_key()

# checks to see if there are 0 items attached to a holding, returns true if so.
def get_item_count(mms_id,holding_id):
	url =  get_base_url() + "bibs/" + mms_id + '/holdings/' + holding_id + '/items?apikey=' + get_key()
	response = requests.get(url)
	if response.status_code == 200:
		items = ET.fromstring(response.content)
		if int(items.get('total_record_count')) == 0:
			return True
	return False

# Creates the new marc datafield element and appends all subfields from the 891 field to the 853 holding field
def add_marc_field(record,new_subfields):
	marc = ET.Element('datafield')
	marc.set("tag",get_target_marc_field())
	for key,value in new_subfields:
		sub = ET.SubElement(marc,'subfield')
		sub.set('code', 'a')
		sub.text = value
	record.append(marc)
	return record

# Places PUT request with updated holding
def make_put_request(url,holding):
	headers = {"Content-Type": "application/xml"}
	r = requests.put(url,data=ET.tostring(holding),headers=headers)
	print (r.content)
	if r.status_code == 200:
		logging.info('Successful update for ' + url)

# Gets holding data form the Alma API, calls , and posts updated holding with added 853 field
def create_libhas_field(url,new_subfields):
	match = False
	response = requests.get(url)
	if response.status_code != 200:
		return None
	holding = ET.fromstring(response.content)
	new_subfields = sorted(new_subfields.items())
	record = holding.findall('record')[0]
	print (record)
	record = add_marc_field(record,new_subfields)
	make_put_request(url,holding)

# Gets all subfields from the XXX MARC field
def get_marc_elements(datafield):
	new_subfields = {}
	for subfields in datafield.findall('subfield'):
		# Let's throw out the $9LOCAL - there's no need to carry it over to the holding
		if subfields.attrib['code'] != '9':
			new_subfields[subfields.attrib['code']] = subfields.text
	return new_subfields

# Can't just get the last holding - go through primo heirarchy to get the last one that displays
def find_last_displayed(holdings,mms_id):
	holding_id = None
	no_items = False
	print (holdings.findall('./holding'))
	# if a holding is an LRS holding, select that one as it should display last
	# Otherwise, select last holding
	for h in holdings.findall('./holding'):
		if not no_items:
			print (get_item_count(mms_id,h.find('./holding_id').text))
			if get_item_count(mms_id,h.find('./holding_id').text):
				holding_id = h.find('./holding_id')
				no_items = True
			elif h.find('./location').text.find('lrs') > -1:
				print ('found in location')
				holding_id = h.find('./holding_id')
	if holding_id is None:
		holding_id = holdings.findall('./holding')[-1].find('./holding_id')
	return holding_id.text

# Calls the holdings API to get the correct sort order
def get_last_holding(mms_id):
	url = get_base_url() + "bibs/" + mms_id + '/holdings?apikey=' + get_key()
	print (url)
	response = requests.get(url)
	if response.status_code == 200:
		holdings = ET.fromstring(response.content)
		print (holdings)
		record_count = int(holdings.get('total_record_count'))
		holding_id = None
		if record_count > 0:
			holding_id = find_last_displayed(holdings,mms_id)
			return holding_id.text

# Read in bib record XML export from Alma
def read_bibs(bib_records):
	tree = ET.parse(bib_records)
	for records in tree.findall('record'):
		# Get bib record MMS ID
		mms_id = records.find('./controlfield[@tag="001"]').text
		logging.info('Bib MMS ID: ' + mms_id)
		# get each lib has field
		for libhas in records.findall('./datafield[@tag="' + get_marc_field() + '"]'):
			new_subfields = get_marc_elements(libhas)
			holding_id = get_last_holding(mms_id)
			print (holding_id)
			if holding_id is not None:
				url = get_holding_url(mms_id,holding_id)
				print (url)
				# add the 853 field to the holding, with the 891 subfields
				create_libhas_field(url,new_subfields)
			else:
				logging.info('No holding found in record: ' +  mms_id)
		else:
			logging.info('No 891 field found in record: ' + mms_id)


logging.basicConfig(filename='status.log',level=logging.DEBUG)
config = configparser.ConfigParser()
config.read(sys.argv[1])

bib_recs = sys.argv[2]
read_bibs(bib_recs)
