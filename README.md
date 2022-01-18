# michigan-deq-auto-scraper
 :mag: Scrapes the Michigan Department of Environmental Quality's [database of communication](https://www.deq.state.mi.us/aps/downloads/SRN/) with sources of air pollution daily at ~11:45pm.
 It looks for new documents from that day and adds them to existing databases.

 
 ### :open_file_folder: /output/
 ---
:gem: ` MDEQ-SRN-documents-source-info.csv`

A dataset of MDEQ communication with known sources of air pollution. Fields include:
- name: Name of company
- doc_type: Type of document (Violation notice, test report, compliance evaluation report etc.)
- date: Date document issued
- zip_code: Zip code of the source of pollution
- county
- address
- geometry: latitude and longitude
- source_id: the MDEQ ID number given to each source of air pollution
- doc_url: link to the document hosted on the MDEQ website
 
:blue_book: ` MDEQ-SRN-documents.csv`

A dataset of communications by just source_id. Does not contain any indentifying information.

:green_book: `MDEQ-SRN-extra-documents.csv`

A dataset of extra documents that don't have dates, like "Active PTIs" (Permits to install).

:clipboard: `MDEQ-SRN-scraper-report.csv`

Creates a report for each day detailing:
- The number of directories where an update was posted
- The number of new URL's it found 
- Lists the new URL's found


### :nut_and_bolt: Process
---
The Michigan DEQ has a [master list](https://www.deq.state.mi.us/aps/downloads/SRN/Sources_By_ZIP.pdf) of sources of air pollution its tracking in the state.

Using Beautiful Soup, I scraped over 18,000 documents for these sources of air pollution. With Regex, I extracted the urls of the documents as well as data from the documents' names, which were all structured predicably as such:

#### {SOURCE ID}\_{TYPE OF DOCUMENT}\_{DATE ISSUED}.pdf

I joined the scraped data with identifing information (name, location) from the master list.

This scraper uses Beautiful Soup and Regex to search the database for directories that have new updates, go into those folders and search for URLs that are not already in the dataset \(`MDEQ-SRN-documents.csv`\).

### Note
---
To better understand what exactly is on their database: you should call the MDEQ. It's on my list of things to do, but alas, I'm in the throes of grad school and motherhood.

*Next* on my list is to download all of these pdfs for safe keeping. But until then, happy exploring!
