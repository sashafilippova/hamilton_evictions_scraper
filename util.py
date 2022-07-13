# imports
from re import search
import sys

from typing_extensions import final
from selenium import webdriver
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.support.ui import Select    # for drop-down menu

import time
from datetime import datetime as dt, timedelta as tdelta
import pandas as pd
import numpy as np
import math

_EVICTION_CASES = {
                "CASE NUMBER": [], "COURT": [], "CASE CAPTION": [], "JUDGE": [], 
                "FILED DATE": [], "CASE TYPE": [], "AMOUNT": [], "DISPOSITION": [], 
                "PLAINTIFF NAME": [], "PLAINTIFF ADDRESS": [], "DEFENDANT_ATTORNEY": [],
                "DEFENDANT NAME": [], "DEFENDANT ADDRESS": [], "PLAINTIFF_ATTORNEY": []}

_KEYS_LIST = [key for key in _EVICTION_CASES.keys()]


def run_eviction_scraper(evictions_csv_path, start_date = "06062022", end_date = "06102022",
                            webdriver_location = "/Users/oleksandrafilippova/Downloads/chromedriver"):
    """
    Scrapes new eviction cases from the website. Updates cases with missing disposition.
    
    Inputs:
      evictions_csv_path (str)
      start_date (str): format mmddyyyy
      end_date (str): format mmddyyyy
      webdriver_location (str): location of Chrome webdriver on the local machine.
    """

    if end_date is None:
        end_date = dt.today().date().strftime("%m%d%Y")

    try:
        old_df = pd.read_csv(evictions_csv_path, parse_dates=['FILED DATE', 'LAST_UPDATED'])
        cases_to_check = old_df[
        old_df.DISPOSITION.isnull()]['CASE NUMBER'].to_list()
        most_recent_filing_date = old_df['FILED DATE'].max().date()
        if start_date is None:
            start_date = (most_recent_filing_date + tdelta(days = 1)).strftime("%m%d%Y") 
    except FileNotFoundError:
            return 'Unable to open file from provided csv_path. Please try again'  

    if start_date is None:
        return 'Creating a brand new file. Please provide at least Start Date' 

    # initiate class
    eviction_scraper = Eviction_Scraper(start_date, end_date, webdriver_location)
    new_df = eviction_scraper.run_scraper()

    # master_df = old_df.append(new_df, ignore_index = True)
    # master_df.to_csv(evictions_csv_path, index=False)
    return old_df, new_df, cases_to_check


################ EVICTION SCRAPER CLASS ##############################

class Eviction_Scraper:
    
    def __init__(self, start_date = "06062022", end_date = "06102022", 
        webdriver_location = "/Users/oleksandrafilippova/Downloads/chromedriver"):

        self.start_date = start_date
        self.end_date = end_date
        self.lst_time_periods = self.__date_converter()
        self.eviction_cases = _EVICTION_CASES.copy()

        # Initialize a Chrome webdriver and navigate to the starting webpage 
        chrome_options = Options()
        chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(webdriver_location, options=chrome_options)
        self.driver.get("https://www.courtclerk.org/records-search/municipal-civil-listing-by-classification/")
        

    def run_scraper(self):
        """
        Scrapes eviction court cases from the Hamilton County
        Clerk of Courts website, using "Selenium" and "Beautiful Soup" packages: 
        https://www.courtclerk.org/records-search/municipal-civil-listing-by-classification/.
        The result is either saved as a csv file or pandas df.
        """
        for start, end in self.lst_time_periods:
            self.__process_search_webpage(start, end)
            # Show all records on one page 
            self.driver.find_element("xpath", "/html/body/div[1]/div[3]/button").click() 
            self.scrape_one_period()
            self.driver.back()
        
        self.driver.quit()

        df  = pd.DataFrame(self.eviction_cases)     
        #df.set_index('CASE NUMBER', drop=True, inplace=True)
        df['FILED DATE'] = pd.to_datetime(df["FILED DATE"]).dt.date
        df['LAST_UPDATED'] = dt.today().date()
        df = df.replace(r'^\s*$', np.nan, regex=True)
        df[['DISPOSITION_DATE','DISPOSITION']]=df.DISPOSITION.str.split(pat=' - ',expand=True)

        return df

