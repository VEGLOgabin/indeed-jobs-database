import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time
import validators
from datetime import datetime
import sys
import pandas as pd
import os
import random

# Get the input CSV file name
CSV_file = input('Enter the CSV file name (e.g., file.csv): ')
CSV = CSV_file.split('-')[1]

# Prompt the user to choose which database filters to process
filter_choice = input("Which Database Filter(s) do you need processed? Please choose one of the following:\n=> Enter 'A' for both\n=> Enter 'T' for Yes-King Only\n=> Enter 'F' for No-King Only\n").strip().upper()

# Define the current timestamp
date_time = datetime.now().strftime("%Y.%m.%d_%H_%M")

# Define output filenames for the filtered files
filtered_csv_no = f"02-{CSV}-No_King_Filtered-{date_time}.csv"
filtered_csv_yes = f"02-{CSV}-Yes_King_Filtered-{date_time}.csv"

# Define log file name
log_file_name = f"Script_2-{CSV}-Logs-{date_time}.txt"

# Redirect stdout to a log file
original_stdout = sys.stdout
log_file = open(log_file_name, "w", encoding="utf-8")
sys.stdout = log_file

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # chrome_options.add_argument(f"user-data-dir=C:\\Users\\Shayan\\AppData\\Local\\Google\\Chrome\\User Data\\Default")
    chrome_options.add_argument(f"user-data-dir=C:\\Users\\ssmcse\\AppData\\Local\\Google\\Chrome\\User Data\\Default")
    chrome_options.add_argument("--log-level=3")
    chrome_driver_path = "C:\\chromedriver-win64\\chromedriver.exe"
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def read_csv_files(file1, file2):
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    return df1, df2

def print_total_data_info(df2):
    total_rows = len(df2)
    total_companies = df2['Company Name'].nunique()
    total_locations = df2['Location'].nunique()
    custom_print(f'==>  Total Data in the File: {total_rows}')
    custom_print(f'==>  Total Unique Companies in the File: {total_companies}')
    custom_print(f'==>  Total Unique Locations in the File: {total_locations}\n')

def remove_companies(df1, df2):
    companies_to_delete = df1['Employers_To_Delete'].dropna().str.lower().unique()
    initial_row_count = len(df2)
    original_company_names = df2['Company Name']
    
    # Ensure all values in 'Company Name' are strings
    df2['Company Name'] = df2['Company Name'].astype(str).str.lower()
    
    mask = ~df2['Company Name'].apply(lambda x: any(term in x for term in companies_to_delete if isinstance(x, str)))
    df2['Company Name'] = original_company_names  # Restore original case
    df2_filtered = df2[mask]
    rows_deleted = initial_row_count - len(df2_filtered)
    custom_print(f'==>  Rows Deleted Based on Companies: {rows_deleted}')
    return df2_filtered

def remove_locations(df1, df2):
    locations_to_delete = df1['Locations_To_Delete'].dropna().unique()
    initial_row_count = len(df2)
    for location in locations_to_delete:
        df2 = df2[~df2['Location'].str.contains(location, na=False, case=False)]
    rows_deleted = initial_row_count - len(df2)
    custom_print(f'==>  Rows Deleted Based on Locations: {rows_deleted}\n')
    return df2

def save_filtered_csv(df, output_file):
    df.to_csv(output_file, index=False)
    custom_print(f'Total Data Remaining in Filtered Data: {len(df)}')

def filter_csv_by_database(input_csv_file, database_file, output_csv_file):
    df_database, df_input = read_csv_files(database_file, input_csv_file)
    print_total_data_info(df_input)
    df_filtered = remove_companies(df_database, df_input)
    df_filtered = remove_locations(df_database, df_filtered)
    save_filtered_csv(df_filtered, output_csv_file)

