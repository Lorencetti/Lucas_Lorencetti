import os
from datetime import datetime, timedelta
import logging
import re
import requests
import zipfile
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook
from robocorp.tasks import task
from RPA.Browser.Selenium import Selenium
from RPA.Robocorp.WorkItems import WorkItems

# Configure the logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S',
                    handlers=[
                        logging.FileHandler("./output/news_crawler.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

def retry_on_failure(task_name):
    """
        Decorator to retry the function if it fails by closing the popup and retrying.
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.warning("Failed to complete %s: %s", task_name, e)
                self.close_popup()
                try:
                    return func(self, *args, **kwargs)
                except Exception as exc:
                    logger.error("Retrying %s failed: %s", task_name, exc)
                    raise
        return wrapper
    return decorator

class NewsCrawlerBot:
    """
        A bot that collects news from a given URL.
    """

    def __init__(self, url: str, search_phrase: str, category: str = "",
                 time_option: int = 0):
        """
            A bot that collects news from a given URL.

            Attributes:
                url (str): The URL of the news website to crawl.
                search_phrase (str): The word its going to look for the number os occurrences.
                category (str): Optional. The input the bot will use on the website to search for a topic.
                time_option (int): Optional. Number of months for which you need to receive news.
                    0 or 1 - only the current month,
                    2 - current and previous month,
                    3 - current and two previous months, and so on.

            Example:
                bot = NewsCrawlerBot(url="https://apnews.com/")
        """
        self.url = url
        self.search_phrase = search_phrase
        self.category = category
        self.time_option = time_option
        self.selenium_instance = Selenium()
        self.current_date = datetime.now()
        self.calculate_date_range(time_option)
        self.news_list = []

        logger.info("Collecting news from %s", self.url)

    def open_browser(self):
        """
            Opens the WebDriver
        """
        try:
            self.selenium_instance.set_selenium_page_load_timeout(30)
            self.selenium_instance.open_chrome_browser(self.url)
            logger.info("Browser opened successfully!")
        except Exception as e:
            logger.error("Failed to open the browser: %s", e)

    @retry_on_failure('search')
    def search(self):
        """
            Search the previously defined search phrase.
        """
        try:
            self.selenium_instance.click_button_when_visible("css:#onetrust-accept-btn-handler")
            self.selenium_instance.click_button_when_visible("class:SearchOverlay-search-button")
            self.selenium_instance.input_text_when_element_is_visible(
                "class:SearchOverlay-search-input", self.category)
            self.selenium_instance.click_button_when_visible("class:SearchOverlay-search-submit")
            logger.info("Search completed successfully!")
            self.selenium_instance.select_from_list_by_value("class:Select-input","3")
            logger.info("Selected option 3 Newest!")
        except Exception as e:
            logger.warning("Failed to complete the search: %s", e)
            raise  # Raise the exception to trigger the retry mechanism

    @retry_on_failure('get_news_info')
    def get_news_info(self):
        """
            Select the news according to its date and the time_option, and save its content on a dictionary.
        """
        try:
            self.selenium_instance.wait_until_page_contains_element(
                locator="xpath://div[@class='SearchResultsModule-results']//div[@class='PageList-items']//div[@class='PageList-items-item']")
            news_from_page = self.selenium_instance.get_webelements(
                "xpath://div[@class='SearchResultsModule-results']//div[@class='PageList-items']//div[@class='PageList-items-item']")
            for article in news_from_page:
                news_dict = {}
                words_occurrences = 0

                news_dict['date'] = self.get_news_date(article)
                if news_dict['date'] and not self.is_within_month_interval(news_dict['date']):
                    continue  # Skip to the next article if date is not within the interval

                news_dict['img_path'] = self.get_news_image_path(article)
                news_dict['title'] = self.get_news_title(article)
                news_dict['description'] = self.get_news_description(article)

                words_occurrences += self.count_word_occurrences(news_dict['title'])
                words_occurrences += self.count_word_occurrences(news_dict['description'])
                news_dict['words_occurrences'] = words_occurrences
                news_dict['contain_money'] = any(self.contains_money(news_dict[key]) for key in
                                                 ['description', 'title'])
                news_dict["img_path"] = self.download_image(news_dict["img_path"])

                self.news_list.append(news_dict)
                self.log_news_info(news_dict)

        except Exception as e:
            logger.warning("Failed to get the news: %s", e)
            raise  # Raise the exception to trigger the retry mechanism

    def get_news_date(self, article):
        """
            Extract the date from the news article.
        """
        try:
            try:
                date_element = self.selenium_instance.get_webelement(
                    "class:Timestamp-template", article)
            except Exception as e:
                logger.warning("Failed to get the date: %s", e)
                logger.info("Retrying to get it with the class Timestamp-template-now")
                date_element = self.selenium_instance.get_webelement(
                    "class:Timestamp-template-now", article)
            return self.parse_date_string(date_element.text)
        except Exception as e:
            logger.warning("Failed to get the date: %s", e)
            return None

    def get_news_image_path(self, article):
        """
            Extract the image path from the news article.
        """
        try:
            father = self.selenium_instance.get_webelement("class:PagePromo-media", article)
            img_path = self.selenium_instance.get_webelement("class:Image", father)
            return img_path.get_attribute("src")
        except Exception as e:
            logger.warning("Failed to get the image path: %s", e)
            return None

    def get_news_title(self, article):
        """
            Extract the title from the news article.
        """
        try:
            title = self.selenium_instance.get_webelement("class:PagePromo-title", article)
            return title.text
        except Exception as e:
            logger.warning("Failed to get the title: %s", e)
            return None

    def get_news_description(self, article):
        """
            Extract the description from the news article.
        """
        try:
            description = self.selenium_instance.get_webelement("class:PagePromo-description", article)
            return description.text
        except Exception as e:
            logger.warning("Failed to get the description: %s", e)
            return None

    def log_news_info(self, news_dict):
        """
            Logs the information of the news article.
        """
        logger.info("Title: %s", news_dict['title'])
        logger.info("Description: %s", news_dict['description'])
        logger.info("Date: %s", news_dict['date'])
        logger.info("Image path: %s", news_dict["img_path"])
        logger.info("Words occurrences: %s", news_dict['words_occurrences'])
        logger.info("Contain money: %s", news_dict['contain_money'])

    def get_every_news(self):
        """
            Get the news from every page after the initial category has been searched.
        """
        try:
            page_index_text = self.selenium_instance.get_webelement(
                "class:Pagination-pageCounts").text
            total_pages = int(page_index_text.split(" of ")[1].replace(",", "").strip())
            self.get_news_info()

            for i in range(1, total_pages):
                self.selenium_instance.click_element_when_clickable("class:Pagination-nextPage")
                logger.info("Navigating to page number: %i", i)
                self.get_news_info()
        except Exception as e:
            logger.warning("Stopped getting the news reason: %s", e)

        self.zip_images_folder("./output/images")
        self.save_to_excel(self.news_list)
        # Not needed for this project, but this function would generate the output of images
        # and the excel files as a Work Item on robocloud.
        # self.create_output_work_item()

    def extract_image_paths(self):
        """
            Extracts image paths from the news list.

            Returns:
            - image_paths (list): A list of image file paths.
        """
        image_paths = []
        for news_item in self.news_list:
            if "img_path" in news_item and news_item["img_path"]:
                image_paths.append(news_item["img_path"])
        return image_paths

    def create_output_work_item(self):
        """
            Create output work items with the paths of the Excel file and images.
        """
        try:
            excel_path = self.save_to_excel(self.news_list)
            image_paths = self.extract_image_paths()

            workitems = WorkItems()
            workitems.get_input_work_item()

            if excel_path:
                files = [excel_path] + image_paths
                workitems.create_output_work_item(files=files, save=True)
                logger.info("Output work item created with Excel file and images.")
            else:
                logger.warning("No Excel file was created, skipping output work item creation.")

        except Exception as e:
            logger.error("Failed to create output work item: %s", e)

    def close_popup(self):
        """
            Close the advertisiment popup
        """
        try:
            self.selenium_instance.click_element_when_clickable(
                "xpath://a[@class='fancybox-item fancybox-close']")
            logger.info("Popup closed successfully")
        except Exception as e:
            logger.error("Failed to close the popup: %s", e)

    def calculate_date_range(self, months: int):
        """
            Calculate the date inteval accordind to the following formula:
                < 0 - ERROR. Months must be >= 0
                0 or 1 - only the current month,
                2 - current and previous month,
                3 - current and two previous months, and so on.
        """
        if months == 0:
            months = 1

        if months <= 0:
            logging.error("Invalid input: Number of months must be greater than 0.")
            months = 1

        current_date = datetime.now()
        start_date = (current_date - relativedelta(months=months-1)).replace(day=1)
        end_date = current_date.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

        logging.debug("Calculating date range for the last %i month(s).", months)
        logging.debug("Start date: %s, End date: %s", start_date.strftime('%Y/%m'),
                      end_date.strftime('%Y/%m'))
        return start_date, end_date

    def count_word_occurrences(self, text):
        """
            Count the number of occurrences of a search_phrase in a text.

            Args:
                text (str): The text in which to search for the word.

            Returns:
                int: The number of occurrences of the search_phrase in the text.
        """
        if text is None:
            return 0
        pattern = rf'\b{re.escape(self.search_phrase)}\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return len(matches)


    def is_within_month_interval(self, parsed_date):
        """
            Check if the provided date string is within the current month interval.

            Args:
            - parsed_date: The previusly parsed date to be checked.

            Returns:
            - bool: True if the data is within the time_option data range, false otherwise.
        """
        try:
            if parsed_date is None:
                return False
            start_date, end_date = self.calculate_date_range(self.time_option)
            start_date = datetime.combine(start_date, datetime.min.time())
            end_date = datetime.combine(end_date, datetime.max.time())
            # Check if parsed_date is within the interval
            if start_date <= parsed_date <= end_date:
                return True
            else:
                return False
        except Exception as e:
            logger.warning("Failed to compare date: %s", e)
            return False

    def parse_date_string(self, date_str: str):
        """
            Parse the date string to a datetime object using regex patterns.

            Args:
            - date_str (str): The date to be parsed.

            Returns:
            - datetime: the parsed date in datetime.
        """
        today = datetime.now().date()
        patterns = [
            r'(?i)now',
            r'(?i)yesterday',
            r'(?i)(\d+) min(?:s)? ago',
            r'(?i)(\d+) hour(?:s)? ago',
            r'(?i)(\w+) (\d+),? (\d{4})?',
            r'(?i)(\w+) (\d+)',
        ]

        for pattern in patterns:
            match = re.match(pattern, date_str.strip())
            if match:
                if 'now' in pattern:
                    return datetime.now()
                elif 'min' in pattern:
                    minutes = int(match.group(1))
                    return datetime.now() - timedelta(minutes=minutes)
                elif 'hour' in pattern:
                    hours = int(match.group(1))
                    return datetime.now() - timedelta(hours=hours)
                elif 'yesterday' in pattern:
                    return datetime.combine(today - timedelta(days=1), datetime.min.time())
                elif match.lastindex == 3:  # Month, Day, Year
                    return datetime.combine(datetime.strptime(date_str, "%B %d, %Y"), datetime.min.time())
                elif match.lastindex == 2:  # Month, Day
                    return datetime.combine(datetime.strptime(date_str, "%B %d").replace(year=today.year), datetime.min.time())

        logger.warning("Failed to parse date string '%s': No matching pattern found", date_str)
        return None
    
    def contains_money(self, text):
        """
            Check if the given text contains any amount of money.

            Possible formats:
            - $11.1
            - $111,111.11
            - 11 dollars
            - 11 USD

            Args:
            - text: The text to be checked.

            Returns:
            - bool: True if money on the given format was found, false otherwise.
        """
        if text is None:
            return False
        money_patterns = [
            r'\$\d+(\.\d+)?',            # $11.1 or $111.11
            r'\$\d{1,3}(,\d{3})*\.\d+',  # $111,111.11
            r'\d+\s*dollars?',           # 11 dollars or 111 dollars
            r'\d+\s*USD'                 # 11 USD or 111 USD
        ]
        money_regex = re.compile('|'.join(money_patterns), re.IGNORECASE)
        if money_regex.search(text):
            return True
        else:
            return False

    def zip_images_folder(self, input_folder: str, 
                          output_folder: str = "./output", zip_filename: str = "images.zip"):
        """
            Zips all images in the specified input folder and saves them on the output folder.

            Args:
            - input_folder (str): Path to the folder containing the images to zip.
            - output_folder (str): Path to the folder where the zip file will be saved.
                                    Default is './output'.
            - zip_filename (str): The name of the zip file to create. Default is 'images.zip'.

            Returns:
            - str: The path to the created zip file.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        zip_path = os.path.join(output_folder, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(input_folder):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, input_folder))

        return zip_path

    def download_image(self, url: str):
        """
            Downloads an image from a given URL and saves it to the specified path.

            Parameters:
            url (str): The URL of the image to download.
            
            Returns: 
            save_path (str): The file path of the downloaded image.
            None : Download failed or no URL was given.
        """
        if url is None:
            return None

        save_dir = os.path.join(os.getcwd(), 'output', 'images')
        os.makedirs(save_dir, exist_ok=True)
        existing_files = os.listdir(save_dir)
        image_count = sum(
            1 for file in existing_files if file.startswith("image_") and file.endswith(".jpg"))
        image_name = f"image_{image_count + 1}.jpg"
        save_path = os.path.join(save_dir, image_name)
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()  # Check if the request was successful
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)  
            logger.info("Image successfully downloaded and saved to %s", save_path)
            return save_path
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to download image: %s", e)
            return None

    def save_to_excel(self, data_list: list):
        """
            Save a list of dictionaries to an Excel file.

            Args:
            - data_list (list[dict]): List of dictionaries where each one represents a row of data.

            Returns:
            - file_path: The path where the generated excel file is located.
        """
        try:
            save_dir = os.path.join(os.getcwd(), 'output')
            file_path = os.path.join(save_dir, "result.xlsx")

            wb = Workbook()
            ws = wb.active
            if data_list:
                headers = list(data_list[0].keys())
                ws.append(headers)
                for item in data_list:
                    row_data = [item.get(header, '') for header in headers]
                    ws.append(row_data)
            wb.save(file_path)
            return file_path
    
        except Exception as e:
            logger.error("Failed to save Excel file: %s", e)
            return None

    def run(self):
        """
            Runs the bot
        """
        try:
            self.open_browser()
            self.search()
            self.get_every_news()
        except Exception as e:
            logger.error("Failed to run the bot: %s", e)

@task
def run_robot():
    """
        Initialize and runs the robot with the given work items as inputs.
    """
    workitems = WorkItems()
    item = workitems.get_input_work_item()
    try:
        payload = item.payload
        category = payload["category"]
        search_phrase = payload["search_phrase"]
        time_option = payload["time_option"]
        assert isinstance(category, str), "Category must be a string"
        assert isinstance(search_phrase, str), "Search phrase must be a string"
        assert isinstance(time_option, int) and time_option > 0, "Time option must be an integer greater than 0"
    except AssertionError as err:
        print("BUSINESS", code="INVALID_INPUT", message=str(err))
    except KeyError as err:
        print("APPLICATION", code="MISSING_FIELD", message=f"Missing field: {err}")
    except Exception as err:
        print("APPLICATION", code="GENERAL_ERROR", message=str(err))
    bot = NewsCrawlerBot(url="https://apnews.com/",
                          category=category, time_option=time_option, search_phrase=search_phrase)
    bot.run()
