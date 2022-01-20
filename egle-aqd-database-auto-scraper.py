#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from datetime import datetime
from pytz import timezone


# In[ ]:


# What day is it?
tz = timezone('EST')
today = datetime.now(tz) 

# Making datetime the same format as the EGLE database
today = today.strftime("%-m/%-d/%Y")


# In[ ]:


# Reading in the EGLE master list of sources to search database for known sources
source_list_df = pd.read_csv("EGLE-AQD-source-list.csv")

# Getting a list of known sources
source_id_list = source_list_df.id.to_list()


# In[ ]:


# Reading the EGLE database home page and getting the text
raw_html = requests.get("https://www.deq.state.mi.us/aps/downloads/SRN/").content
doc = BeautifulSoup(raw_html, "html.parser")
text = doc.get_text()


# In[ ]:


# Getting the source name and date the directory was updated
# Although the text shows the source ID next to the date, 
# the date actually appears before the source ID on the website
# So my regex is looking for the source ID ~after~ the date.
source_dates = re.findall(r"(\d\d?/\d\d?/\d{4})\s+\d+:\d{2}\s[A-Z]{2}\s*<dir>\s([A-Z]\d{4})",text)
unknown_source_dates = re.findall(r"(\d\d?/\d\d?/\d{4})\s+\d+:\d{2}\s[A-Z]{2}\s*<dir>\s([U]\d{9})",text)


# In[ ]:


# Making a list of directory URLs that have had updates today
updates = []
sources_updated = []
for source in source_dates:
    source_id = source[1]
    date = source[0]
    if (date == today) & (source_id in source_id_list):
        link = "https://www.deq.state.mi.us/aps/downloads/SRN/"+source_id
        updates.append(link)
        sources_updated.append(source_id)
for source in unknown_source_dates:
    if (date == today) & (source_id in source_id_list):
        link = "https://www.deq.state.mi.us/aps/downloads/SRN/"+source_id
        updates.append(link)
        sources_updated.append(source_id)


# In[ ]:


# Reading in the most recent csv of extra documents
df = pd.read_csv("output/EGLE-AQD-extra-documents.csv")

# Getting a list of extra document urls I already have
extra_doc_url_list = df.doc_url.to_list()


# In[ ]:


# Reading in the most recent csv of documents
df = pd.read_csv("output/EGLE-AQD-documents.csv")

# Getting a list of document urls I already have
doc_url_list = df.doc_url.to_list()


# In[ ]:


# Scrape the directories that have had updates looking for urls that are not already in my csv
all_sources_data = []
all_sources_extras = []
mistakes = []

# Look in the directories that have updates
for directory in tqdm(updates):
    raw_html = requests.get(directory).content
    doc = BeautifulSoup(raw_html, "html.parser")
    links = doc.find_all('a')
    source_data = []
    source_extras = []
    
    # For each directory, look at the urls
    for link in links:
        data = {}
        other = {}
        doc_url = 'https://www.deq.state.mi.us'+link['href']
        
        # I only want new URLs. Also, don't capture the ['To Parent Directory'] link
        if (doc_url not in doc_url_list) & (doc_url != 'https://www.deq.state.mi.us/aps/downloads/SRN/'):
            
            # Save data from documents that fit the regex
            try:
                # Source_ID
                data['source_id'] = re.findall(r"^\w\w?\d+",link.text)[0]
                # Document code
                data['doc_type'] = re.findall(r"_?([A-Z]+\d?\d?)_",link.text, re.IGNORECASE)[0]
                # Date
                data['date'] = re.findall(r"_(\d{8})", link.text)[0]
                # URL
                data['doc_url'] = doc_url
                source_data.append(data)
            
            # Save links that don't fit the regex or just don't work for some reason (misakes)
            except:
                try:
                    # Source_ID
                    other['source_id'] = re.findall(r"\w\w?\d+", directory)[0]
                    
                    # extra doc names that don't fit the regex
                    other['doc_name'] = link.text
                    
                    # extra doc URLs
                    other['doc_url'] = doc_url
                    if (other['doc_name'] != '[To Parent Directory]') & (doc_url not in extra_doc_url_list):
                        source_extras.append(other)
                        
                    
                except:
                    # If there are still links that don't work, save them in a list
                    mistake = link
                    mistakes.append(mistake)
                    
    if len(source_data) != 0:
        all_sources_data.append(source_data)
    if len(source_extras) != 0:
        all_sources_extras.append(source_extras)