def filter_dollar_and_expired_jobs(driver, input_csv_file, output_csv_file):
    with open(input_csv_file, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        rows = list(reader)

    custom_print("\n++++++++++++++++++++++++++++++++++++++++++++++")
    custom_print(f"CSV Contains {len(rows)-1} Records")
    custom_print("++++++++++++++++++++++++++++++++++++++++++++++\n")

    rows_to_keep = [rows[0]]

    with open(output_csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(rows_to_keep[0])  

        row_count = 1
        for row in rows[1:]:
            job_url = row[-2].strip()
            
            wait_time = random.randint(1, 4)

            if not job_url:
                custom_print(f"Removing Row {row_count}/{len(rows)-1} Due To Empty Job URL")
                row_count += 1    
                continue

            if not validators.url(job_url):
                custom_print(f"Removing Row {row_count}/{len(rows)-1} Due To Invalid Job URL")
                row_count += 1 
                continue

            try:
                driver.get(job_url)
                job_descriptions = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#viewJobSSRRoot > div > div.css-1quav7f.eu4oa1w0 > div > div > div.jobsearch-JobComponent.css-u4y1in.eu4oa1w0"))
                )

                if "$" in job_descriptions[0].text:
                    custom_print(f"Removing Row {row_count}/{len(rows)-1} Due To Dollar Sign '$'")
                    row_count += 1 
                    time.sleep(wait_time)
                    # custom_print(f"=> Sleeping: {wait_time} seconds")
                    continue

                elif "job has expired" in job_descriptions[0].text:
                    custom_print(f"Removing Row {row_count}/{len(rows)-1} Due To 'Job Expired'")
                    row_count += 1 
                    time.sleep(wait_time)
                    # custom_print(f"=> Sleeping: {wait_time} seconds")
                    continue      

                else:
                    writer.writerow(row)
                    custom_print(f"****** **** Keeping Row {row_count}/{len(rows)-1} **** ******")
                    row_count += 1
                    time.sleep(wait_time)
                    # custom_print(f"=> Sleeping: {wait_time} seconds")
                    
            except Exception as e:
                custom_print(f"Skipping Row {row_count}/{len(rows)-1} Due To CAPTCHA or Other Error - Retrying ....")
                driver.quit()
                
                time.sleep(wait_time)
                time.sleep(10)
                custom_print(f"=> Sleeping: {wait_time} seconds + 10 seconds extra sleep for CAPTCHA")
                
                driver = initialize_driver()
                
                try:
                    driver.get(job_url)
                    job_descriptions = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#viewJobSSRRoot > div > div.css-1quav7f.eu4oa1w0 > div > div > div.jobsearch-JobComponent.css-u4y1in.eu4oa1w0"))
                    )

                    if "$" in job_descriptions[0].text:
                        custom_print(f"Removing Row {row_count}/{len(rows)-1} Due To Dollar Sign '$'")
                        row_count += 1 
                        time.sleep(wait_time)
                        continue

                    elif "job has expired" in job_descriptions[0].text:
                        custom_print(f"Removing Row {row_count}/{len(rows)-1} Due To 'Job Expired'")
                        row_count += 1 
                        time.sleep(wait_time)
                        continue      

                    else:
                        writer.writerow(row)
                        custom_print(f"****** **** Keeping Row {row_count}/{len(rows)-1} **** ******")
                        row_count += 1
                        time.sleep(wait_time)

                except Exception as e:
                    custom_print(f"Skipping Row {row_count}/{len(rows)-1} After Retry Due To CAPTCHA or Other Error")
                    row_count += 1
                    time.sleep(wait_time)
                    time.sleep(10)
                    custom_print(f"=> Sleeping: {wait_time} seconds + 10 seconds extra sleep for CAPTCHA")
                
            time.sleep(2)

    second_csv_row_count = 0
    with open(output_csv_file, 'r', newline='', encoding="utf-8") as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            second_csv_row_count += 1

        custom_print(f"Total rows was: {len(rows)-1} | Removed: {(len(rows)-1) - (second_csv_row_count-1)} | Remaining: {second_csv_row_count-1} ")
        custom_print(f"\nOutput CSV File: {output_csv_file}")

