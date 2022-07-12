# imports
from typing_extensions import final
from selenium import webdriver
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.support.ui import Select    # for drop-down menu

import time
from datetime import datetime as dt, timedelta as tdelta
import pandas as pd
import math


##############################

def run_eviction_scraper(start_date, end_date, evictions_csv_path):

    previosly_scraped_cases = pd.read_csv(evictions_csv_path, parse_dates=['FILED DATE', 'LAST_UPDATED'])
    cases_to_check = previosly_scraped_cases[
        previosly_scraped_cases.DISPOSITION.isnull()]['CASE NUMBER'].to_list()
    
    most_recent_filing_date = previosly_scraped_cases['FILED DATE'].max().date()
    
    return previosly_scraped_cases, cases_to_check


################ EVICTION SCRAPER CLASS ##############################

class Eviction_Scraper:
    
    def __init__(self, start_date = "06062022", end_date = "06102022", 
        webdriver_location = "/Users/oleksandrafilippova/Downloads/chromedriver"):

        self.start_date = start_date
        self.end_date = end_date
        self.lst_time_periods = self.__date_converter()

        self.eviction_cases = {
                "CASE NUMBER": [], "COURT": [], "CASE CAPTION": [], "JUDGE": [], 
                "FILED DATE": [], "CASE TYPE": [], "AMOUNT": [], "DISPOSITION": [], 
                "PLAINTIFF NAME": [], "PLAINTIFF ADDRESS": [], "DEFENDANT_ATTORNEY": [],
                "DEFENDANT NAME": [], "DEFENDANT ADDRESS": [], "PLAINTIFF_ATTORNEY": []}

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

        df = pd.DataFrame.from_dict(self.eviction_cases)
        df['LAST_UPDATED'] = dt.today().date()

        return df


#################### UTILITY METHODS #############################

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
        assert start_date <= end_date

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

        for record in records_xpath_list[:30]:
            record.click()
            
            # switch focus to the newly open tab to scrape data
            self.driver.switch_to.window(self.driver.window_handles[1])

            # open parties table with plaintiff and defendant info
            self.driver.find_element('xpath', '/html/body/div[1]/table/tbody/tr[1]/td[2]/form[4]').click()

            # get a list of all rows containing data to be scraped 
            case_summary_table_rows = self.driver.find_elements('xpath', '//*[@id="case_summary_table"]/tbody/tr')
            party_info_table_rows = self.driver.find_elements('xpath', '//*[@id="party_info_table"]/tbody/tr')
            
            # process case summary table & party contact info table rows 
            self.__extract_summary_case_data(case_summary_table_rows)
            self.__extract_party_info_data(party_info_table_rows)
            
            # close this tab to return to the main tab with all records. 
            # shift driver focus on the main page with all records 
            self.driver.close()
            self.driver.switch_to.window(search_tab_handle)

            time.sleep(1)     


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

        # Now we can grab the search button and click it
        self.driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[4]").click()

    
    def __extract_summary_case_data(self, case_summary_table_rows):
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

        if "DISPOSITION" not in case_summary_dict:
            case_summary_dict['DISPOSITION'] = ""


        for key, val in case_summary_dict.items():
            self.eviction_cases[key].append(val)


    def __extract_party_info_data(self, party_info_table_rows):
        """
        Takes in a list of party contact info table tags, unpacks them 
        and adds them into dictionary containing court records.  

        Inputs:
        party_info_table_rows (lst): list of party_info_table tags 
          where each tag represents one column
        """
        for row in party_info_table_rows:
            # put row fields in a list row_fields
            row_fields = [val.text.replace('\n', '') for val in \
                row.find_elements('xpath', '*')]
            party = row_fields[2]
            
            if party == 'P 1':
                self.eviction_cases["PLAINTIFF NAME"].append(row_fields[0])
                self.eviction_cases["PLAINTIFF ADDRESS"].append(row_fields[1])
                
                # check whether plaintiff has attorney
                if 3 in range(len(row_fields)):
                    self.eviction_cases["PLAINTIFF_ATTORNEY"].append(row_fields[3])
                else:
                    self.eviction_cases["PLAINTIFF_ATTORNEY"].append("")

            elif party == 'D 1':
                self.eviction_cases["DEFENDANT NAME"].append(row_fields[0])
                self.eviction_cases["DEFENDANT ADDRESS"].append(row_fields[1])

                # check whether defendant has an attorney
                if 3 in range(len(row_fields)):
                    self.eviction_cases["DEFENDANT_ATTORNEY"].append(row_fields[3])
                else:
                    self.eviction_cases["DEFENDANT_ATTORNEY"].append("")


if __name__ == '__main__':
    pass 