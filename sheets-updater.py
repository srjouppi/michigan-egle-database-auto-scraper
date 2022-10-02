# Importing required libraries
import pygsheets
from pygsheets.datarange import DataRange
import pandas as pd
  
# Create the cietn and enter 
gc = pygsheets.authorize(service_account_env_var = 'sheets_service_auth')

# Grab the spreadsheet
sh1 = gc.open('EGLE AQD Document Database')
sh2 = gc.open('EGLE AQD Document Database - Last 90 Days')
# Grab the worksheet
wks1 = sh1.worksheet_by_title("data")
wks2 = sh2.worksheet_by_title("data")

# Define a dataframe
df1 = pd.read_csv('output/EGLE-AQD-document-dataset-full.csv')
df2 = pd.read_csv('output/EGLE-AQD-document-dataset-90days.csv')

# Assign the dataframe to the worksheet
wks1.set_dataframe(df1, start='A1', fit=True)
wks2.set_dataframe(df2, start='A1', fit=True)

# Freeze the first row
wks1.frozen_rows=1
wks2.frozen_rows=1

# Bold the first row
model_cell1 = wks1.cell('A1')
model_cell2 = wks2.cell('A1')

model_cell2.set_text_format('bold', True)
model_cell2.set_text_format('bold', True)

drange1 = pygsheets.datarange.DataRange(start='A1', end='Q1', worksheet=wks1)
drange2 = pygsheets.datarange.DataRange(start='A1', end='Q1', worksheet=wks2)

drange1.apply_format(model_cell1)
drange2.apply_format(model_cell2)