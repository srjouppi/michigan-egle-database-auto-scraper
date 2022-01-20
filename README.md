# michigan-egle-database-auto-scraper
 ### :mag: Scrapes the Michigan [Database of Air Pollution Records](https://www.deq.state.mi.us/aps/downloads/SRN/) daily at ~11:45pm.

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
:gem: `EGLE-AQD-documents-source-info.csv`

A dataset of Michigan Department of Environment, Great Lakes, and Energy (EGLE) communication with known sources of air pollution. Fields include:
- name: Name of company
- doc_type: Type of document
- date: Date document issued
- zip_code: Zip code of the source of pollution
- county
- address
- geometry: Latitude and longitude
- source_id: The EGLE ID number given to each source of air pollution
- doc_url: link to the document hosted on the EGLE database
 
:blue_book: `EGLE-AQD-documents.csv`

A dataset of communications by just source_id. Does not contain any indentifying information.

:green_book: `EGLE-AQD-extra-documents.csv`

A dataset of extra documents that don't have dates, like "Active PTIs" (Permits to install).

:clipboard: `EGLE-AQD-scraper-report.csv`

Creates a report for each day detailing:
- The number of directories where an update was posted
- The number of new URL's it found 
- Lists the new URL's found


### :nut_and_bolt: Process
---
EGLE has a [master list](https://www.deq.state.mi.us/aps/downloads/SRN/Sources_By_ZIP.pdf) of sources of air pollution its tracking in the state.

Using Beautiful Soup, I scraped over 18,000 documents for these sources of air pollution. With Regex, I extracted the urls of the documents as well as data from the documents' names, which were all structured predicably as such:

#### {SOURCE ID}\_{TYPE OF DOCUMENT}\_{DATE ISSUED}.pdf

I joined the scraped data with identifing information (name, location) from the master list.

This scraper uses Beautiful Soup and Regex to search the database for directories that have new updates, go into those folders and search for URLs that are not already in the dataset \(`EGLE-AQD-documents.csv`\).

### Note
---
To better understand what exactly is on their database: you should call the EGLE's Air Quality Division. It's on my list of things to do, but alas, I'm in the throes of grad school and motherhood.

*Next* on my list is to download all of these pdfs for safe keeping. But until then, happy exploring!
