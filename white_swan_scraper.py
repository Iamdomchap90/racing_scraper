import pandas as pd
import re
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


class RaceScraper:
    def __init__(self, url: str, is_tomorrow: bool = False):
        self._url = url
        self.is_tomorrow = is_tomorrow
        self.now = datetime.now()
        self.driver = None
        self.soup = ''
        self.data = []

    @property
    def url(self):
        if not self.is_tomorrow:
            return self._url
        return f'{self._url}/all/{self.get_tomorrow_date()}'

    def get_tomorrow_date(self) -> str:
        tomorrow = self.now + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")

    def get_race_time(self, time_until_race_start: str) -> str:
        match = re.match(r'(\d+)h (\d+)m', time_until_race_start)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return (self.now + timedelta(hours=hours, minutes=minutes)).strftime('%H:%M')
        return "race time unavailable"

    def initialize_driver(self):
        """Initializes the WebDriver and navigates to the URL."""
        self.driver = webdriver.Chrome()
        self.driver.get(self.url)

    def get_aus_nz_race_title(self) -> BeautifulSoup:
        """Waits for the 'AU/NZ GALLOPS' section to appear and returns the parsed HTML."""
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'AU/NZ GALLOPS')]")))
        self.soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        return self.soup.find('h2', string='AU/NZ GALLOPS')

    def get_track_names(self, title_element: BeautifulSoup) -> dict:
        """Extracts track names and their corresponding IDs."""
        race_container = title_element.find_parent('div').find_next_sibling()
        a_tags = race_container.find_all('a')
        track_names = {
            a.get_text(strip=True): a.find_parent('div').find_parent('div').get('id')
            for a in a_tags
            if a.get_text(strip=True) and a.find_parent('div').find_parent('div').get('id')
        }
        return track_names

    def collect_race_data(self, track_names: dict):
        """Collects race data and appends it to the data list."""
        for track, _id in track_names.items():
            venue_row = self.soup.find(
                lambda tag: 'e15267q10' in tag.get('class', []) and
                            'css-dr0t2h-TableRow-TableRow-TableRow-RacesRow-RacesRow-RacesRow' in tag.get('class', [])
            )
            race_links_html = venue_row.find_all('a')
            race_links = [link.attrs.get('href') for link in race_links_html]
            race_times = [self.get_race_time(link.find_all('div')[1].text) for link in race_links_html]
            for index, (link, time) in enumerate(zip(race_links, race_times), start=1):
                self.data.append({
                    'Track Name': track,
                    'Race Number': index,
                    'Race Link': link,
                    'Race Time': time
                })

    def scrape(self):
        """Orchestrates the scraping process."""
        try:
            self.initialize_driver()

            title_element = self.get_aus_nz_race_title()
            track_names = self.get_track_names(title_element)
            self.collect_race_data(track_names)

            return pd.DataFrame(self.data)
        except Exception as e:
            return f"Web driver could not load page source due to the following error: {e}"
        finally:
            if self.driver:
                self.driver.quit()  # Ensure the driver is closed after scraping


if __name__ == "__main__":
    try:
        scraper = RaceScraper("https://www.swiftbet.com.au/racing")
        today_df = scraper.scrape()
        tomorrow_scraper = RaceScraper("https://www.swiftbet.com.au/racing", True)
        tomorrow_df = tomorrow_scraper.scrape()

        total_df = pd.concat([today_df, tomorrow_df], ignore_index=True)
        total_df.to_csv("df_races_data.csv", index=False)
    except TypeError as e:
        print(f"Something went wrong. At least one of the scrapers didn't return a dataframe: {e}")
