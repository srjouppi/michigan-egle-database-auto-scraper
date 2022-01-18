# michigan-deq-auto-scraper
 :mag: Scrapes the MDEQ SRN database daily at ~11:45pm, looking for new documents from that day and adding them to existing databases
 
 ### :open_file_folder: output
 ---
 * ` MDEQ-SRN-documents-source-info.csv`: A database of MDEQ communication with known sources of air pollution. Field include:
  - name: Name of company
  - doc_type: Type of document (Violation notice, test report, etc.)
  - dat
  - zip_code
  - county
  - address
  - source_id: the MDEQ ID number given to each source of air pollution
  - geometry: latitude and longitude
  - doc_url: link to the document hosted on the MDEQ website
 
 :clipboard: Creates a report for each day detailing:
 1. The number directories where an update was posted.
 2. The number of new URL's it found 
 3. Lists the new URL's found