def custom_print(*args, **kwargs):
    print(*args, **kwargs, file=original_stdout)
    with open(log_file_name, "a", encoding="utf-8") as log_file:
        print(*args, **kwargs, file=log_file)

def main():
    custom_print("\n")
    custom_print("<<<<< ----- Script: 2 - Indeed Job Filter (DB + Dollar) by AHMAD S. for DOMAINSTERS LLC ----- >>>>>")
    custom_print("--------------------------------------------")
    
    process_two_start_time = datetime.now().strftime("%Y.%m.%d_%H_%M")
    custom_print("\n<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    custom_print(f"Initiating The Final Script at: {process_two_start_time}")
    custom_print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")

    custom_print("Which Database Filter(s) do you need processed? Please choose one of the following:\n=> Enter 'A' for both\n=> Enter 'T' for Yes-King Only\n=> Enter 'F' for No-King Only\n")
    custom_print(f"User selected filter option: {filter_choice}")

    db_file_no = 'Indeed_Local_Database_NO.csv'
    db_file_yes = 'Indeed_Local_Database_YES.csv'

    if filter_choice == 'A':
        custom_print("\n<===     Filtering by Indeed_Local_Database_NO.csv    ===>\n")
        filter_csv_by_database(CSV_file, db_file_no, filtered_csv_no)

        custom_print("\n<===     Final Filtering for the NO_KING Database    ===>\n")
        driver = initialize_driver()
        filter_dollar_and_expired_jobs(driver, filtered_csv_no, f"03-{CSV}-No_King_Final_Data-{date_time}.csv")
        driver.quit()

        custom_print("\n<===     Filtering by Indeed_Local_Database_YES.csv    ===>\n")
        filter_csv_by_database(CSV_file, db_file_yes, filtered_csv_yes)

        custom_print("\n<===     Final Filtering for the YES_KING Database    ===>\n")
        driver = initialize_driver()
        filter_dollar_and_expired_jobs(driver, filtered_csv_yes, f"03-{CSV}-Yes_King_Final_Data-{date_time}.csv")
        driver.quit()

    elif filter_choice == 'T':
        custom_print("\n<===     Filtering by Indeed_Local_Database_YES.csv    ===>\n")
        filter_csv_by_database(CSV_file, db_file_yes, filtered_csv_yes)

        custom_print("\n<===     Final Filtering for the YES_KING Database    ===>\n")
        driver = initialize_driver()
        filter_dollar_and_expired_jobs(driver, filtered_csv_yes, f"03-{CSV}-Yes_King_Final_Data-{date_time}.csv")
        driver.quit()

    elif filter_choice == 'F':
        custom_print("\n<===     Filtering by Indeed_Local_Database_NO.csv    ===>\n")
        filter_csv_by_database(CSV_file, db_file_no, filtered_csv_no)

        custom_print("\n<===     Final Filtering for the NO_KING Database    ===>\n")
        driver = initialize_driver()
        filter_dollar_and_expired_jobs(driver, filtered_csv_no, f"03-{CSV}-No_King_Final_Data-{date_time}.csv")
        driver.quit()

    else:
        custom_print("Invalid choice. Please enter 'A', 'T', or 'F'.")
        sys.exit(1)

    process_two_completion_time = datetime.now().strftime("%Y.%m.%d_%H_%M")
    custom_print("\n<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    custom_print(f"Final Script Completed at: {process_two_completion_time}")
    custom_print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
    custom_print("********** ******* ***** COMPLETED ******* ***** *******\n")
    
    custom_print("<<<<<<<<<<<<<<<<<<<<<<<< TimeStamps >>>>>>>>>>>>>>>>>>>>>>>>>>>")
    custom_print(f"Initiated The Final Script at: {process_two_start_time}")
    custom_print(f"Final Script Completed at: {process_two_completion_time}")
    custom_print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")

    log_file.close()
    sys.stdout = original_stdout

if __name__ == "__main__":
    main()
