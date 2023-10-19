# scraper-demo

## What is this script?
This script will scrape the NFL 2023 schedule from pro-football-reference.com, and then output that data as a CSV. The point of this example is to show a simple python scraper implementation using a reusable BaseScraper class that leverages BeatifulSoup. You can create your own scraper that inherits from BaseScraper in the same way that is show here.

## How to run:

### 1. Clone repository
```bash
git clone https://github.com/brayk2/scraper-demo.git
cd scraper-demo
```

### 2. Install dependencies with poetry
```bash
poetry install
```

### 3. Run the script
```bash
poetry run python3 main.py
```

### 4. Observe output
The script will output a csv file "2023_nfl_schedule.csv". This file will contain the scraping results.
