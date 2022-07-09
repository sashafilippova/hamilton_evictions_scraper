# imports
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.support.ui import Select    # for drop-down menu
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import time

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
                "case_number": [], "court": [], "case_caption": [], "judge": [], 
                "filed_date": [], "case_type": [], "amount": [], "disposition": [], 
                "plaintiff_name": [], "plaintiff_address": [], "defendant_name": [], 
                "defendant_address": [], "court_id": []}

        # Initialize a Chrome webdriver and navigate to the starting webpage 
        chrome_options = Options()
        #chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(webdriver_location, options=chrome_options)
        self.driver.get("https://www.courtclerk.org/records-search/municipal-civil-listing-by-classification/")
        


    def run_scraper(self):
        """
        Main function scraping eviction cases. 
        
        Returns pandas dataframe. 
        """
        self.__process_search_webpage()

        # Show all records on one page 
        all_rows = self.driver.find_element("xpath", "/html/body/div[1]/div[3]/button")
        all_rows.click()

        search_tab_handle = self.driver.current_window_handle

        #records = self.driver.find_elements('xpath', '//*[@id="munciv_classlist_table"]/tbody/tr/td[1]')
        #self.eviction_cases_list = [i.text for i in records]  # case ids

        # Create a list of links to case summary of all court records. 
        # td[5] specifies to use case summary, not case documents link
        records_xpath_list = self.driver.find_elements('xpath', "//td[5]/form")

        for record in records_xpath_list[:1]:
            record.click()

            # switch focus to the newly open tab to scrape data
            self.driver.switch_to.window(self.driver.window_handles[1])

            # open parties table with plaintiff and defendant info
            parties_table = self.driver.find_element('xpath', '/html/body/div[1]/table/tbody/tr[1]/td[2]/form[4]')
            parties_table.click()

            # scrape case data and add it to the dictionary
            self.eviction_cases["case_number"].append(None) 
            self.eviction_cases["court"] 
            self.eviction_cases["case_caption"] 
            self.eviction_cases["judge"] 
            self.eviction_cases["filed_date"] 
            self.eviction_cases["case_type"] 
            self.eviction_cases["amount"]
            self.eviction_cases["disposition"]
            self.eviction_cases["plaintiff_name"]
            self.eviction_cases["plaintiff_address"]
            self.eviction_cases["defendant_name"]
            self.eviction_cases["defendant_address"]
            self.eviction_cases["court_id"]

            # close this tab to return to the main tab with all records
            self.driver.close()

            time.sleep(1)

        
        
        return self.driver


    def __process_search_webpage(self):

        # Use selenium.webdriver.support.ui.Select that we imported above to grab the Select element
        dropdown = Select(self.driver.find_element("name", "ccode"))
        dropdown.select_by_value("G")

        beg_date = self.driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[1]")
        final_date = self.driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[2]")

        # Then we'll fake typing into it
        beg_date.send_keys(self.start_date)
        final_date.send_keys(self.end_date)

        # Now we can grab the search button and click it
        search_button = self.driver.find_element("xpath", "/html/body/div[1]/div/div[2]/form/input[4]")
        search_button.click()
