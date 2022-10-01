# michigan-egle-database-auto-scraper
 ### :mag: Scrapes the Michigan [Database of Air Polluter Records](https://www.egle.state.mi.us/aps/downloads/SRN/) daily at ~11:45pm EST.

It looks for new documents from that day and adds them to existing datasets.

The database contains documents for each known source of air pollution in the state. Documents like:

* Stack Test Reports
* Compliance Evaluations
* Violation Notices
* Enforcement Notices
* Staff Activity Reports
* and more! :sparkles:


 ### :open_file_folder: /output/
 ---
:gem: `EGLE-AQD-document-dataset-full.csv`

A dataset of Michigan Department of Environment, Great Lakes, and Energy (EGLE) communication with known sources of air pollution. Fields include:

DOC INFO:

- **facility_name:** Name of company or facility
- **doc_type:** Document type code (ie "VN")
- **type_name:** Name of document type (ie "Violation Notice"). Please reference README in `EGLE-AQD-document-code-key.xlsx` for caveats.
- **date:** Date document issued
- **doc_url:** Link to the document hosted on the EGLE database

SOURCE INFO:

- **epa_class:** EPA classification of the source (ie "Major")
- **district_name:** EGLE district where facility is located
- **staff:** EGLE staff member assigned to facility
- **srn:** EGLE-issued identification number (can be cross referenced with EPA databases)

LOCATION INFO:

_NOTE: This is taken from FOIA'd source list. Use with caution. I have noticed inconsistencies. Sometimes address and zip code are related to the main facility, and not necessarily a specific plant._

- **address**
- **city**
- **zip code**
- **county**

 
:blue_book: `EGLE-AQD-document-dataset-90days.csv`

A lightweight dataset of the most recent documents from the past 90 days.

:green_book: `EGLE-AQD-extra-documents.csv`

A dataset of extra documents that don't have dates, like "Active PTIs" (Permits to install).

:clipboard: `EGLE-AQD-scraper-report.csv`

Creates a report for each day detailing:
- Number of sources that had updates
- Number of documents found by type (ie, "VN" (Violation Notice) or "ENFN" (Enforcement Notice))
- Number of extra documents found

### :nut_and_bolt: Process
---
EGLE provided me with a list of sources by their type (Major, Minor, Synthetic Minor, Megasite) via a FOIA request in May of 2022. Using this list, I searched their database for the source codes. 

They also keep an updated [master list](https://www.egle.state.mi.us/aps/downloads/SRN/Sources_By_ZIP.pdf) of sources of air pollution on the website.

Using Beautiful Soup, I scraped over 18,000 documents for these sources of air pollution. With Regex, I extracted the urls of the documents as well as data from the documents' names, which were all structured predicably as such:

#### {SOURCE ID}\_{TYPE OF DOCUMENT}\_{DATE ISSUED}.pdf

I joined the scraped data with identifing information (name, location, source type) from the master list. I also created a document code key \(`EGLE-AQD-document-code-key.xlsx`\) manually so users can easily see what kind of document they are looking at.

This scraper uses Beautiful Soup and Regex to search the database for directories that have new updates, go into those folders and search for URLs that are not already in the dataset \(`output/EGLE-AQD-document-dataset-full.csv`\).

### Note
---
To better understand what exactly is on their database: you should call the EGLE's Air Quality Division. For instance, it's easy to assume that the violation notices are *emissions* violations, however many times they are data reporting or other procedural violations.

*Next* on my list is to download all of these pdfs for safe keeping. But until then, happy exploring!
