#!/usr/bin/env python
# coding: utf-8

# ### Imports

import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from datetime import datetime
from pytz import timezone


# ### Getting the date

tz = timezone('EST')
today = datetime.now(tz) 

# Making datetime the same format as the EGLE database
today = today.strftime("%-m/%-d/%Y")


# ### Getting a list of current sources
# List provided by EGLE in May 2022 via FOIA.
sourceList = pd.read_csv('CMS-Subject-Sources-Simple.csv')

# ### Looking for sources in this list that were updated today

# Pulling up the EGLE database
raw_html = requests.get("https://www.egle.state.mi.us/aps/downloads/SRN/", verify=False).content
doc = BeautifulSoup(raw_html, "html.parser")
text = doc.get_text()

# Getting the source name and date the directory was updated
# Although the text shows the source ID next to the date, 
# the date actually appears before the source ID on the website
# So my regex is looking for the source ID ~after~ the date.
sourceDates = re.findall(r"(\d\d?/\d\d?/\d{4})\s+\d+:\d{2}\s[A-Z]{2}\s*<dir>\s([A-Z]\d{4})",text)
sourceDatesUnknown = re.findall(r"(\d\d?/\d\d?/\d{4})\s+\d+:\d{2}\s[A-Z]{2}\s*<dir>\s([U]\d{9})",text)


# ### Making a list of directory URLs that have had updates today

updates = []
sourcesUpdated = []

sourceListSRNs = sourceList.srn.to_list()

for source in sourceDates:
    sourceID = source[1]
    date = source[0]
    if (date == today) & (sourceID in sourceListSRNs):
        link = "https://www.egle.state.mi.us/aps/downloads/SRN/"+ sourceID
        updates.append(link)
        sourcesUpdated.append(sourceID)
        
for source in sourceDatesUnknown:
    if (date == today) & (sourceID in sourceList.srn):
        link = "https://www.egle.state.mi.us/aps/downloads/SRN/"+ sourceID
        updates.append(link)
        sourcesUpdated.append(sourceID)


# ### Getting the current document datasets

# documents I already have
oldDocs = pd.read_csv("output/EGLE-AQD-document-dataset-full.csv")

# list of URLs
oldDocs = oldDocs.doc_url.to_list()

# EXTRA documents that didn't fit the regex
oldExtras = pd.read_csv("output/EGLE-AQD-extra-documents.csv")

# list of URLs
oldExtras = oldExtras.doc_url.to_list()

# ### Looking for new documents in the updated directories

allSourcesData = []
allSourcesExtras = []
mistakes = []

# Look in the directories that have updates
for directory in tqdm(updates):
    raw_html = requests.get(directory, verify=False).content
    doc = BeautifulSoup(raw_html, "html.parser")
    links = doc.find_all('a')
    sourceData = []
    sourceExtras = []
    # For each directory, look at the urls
    for link in links:
        data = {}
        other = {}
        doc_url = 'https://www.egle.state.mi.us'+link['href']
        
        # I only want new URLs. Also, don't capture the ['To Parent Directory'] link
        if (doc_url not in oldDocs) & (doc_url != 'https://www.egle.state.mi.us/aps/downloads/SRN/'):
            
            # Save data from documents that fit the regex
            try:
                # Source_ID
                data['source_id'] = re.findall(r"SRN/(.*)",directory)[0]
                # Document code
                data['doc_type'] = re.findall(r"_?([A-Z]+\d?\d?)_",link.text, re.IGNORECASE)[0]
                # Date
                data['date'] = re.findall(r"_(\d{8})", link.text)[0]
                # URL
                data['doc_url'] = doc_url
                sourceData.append(data)

            # Save links that don't fit the regex or just don't work for some reason (misakes)
            except:
                try:
                    # Source_ID
                    other['source_id'] = re.findall(r"SRN/(.*)", directory)[0]

                    # extra doc names that don't fit the regex
                    other['doc_name'] = link.text
                    print(link.text)

                    # extra doc URLs
                    other['doc_url'] = doc_url
                    if (other['doc_name'] != '[To Parent Directory]') & (doc_url not in oldExtras):
                        sourceExtras.append(other)


                except:
                    # If there are still links that don't work, save them in a list
                    mistake = link
                    mistakes.append(mistake)

    if len(sourceData) != 0:
        allSourcesData.append(sourceData)
    if len(sourceExtras) != 0:
        allSourcesExtras.append(sourceExtras)


# ### Formatting new document data and adding it to existing dataset

