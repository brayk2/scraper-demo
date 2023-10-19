import logging
from functools import cached_property
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pydantic import BaseModel


class Game(BaseModel):
    week: int
    season: int
    url: str
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    completed: bool = False


class BaseScraper:
    def __init__(self, base_url: str):
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url

    @cached_property
    def client(self):
        self.logger.info(f"creating client for: {self.base_url}")
        return httpx.Client(base_url=self.base_url, timeout=60)

    def _get_static_soup(self, url: str) -> BeautifulSoup:
        """
        Generate BeautifulSoup for a static HTML site. Fetch site using httpx client and parse response with BS4.
        :param url: the endpoint to init BeautifulSoup [full url is base_url/url]
        :return: BeautifulSoup object setup with the url param
        """
        self.logger.info(f"generating static soup: {url}")
        page = self.client.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        return soup

    def _get_dynamic_soup(self, url: str) -> BeautifulSoup:
        """
        Generate BeautifulSoup for a dynamic JS site. Open site in chromium browser then init BeautifulSoup with page contents, closing the browser on exit.
        :param url: the endpoint to init BeautifulSoup [full url is base_url/url]
        :return: BeautifulSoup object setup with the url param
        """
        self.logger.info(f"generating dynamic soup: {url}")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"{self.base_url}/{url}")
            soup = BeautifulSoup(page.content(), "html.parser")
            browser.close()
            return soup

    def get_soup(self, url: str, dynamic: bool = False) -> BeautifulSoup:
        """
        Generate BeautifulSoup for given URL and dynamic flag.
        :param url: the endpoint to init BeautifulSoup [full url is base_url/url]
        :param dynamic: flag to indicate dynamic site
        :return: BeautifulSoup object setup with the url param
        """
        self.logger.info(
            f"generating soup for request, url = {url}, dynamic = {dynamic}"
        )
        if dynamic:
            return self._get_dynamic_soup(url=url)
        return self._get_static_soup(url=url)


class PfrScraper(BaseScraper):
    """
    Subclass of BaseScraper, with base_url set to
    https://www.pro-football-reference.com. Load HTML
    using the self.get_soup() method.
    """
    def __init__(self):
        # Calling the BaseScraper's __init__ with PFR url
        super().__init__(base_url="https://www.pro-football-reference.com")

    def scrape_schedule(self) -> list[dict]:
        """
        Scrape all the week pages for the 2023 football season, and
        return the results as a list of dictionaries
        :return: list of games scraped from pfr
        """
        # hardcode year to 2023 for now
        year = 2023

        # create empty list to add all the games to
        games = []

        # iterate from 0-17 to load each week of the 2023 season
        for i in range(18):
            # using the get_soup method of the BaseScraper class, load page
            # for the corresponding week i + 1 (since i starts at 0). This
            # site is not dynamic, so regular soup is fine.
            soup = self.get_soup(url=f"years/{year}/week_{i + 1}.htm")

            # select all div elements from the page with class game_summary,
            # which contains the table of matchup data. The element will look
            # something like - <div class="game_summary"> ... </div>
            summaries = soup.find_all("div", class_="game_summary")

            # iterate over each div and parse the data from the underlying tables
            for summary in summaries:
                # find the first table element with the class teams, for a given game_summary div
                teams = summary.find("table", class_="teams")

                # the table has 3 rows: Date, Away Team, Home Team
                # ignore date for now, unpack away and home rows
                _, away_row, home_row = teams.find_all("tr")

                # within each table row there is an anchor element with
                # the team names in them, select these anchors and extract text
                away, link = away_row.find_all("a")
                home = home_row.find("a")

                # extract text and trim any whitespace from
                # beginning and end of the string
                home = home.text.strip()
                away = away.text.strip()

                # try to load the game scores, if game is in the future
                # these values will be empty strings
                away_score = away_row.find("td", class_="right").text.strip()
                home_score = home_row.find("td", class_="right").text.strip()

                # load game data into a game model
                self.logger.info(f"creating game model {home} vs {away}")
                game = Game(
                    home_team=home,
                    away_team=away,
                    week=i + 1,
                    season=year,
                    url=link.get("href"),
                )

                # if any scores were found, parse these score and add to the game model
                if home_score and away_score:
                    self.logger.info("scores found, loading results")
                    game.away_score = int(away_score)
                    game.home_score = int(home_score)
                    game.completed = link.text.strip().lower() == "final"

                # dump model to dict and add to list of games
                games.append(game.model_dump())

        # return list of all 2023 games
        return games


def save_to_csv(filename: str, data: list[dict]):
    """
    Convert a uniform list of dictionaries to a csv file
    :param filename: the name of the resulting .csv file
    :param data: the list of dictionaries to encode
    """
    if not data:
        raise ValueError("data must not be empty")

    csv_rows = [data[0].keys(), *[x.values() for x in data]]
    with open(filename, "w") as file:
        for line in csv_rows:
            file.write(",".join([str(x) for x in line]) + "\n")


# this is the scripts entrypoint: https://stackoverflow.com/questions/419163/what-does-if-name-main-do
if __name__ == '__main__':
    # create a new instance of the scraper
    scraper = PfrScraper()

    # scrape the schedule data from PFR
    games = scraper.scrape_schedule()

    # here you can do any type of postprocessing with the scraped
    # data, for example let's save the output to a .csv file
    save_to_csv(filename="2023_nfl_schedule.csv", data=games)
