# RPA Project: News Automation Bot

## Overview

Welcome to the RPA Project! This project aims to automate the process of extracting data from news websites, enabling businesses to streamline tedious but critical tasks. The mission is to allow people to focus on more impactful work by automating repetitive processes.

## Challenge Description

The challenge involves building a bot that automates data extraction from a chosen news site. The goal is to demonstrate skills in RPA (Robotic Process Automation) by fetching news articles based on specific criteria and storing the results in an organized format.

### Key Objectives

- Automate data extraction from a news site.
- Parse information such as title, date, description, and images.
- Store data in an Excel file, including:
  - Article title
  - Publication date
  - Description
  - Patch to the downloaded picture (if it exists)
  - Count of search phrases
  - Is there monetary values mentioned in the text? (True of False)

### Parameters

The bot processes three parameters provided via Robocloud work items:

1. **Search Phrase**: The term to search for inside the title and description of the news.
2. **News Category**: The specific category of news to filter using the website search filter.
3. **Number of Months**: Specifies the time range of articles to retrieve (e.g., 0 for the current month, 1 for current and previous month, etc.).

## Implementation Details

### Process Flow

1. **Open the Website**: Navigate to the chosen news website.
2. **Filter by Category**: Enter the provided category in the search field.
3. **Filter by Newest**: Select the newest from the dropdown menu, for easier data access.
4. **Extract Articles**: Retrieve the latest news articles, getting only those that meet the specified time range.
5. **Data Collection**:
   - Title, date, and description.
   - Download and save the article image.
   - Count occurrences of the search phrase in the title and description.
   - Check for monetary values in the article text.
6. **Store Data**: Save all collected data into an Excel file for easy access and review.

### Tools and Technologies Used

- **Python**: The primary language used for scripting and automation.
- **Selenium (via rpaframework)**: For web navigation and data extraction.
- **OpenPyXL**: To manage Excel file operations.
- **Logging**: For effective monitoring and debugging.
- **GitHub**: Code repository for version control and collaboration.
- **Robocloud**: To run the automation process in the cloud environment.

### Code Quality

The code adheres to PEP8 standards, ensuring it is clean, maintainable, and follows best practices. An object-oriented approach is employed, providing a robust and scalable architecture. Explicit waits and error handling are incorporated to enhance resiliency.

### Bonus Features

This project not only showcases technical skills but also reflects a passion for automation and creativity. The bot is designed to handle unexpected scenarios gracefully, ensuring a smooth and efficient process.

## Getting Started

To run this project:

1. Clone the repository from GitHub.
2. Set up the environment with the necessary dependencies.
3. Configure the parameters in Robocloud.
4. Execute the bot via Robocloud to extract news articles and generate the Excel report.

## Conclusion

This RPA Project is an exciting exploration of automation in the realm of news data extraction. It demonstrates a blend of technical expertise, creativity, and a passion for process improvement. By automating these tasks, companies can focus on more strategic activities, ultimately achieving greater efficiency.

---

Thank you for considering my project. I look forward to the opportunity to contribute to your team and help drive impactful automation solutions!

