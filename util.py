# imports
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.support.ui import Select    # for drop-down menu
from selenium.webdriver.support.ui import WebDriverWait
#from bs4 import BeautifulSoup
import time
import pandas as pd

def scrape_court_evictions_data(start_date = "06/06/2022", end_date = "06/10/2022"):
    """
    Main function that scrapes eviction court cases from the Hamilton County
    Clerk of Courts website, using "Selenium" and "Beautiful Soup" packages: 
    https://www.courtclerk.org/records-search/municipal-civil-listing-by-classification/.
    The result is saved as a csv file.

    Inputs:
      start_date (str): beginning date from which cases should be scraped
      end_date (str): end date 
    """

    chrome_options = Options()
    #chrome_options.add_argument("--headless")

    # Initialize a Chrome webdriver
    driver = webdriver.Chrome("/Users/oleksandrafilippova/Downloads/chromedriver", options=chrome_options)
    driver.get("https://www.courtclerk.org/records-search/municipal-civil-listing-by-classification/")

    # Use selenium.webdriver.support.ui.Select that we imported above to grab the Select element
    dropdown = Select(driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/select"))
    dropdown.select_by_value("G")

    beg_date = driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[1]")
    final_date = driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[2]")

    # Then we'll fake typing into it
    beg_date.send_keys(start_date)
    final_date.send_keys(end_date)

    # Now we can grab the search button and click it
    search_button = driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[4]")
    search_button.click()

    # show all records 
    all_rows = driver.find_element("xpath", "/html/body/div[1]/div[3]/button")
    all_rows.click()


    return driver
    #driver.quit()

class Eviction_Scraper:
    """
    scrapes eviction court cases from the Hamilton County
    Clerk of Courts website, using "Selenium" and "Beautiful Soup" packages: 
    https://www.courtclerk.org/records-search/municipal-civil-listing-by-classification/.
    The result is either saved as a csv file or pandas df.
    """
    def __init__(self, start_date = "06/06/2022", end_date = "06/10/2022", webdriver_location = "/Users/oleksandrafilippova/Downloads/chromedriver"):

        self.start_date = start_date
        self.end_date = end_date

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
        Main function scraping eviction cases. 
        
        Returns pandas dataframe. 
        """
        self.__process_search_webpage()

        # Show all records on one page 
        self.driver.find_element("xpath", "/html/body/div[1]/div[3]/button").click()

        search_tab_handle = self.driver.current_window_handle

        #records = self.driver.find_elements('xpath', '//*[@id="munciv_classlist_table"]/tbody/tr/td[1]')
        #self.eviction_cases_list = [i.text for i in records]  # case ids

        # Create a list of links to case summary of all court records. 
        # td[5] specifies to use case summary, not case documents link
        records_xpath_list = self.driver.find_elements('xpath', "//td[5]/form")

        for record in records_xpath_list[:10]:
            
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


        self.pd_df = pd.DataFrame.from_dict(self.eviction_cases)  

        return self.driver


    def __process_search_webpage(self):

        # Use selenium.webdriver.support.ui.Select that we imported above to grab the Select element
        Select(self.driver.find_element("name", "ccode")).select_by_value("G")

        beg_date = self.driver.find_element('name', 'begdate')
        final_date = self.driver.find_element('name','enddate')

        # Then we'll fake typing into it
        beg_date.send_keys(self.start_date)
        final_date.send_keys(self.end_date)

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