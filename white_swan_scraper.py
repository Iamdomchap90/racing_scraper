import pandas as pd
import re
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


URL = "https://www.swiftbet.com.au/racing"
NOW = datetime.now()


def get_tomorrow_date():
    TOMORROW = NOW + timedelta(days=1)
    return TOMORROW.strftime("%Y-%m-%d")


def get_race_time(time_until_race_start):
    match = re.match('(\\d+)h (\\d+)m', time_until_race_start)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return (NOW + timedelta(hours=hours, minutes=minutes)).strftime('%H:%M')
    return "race time unavailable"


try:
    driver = webdriver.Chrome()
    driver.get(URL)
    wait = WebDriverWait(driver, 10)
    aus_nz_race_title_element = wait.until(
        EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'AU/NZ GALLOPS')]"))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    aus_nz_race_title_element = soup.find('h2', string='AU/NZ GALLOPS')

    if aus_nz_race_title_element:
        race_container = aus_nz_race_title_element.find_parent('div').find_next_sibling()
        a_tags = race_container.find_all('a')
        track_names = {
            a.get_text(strip=True): a.find_parent('div').find_parent('div').get('id')
            for a in a_tags
            if a.get_text(strip=True) and a.find_parent('div').find_parent('div').get('id')
        }
        print("TRACK NAMES: ", track_names)
        data = []

        for track, _id in track_names.items():
            print("Track ID: ", _id)
            venue_row = soup.find(
                lambda tag: 'e15267q10' in tag.get('class', []) and
                            'css-dr0t2h-TableRow-TableRow-TableRow-RacesRow-RacesRow-RacesRow' in tag.get('class', [])
            )
            race_links_html = venue_row.find_all('a')
            race_links = [link.attrs.get('href') for link in race_links_html]
            race_times = [get_race_time(link.find_all('div')[1].text) for link in race_links_html]
            print("RACE times: ", race_times)
            for index, (link, time) in enumerate(zip(race_links, race_times), start=1):
                data.append({
                    'Track Name': track,
                    'Race Number': index,
                    'Race Link': link,
                    'Race Time': time
                })

                # Create DataFrame from the collected data
        df = pd.DataFrame(data)
        print("DF: ", df)

except Exception as e:
    print(f"Web driver could not load page source due to follwing error: {e}")

