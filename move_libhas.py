#!/usr/bin/python
import requests
import sys
import csv
import configparser
import logging
import json
import xml.etree.ElementTree as ET

# Returns the API key
def get_key():
	return config.get('Params', 'apikey')

# Returns the Alma API base URL
def get_base_url():
	return config.get('Params', 'baseurl')

def get_marc_field():
	return config.get('Params', 'marc_tag')

def get_target_marc_field():
	return config.get('Params', 'target_marc_tag')

# Return holding API url
def get_holding_url(mms_id,holding_id):
	return get_base_url() + "bibs/" + mms_id + '/holdings/' + holding_id + '?apikey=' + get_key()

"""
	Creates the new marc datafield element and appends all subfields from the 891 field to the 853 holding field
"""
def add_marc_field(record,new_subfields):
	marc = ET.Element('datafield')
	marc.set("tag",get_target_marc_field())
	for key,value in new_subfields:
		sub = ET.SubElement(marc,'subfield')
		sub.set('code', 'a')
		sub.text = value
	record.append(marc)
	return record

"""
	Gets holding data form the Alma API, calls , and posts updated holding with added 853 field
"""
def create_libhas_field(url,new_subfields):
	match = False
	response = requests.get(url)
	if response.status_code != 200:
		return None
	holding = ET.fromstring(response.content)
	new_subfields = sorted(new_subfields.items())
	record = holding.findall('record')[0]
	print (record)
	# change this to compare the data t othe new_subfields data

	record = add_marc_field(record,new_subfields)
	headers = {"Content-Type": "application/xml"}
	r = requests.put(url,data=ET.tostring(holding),headers=headers)
	print (r.content)
	if r.status_code == 200:
		logging.info('Successful update for ' + url)

# Gets all subfields from the XXX MARC field
def get_marc_elements(datafield):
	new_subfields = {}
	for subfields in datafield.findall('subfield'):
		# Let's throw out the $9LOCAL - there's no need to carry it over to the holding
		if subfields.attrib['code'] != '9':
			new_subfields[subfields.attrib['code']] = subfields.text
	return new_subfields

# Calls the holdings API to get the correct sort order
def get_last_holding(mms_id):
	url = get_base_url() + "bibs/" + mms_id + '/holdings?apikey=' + get_key()
	response = requests.get(url)
	if response.status_code == 200:
		holdings = ET.fromstring(response.content)
		record_count = int(holdings.get('total_record_count'))
		if record_count > 0:
			holding_id =  holdings.findall('./holding/holding_id')[-1]
			print (holding_id.text)
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
			print (new_subfields)
		#	for holding in records.findall('./datafield[@tag="852"]'):
		# Instead of getting the holding ID from the export, call the /holdings API
			holding_id = get_last_holding(mms_id)
			print (holding_id)
			if holding_id is not None:
				url = get_holding_url(mms_id,holding_id)
				# add the 853 field to the holing, with the 891 subfields
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