###############################################################################################
################################ UTILITY METHODS ##############################################
###############################################################################################

    def __date_converter(self, max_period = 7):
        """
        The court website limits search of records to up to 7 days. This function
        breaks a given time period into several, smaller time periods containing up to max_period days.

        Inputs:
          start_date (str): format should be mmddyyyy
          end_date (str): format should be mmddyyyy

        Returns a list of lists where each inner list represents a 
        """
        # convert dates
        start_date = dt.strptime(self.start_date,"%m%d%Y").date()
        end_date = dt.strptime(self.end_date, "%m%d%Y").date()

        # check that start date is not before end date
        assert start_date <= end_date, 'Start Date is greater than End Date. Try again'
        assert end_date <= dt.today().date(), "End Date is greater than today's date. Try again"

        number_batches = math.ceil((end_date  - start_date).days / max_period)
        end = start_date + tdelta(days = max_period)

        # add to the list the first period
        lst_periods = [[start_date.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")]]

        # add more periods to the list
        for _ in range(number_batches - 1):
            start = end + tdelta(days = 1)
            end = start + tdelta(days = max_period)
            lst_periods.append([start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")])

        lst_periods[-1][1] = end_date.strftime("%m/%d/%Y")

        return lst_periods    


    def scrape_one_period(self):

        search_tab_handle = self.driver.current_window_handle

        # Create a list of links to case summary of all court records. 
        # td[5] specifies to use case summary, not case documents link
        records_xpath_list = self.driver.find_elements('xpath', "//td[5]/form")

        self.local_records = None
        self.local_records = {key: [None] * len(records_xpath_list) for key in _KEYS_LIST}

        for i, record in enumerate(records_xpath_list):
            record.click()
            
            # switch focus to the newly open tab to scrape data
            self.driver.switch_to.window(self.driver.window_handles[1])

            # open parties table with plaintiff and defendant info
            self.driver.find_element('xpath', '/html/body/div[1]/table/tbody/tr[1]/td[2]/form[4]').click()

            # get a list of all rows containing data to be scraped 
            case_summary_table_rows = self.driver.find_elements('xpath', '//*[@id="case_summary_table"]/tbody/tr')
            party_info_table_rows = self.driver.find_elements('xpath', '//*[@id="party_info_table"]/tbody/tr')
            
            # process case summary table & party contact info table rows 
            self.__extract_summary_case_data(case_summary_table_rows, i)
            self.__extract_party_info_data(party_info_table_rows, i)
            
            # close this tab to return to the main tab with all records. 
            # shift driver focus on the main page with all records 
            self.driver.close()
            self.driver.switch_to.window(search_tab_handle)

            time.sleep(1) 

        #add records to the main eviction file
        for key, value in self.local_records.items():
                self.eviction_cases[key] += value 


    def __process_search_webpage(self, start, end):
        """
        Processes search webpage by filling it out with classification code,
        start & end date periods to query the court website.

        Inputs:
          start (str): start date following format 'mm/dd/yyyy'
          end (str): end date following format 'mm/dd/yyyy'

        """
        # Use selenium.webdriver.support.ui.Select that we imported above to grab the Select element
        Select(self.driver.find_element("name", "ccode")).select_by_value("G")

        beg_date = self.driver.find_element('name', 'begdate')
        final_date = self.driver.find_element('name','enddate')

        # Then we'll fake typing into it
        beg_date.clear()
        beg_date.send_keys(start)
        final_date.clear()
        final_date.send_keys(end)

        # Now we can grab the search button and click on it
        self.driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[4]").click()

    
    def __extract_summary_case_data(self, case_summary_table_rows, i):
        """
        Takes in a list of case summary tags, unpacks them and adds case summary info
        into dictionary containing court records.  

        Inputs:
        case_summary_table_rows (lst): list of case_summary_table tags 
          where each tag represents one row
        """
        case_summary_dict = dict()

        for row in case_summary_table_rows: 
            # convert tag into string, apply upper case, and split string by ":"
            # example of row variable below: 'CASE NUMBER', 'A1111111'
            field_name, field_value = row.text.upper().split(":")

            # add field_name and field_value to dict. method strip() removes blank spaces
            # in the beginning and in the end of a string
            case_summary_dict[field_name.strip()] = field_value.strip()

        ######### MAY REMOVE LATER IF USING LOCAL LIST
        #if "DISPOSITION" not in case_summary_dict:
            #case_summary_dict['DISPOSITION'] = ""


        for key, val in case_summary_dict.items():
            self.local_records[key][i] = val 
        

    def __extract_party_info_data(self, party_info_table_rows, i):
        """
        Takes in a list of party contact info table tags, unpacks them 
        and adds them into dictionary containing court records.  

        Inputs:
        party_info_table_rows (lst): list of party_info_table tags 
          where each tag represents one column
        """
        num_parties = 0
        party_info_dict = dict()

        for row in party_info_table_rows:
            # put row fields in a list row_fields
            row_fields = [val.text.replace('\n', '') for val in \
                row.find_elements('xpath', '*')]
            party = row_fields[2]
            
            if party == 'P 1':
                party_info_dict["PLAINTIFF NAME"] = row_fields[0]
                party_info_dict["PLAINTIFF ADDRESS"] = row_fields[1]
                
                # check whether plaintiff has attorney
                if 3 in range(len(row_fields)):
                    party_info_dict["PLAINTIFF_ATTORNEY"] = row_fields[3]

            elif party == 'D 1' or ('D' in party and num_parties < 1):
                num_parties += 1
                party_info_dict["DEFENDANT NAME"] = row_fields[0]
                party_info_dict["DEFENDANT ADDRESS"] = row_fields[1]

                # check whether defendant has an attorney
                if 3 in range(len(row_fields)):
                    party_info_dict["DEFENDANT_ATTORNEY"] = row_fields[3]

        for key, val in party_info_dict.items():
            self.local_records[key][i] = val 
                


class Update_Eviction_Cases:

    def __init__(self, cases_to_update_lst, df_to_update_in, 
        webdriver_location = "/Users/oleksandrafilippova/Downloads/chromedriver"):

        # Initialize a Chrome webdriver and navigate to the starting webpage 
        chrome_options = Options()
        #chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(webdriver_location, options=chrome_options)
        self.driver.get("https://www.courtclerk.org/records-search/search-by-case-number/")

        self.cases = cases_to_update_lst
        self.df = df_to_update_in
    
    def update_cases(self):

        for case_id in self.cases:
            # enter case_id on the search page
            self.driver.find_element('name', 'casenumber').clear().send_keys(case_id)
            # find search button and click on it
            self.driver.find_element('xpath', '/html/body/div[1]/div/div[2]/form/p/input[4]')

            disposition_tag = self.driver.find_element('//*[@id="case_summary_table"]/tbody/tr[8]').text.upper()
            
            if 'DISPOSITION' in disposition_tag:
                _, field_value = disposition_tag.split(":")
                disposition_date, disposition = field_value.split('-')

                self.df[self.df['CASE NUMBER'] == case_id]['DISPOSITION_DATE'] = disposition_date.strip()
                self.df[self.df['CASE NUMBER'] == case_id]['DISPOSITION'] = disposition.strip()
                self.df[self.df['CASE NUMBER'] == case_id]['LAST_UPDATED'] = dt.today().date()

            # return on the search page
            self.driver.back()
        
        return self.df




# should be able to pass in start date (optional), end date (optional), path to csv if exists (optional),
# webdriver location
if __name__ == '__main__':
    if len(sys.argv) >= 2:
        cities = sys.argv[1:]
        run_eviction_scraper(cities)
    else:
        run_eviction_scraper()