# In[ ]:


# Turning my list of lists of dicts of Source Data into a dataframe
if len(all_sources_data) != 0:
    list_of_dfs = [pd.DataFrame(one_list) for one_list in all_sources_data]
    new_data_df = pd.concat(list_of_dfs, ignore_index=True)
    new_data_urls = new_data_df.doc_url.to_list()
    
    # Adding my new documents to my old documents
    updated_df = pd.concat([df,new_data_df], axis=0,ignore_index=True)
    
    # Overwriting the old csv with updates
    updated_df.to_csv("output/EGLE-AQD-documents.csv", index=False)
    
else:
    new_data_urls = []


# In[ ]:


# Merging documents with EGLE Source Directory
# To get identifying information

if len(all_sources_data) != 0:
    df = updated_df.merge(source_list_df, left_on="source_id", right_on="id", how="left")
    df = df.drop(['id'], axis=1)
    df['date'] = pd.to_datetime(df['date'], format="%Y%m%d", errors='coerce')
    df['zip_code'] = df['zip_code'].astype(str).str[:5]
    df = df[['name', 'doc_type','date','zip_code','county','full_address','source_id','geometry', 'doc_url']]
    df.to_csv("output/EGLE-AQD-documents-source-info.csv", index=False)


# In[ ]:


# Reading in my csv of extra documents
df = pd.read_csv("output/EGLE-AQD-extra-documents.csv")

# Turning my list of lists of dicts of Extra Documents into a dataframe
if len(all_sources_extras) != 0:
    list_of_dfs = [pd.DataFrame(one_list) for one_list in all_sources_extras]
    new_extras_df = pd.concat(list_of_dfs, ignore_index=True)
    new_extras_urls = new_extras_df.doc_url.to_list()
    
    # Adding my new documents to my old documents
    updated_df = pd.concat([df,new_extras_df], axis=0, ignore_index=True)
    
    # Overwriting the old csv with updates
    updated_df.to_csv("output/EGLE-AQD-extra-documents.csv", index=False)
    
else:
    new_extras_urls = []


# In[ ]:


# Reading in my most recent scrape report
df = pd.read_csv("output/EGLE-AQD-scraper-report.csv")

# Creating today's scrape report

scrape_report = []
data = {}

data['date'] = today

data['updates_found'] = len(sources_updated)

data['source_data'] = len(new_data_urls)
    
data['source_extras'] = len(new_extras_urls)

data['mistakes'] = len(mistakes)

if data['updates_found'] != 0:
    data['sources_updated'] = sources_updated
else:
    data['sources_updated'] = None

if data['source_data'] != 0:
    data['source_data_urls'] = new_data_urls
else: 
    data['source_data_urls'] = None
    
if data['source_extras'] != 0:
    data['source_extras_urls'] = new_extras_urls
else:
    data['source_extras_urls'] = None
    
if data['mistakes'] != 0:
    data['mistakes_urls'] = mistakes
else:
    data['mistakes_urls'] = None
    
scrape_report.append(data)


# In[ ]:


report_df = pd.DataFrame(scrape_report)

# Adding the new report to the old reports
report_df = pd.concat([df,report_df], axis=0, ignore_index=True)

# Overwriting the report csv with update
report_df.to_csv("output/EGLE-AQD-scraper-report.csv", index=False)

