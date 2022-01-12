#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from datetime import date


# In[2]:


# What day is it?
today = date.today()

# Making datetime the same format as the MDEQ website
today = today.strftime("%-m/%-d/%Y")


# In[3]:


# Reading in the MDEQ master list of sources to search database for known sources
df = pd.read_csv("MDEQ-SRN-directory.csv")


# In[4]:


# Getting a list of known sources
source_id_list = df.id.to_list()


# In[5]:


# Reading the MDEQ SRN database home page and getting the text
raw_html = requests.get("https://www.deq.state.mi.us/aps/downloads/SRN/").content
doc = BeautifulSoup(raw_html, "html.parser")
text = doc.get_text()


# In[6]:


# Getting the source name and date the directory was updated
source_dates = re.findall(r">\W([A-Z]\d{4})\W?(\d\d?/\d\d?/\d{4})",text)
unknown_source_dates = re.findall(r"\W([U]\d{9})\W?(\d\d?/\d\d?/\d{4})",text)


# In[7]:


# Making a list of directory URLs that have had updates today
updates = []
for source in source_dates:
    source_id = source[0]
    date = source[1]
    if (date == today) & (source_id in source_id_list):
        link = "https://www.deq.state.mi.us/aps/downloads/SRN/"+source[0]
        updates.append(link)
for source in unknown_source_dates:
    if (date == today) & (source_id in source_id_list):
        link = "https://www.deq.state.mi.us/aps/downloads/SRN/"+source[0]
        updates.append(link)


# In[8]:


# Reading in the most recent csv of documents
df = pd.read_csv("output/MDEQ-SRN-all-documents.csv")

# Getting a list of document urls I already have
doc_url_list = df.doc_url.to_list()


# In[9]:


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
                data['doc_type'] = re.findall(r"_([A-Z]+\d?\d?)_",link.text, re.IGNORECASE)[0]
                # Date
                data['date'] = re.findall(r"_(\d{8})", link.text)[0]
                # URL
                data['doc_url'] = "https://www.deq.state.mi.us"+link['href']
                source_data.append(data)
            
            # Save links that don't fit the regex or just don't work for some reason (misakes)
            except:
                try:
                    # Source_ID
                    other['source_id'] = re.findall(r"\w\w?\d+", directory)[0]
                    
                    # extra doc names that don't fit the regex
                    other['doc_name'] = link.text
                    
                    # extra doc URLs
                    other['doc_url'] = "https://www.deq.state.mi.us"+link['href']
                    if other['doc_name'] != '[To Parent Directory]':
                        source_extras.append(other)
                        
                    
                except:
                    # If there are still links that don't work, save them in a list
                    mistake = link
                    mistakes.append(mistake)
                    
    if len(source_data) != 0:
        all_sources_data.append(source_data)
    if len(source_extras) != 0:
        all_sources_extras.append(source_extras)


# In[10]:


# Turning my list of lists of dicts of source data into a dataframe
if len(all_sources_data) != 0:
    list_of_dfs = [pd.DataFrame(one_list) for one_list in all_sources_data]
    new_data_df = pd.concat(list_of_dfs, ignore_index=True)
    new_data_urls = new_data_df.doc_url.to_list()
    
    # Adding my new documents to my old documents
    updated_df = pd.concat([df,new_data_df], axis=0,ignore_index=True)
    
    # Overwriting the old csv with updates
    updated_df.to_csv("output/MDEQ-SRN-all-documents.csv", index=False)


# In[11]:


# Reading in my csv of extra documents
df = pd.read_csv("output/MDEQ-SRN-extra-documents.csv")


# In[12]:


# Turning my list of lists of dicts of extra documents into a dataframe
if len(all_sources_extras) != 0:
    list_of_dfs = [pd.DataFrame(one_list) for one_list in all_sources_extras]
    new_extras_df = pd.concat(list_of_dfs, ignore_index=True)
    new_extras_urls = new_extras_df.doc_url.to_list()
    
    # Adding my new documents to my old documents
    updated_df = pd.concat([df,new_extras_df], axis=0, ignore_index=True)
    
    # Overwriting the old csv with updates
    update_df.to_csv("output/MDEQ-SRN-extra-documents.csv", index=False)


# In[13]:


# Reading in my most recent scrape report
df = pd.read_csv("output/MDEQ-SRN-scraper-report.csv")

# Creating today's scrape report
scrape_report = []
data = {}

data['date'] = today

data['updates_found'] = len(updates)

data['source_data'] = len(all_sources_data)
    
data['source_extras'] = len(all_sources_extras)

data['mistakes'] = len(mistakes)

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


# In[14]:


report_df = pd.DataFrame(scrape_report)

# Adding the new report to the old reports
report_df = pd.concat([df,report_df], axis=0, ignore_index=True)

# Overwriting the report csv with update
report_df.to_csv("output/MDEQ-SRN-scraper-report.csv")