if len(allSourcesData) != 0:
    
    # Converting new data into a dataframe
    dfList = [pd.DataFrame(oneList) for oneList in allSourcesData]
    newDocs = pd.concat(dfList, ignore_index=True)
    newDocsURLs = newDocs.doc_url.to_list()
    
    # Converting to datetime and adding year column
    newDocs.date = pd.to_datetime(newDocs.date,format='%Y%m%d',errors='coerce')
    newDocs['year'] = newDocs.date.dt.year
    
    # Removing leading zeroes
    newDocs.loc[newDocs.doc_type.str.contains('0\d'),'doc_type'] = newDocs.loc[newDocs.doc_type.str.contains('0\d'),'doc_type'].str.replace("0",'')

    # Making codes all uppercase
    newDocs.doc_type = newDocs.doc_type.str.upper()

    # Fixing a common transposition of "RVN"
    newDocs.doc_type = newDocs.doc_type.str.replace('VNR','RVN')
    
    # Reading in a key of document code
    ## Read about the creation of the key at srjouppi.github.io
    key = pd.read_excel('EGLE-AQD-document-code-key.xlsx', sheet_name='DocKey')

    # Merging with document code key 
    newDocs = newDocs.merge(key)

    # Merging with source list for identifying information
    newDocs = newDocs.merge(sourceList,how='left', left_on='source_id',right_on='srn')

    # Rearranging Columns
    newDocs = newDocs[['srn','facility_name','doc_type','type_name','date','year','doc_url','type_simple','type_name_simple','epa_class','address_line1','city_name','zip_cd','add_county_name','district_name','address_full','staff']]
    
    # Reading in existing document dataset
    oldDocs = pd.read_csv("output/EGLE-AQD-document-dataset-full.csv", dtype={'zip_cd':str})
    oldDocs.date = pd.to_datetime(oldDocs.date)
    
    # Adding new documents to dataset
    allDocs = pd.concat([oldDocs, newDocs], axis=0,ignore_index=True)
    
    # Sorting by date
    allDocs = allDocs.sort_values('date',ascending=False, ignore_index=True)
    
    # Overwriting document dataset file
    allDocs.to_csv('output/EGLE-AQD-document-dataset-full.csv',index=False)
    
    # Saving a subset of the most current documents (last 90 days) that is easier to use 
    today = pd.to_datetime(today)
    
    # Getting a duration from the date of the file to today's date
    def duration(date):
        return today - date

    allDocs['duration'] = allDocs.date.apply(duration)
    allDocs.duration = allDocs.duration.dt.days
    
    # If the duration is less than 91, save it to the 90-day file.
    allDocs.query('duration < 91').drop(['duration'],axis=1).sort_values('date',ascending=False).to_csv('output/EGLE-AQD-document-dataset-90days.csv',index=False)
    
else:
    newDocsURLs = []


# ### Adding new extra documents to existing dataset

# Reading in my csv of extra documents
oldExtras = pd.read_csv("output/EGLE-AQD-extra-documents.csv")

# Turning my list of lists of dicts of Extra Documents into a dataframe
if len(allSourcesExtras) != 0:
    dfList = [pd.DataFrame(oneList) for oneList in allSourcesExtras]
    newExtras = pd.concat(dfList, ignore_index=True)
    newExtrasURLs = newExtras.doc_url.to_list()
    
    # Adding my new documents to my old documents
    allExtras = pd.concat([oldExtras ,newExtras], axis=0, ignore_index=True)
    
    # Overwriting the old csv with updates
    allExtras.to_csv("output/EGLE-AQD-extra-documents.csv", index=False)
    
else:
    newExtrasURLs = []


# ### Creating today's scrape report

# Reading in my most recent scrape report
oldReport = pd.read_csv("output/EGLE-AQD-scraper-report.csv")


scrapeReport = []
data = {}

data['date'] = today

data['sources_updated'] = len(sourcesUpdated)

data['docs_found'] = len(newDocsURLs)

# All "Type Simple" Doc Types:
docTypes = ['SAR',
 'FCE',
 'TEST',
 'VN',
 'RVN',
 'ACO',
 'ENFN',
 'STIP',
 'CJ',
 'ASBVN',
 'AFO',
 'RASBVN',
 'SEM',
 'CD']
 
# If documents found today, getting counts for the different types:
if data['docs_found'] != 0:
    newDocsTypes = newDocs.type_simple.value_counts().to_dict()
else:
    newDocsTypes = []

# For each document type, look to see if it was found today,
# If so, add the count. If not, return "None"
for docType in docTypes:
    if docType in newDocsTypes:
        data[docType] = newDocsTypes[docType]
    else:
        data[docType] = None

data['extras_found'] = len(newExtrasURLs)

data['mistakes_found'] = len(mistakes)
    
if data['mistakes_found'] != 0:
    
    data['mistakes'] = mistakes
else:
    data['mistakes'] = None

scrapeReport.append(data)

newReport = pd.DataFrame(scrapeReport)

# Adding the new report to the old reports
newReport = pd.concat([oldReport,newReport], axis=0, ignore_index=True).sort_values('date',ascending=False)

# Overwriting the report csv with update
newReport.to_csv("output/EGLE-AQD-scraper-report.csv", index=False)

