We need to get the cause list for a given date (today or tomorrow) and for a given state, district, court complex, and court.

But note: the cause list is huge. We might have to select a state, district, court complex, and court to get the cause list.

We can let the user specify the state, district, court complex, and court, or we can provide an option to download for a specific court.

We are going to use:

requests.Session()

BeautifulSoup for parsing


Steps for cause list:

GET the cause list search page to get the tokens and also the list of states, districts, etc. (if we don't know the codes)

But we can also let the user provide the codes? Or we can provide a way to map state, district, court complex, court to codes.

Alternatively, we can use the same session and then submit the cause list search by setting the parameters.


# eCourts Case Listing Fetcher

A Python script to fetch court listings from eCourts website (https://services.ecourts.gov.in/ecourtindia_v6/).

## Features

- Search cases by CNR number
- Search cases by case type, number, and year
- Check if cases are listed today or tomorrow
- Show serial number and court name for listed cases
- Download entire cause list for specific dates
- Save results in JSON or text format
- Command-line interface with various options

## Requirements

- Python 3.6+
- Required packages:
  - requests
  - beautifulsoup4
  - lxml

## Installation

1. Clone or download this repository
2. Install required packages:

```bash
pip install requests beautifulsoup4 lxml