#!/usr/bin/env python3
"""
eCourts Case Listing Fetcher
Fetches case listings from eCourts website and checks for today's/tomorrow's listings
"""

import requests
import json
import argparse
import sys
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Tuple
import time

class ECourtsScraper:
    def __init__(self):
        self.base_url = "https://services.ecourts.gov.in/ecourtindia_v6/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_case_details_by_cnr(self, cnr_number: str) -> Dict:
        """Get case details using CNR number"""
        try:
            search_url = f"{self.base_url}?p=case_history/index"
            data = {
                'cnr_number': cnr_number,
                'action': 'cnr_search'
            }
            
            response = self.session.post(search_url, data=data)
            return self._parse_case_response(response.text, cnr_number=cnr_number)
        except Exception as e:
            return {"error": f"Failed to fetch case details: {str(e)}"}

    def get_case_details_by_number(self, case_type: str, case_number: str, case_year: str, state_code: str, dist_code: str, court_code: str) -> Dict:
        """Get case details using case type, number, and year"""
        try:
            search_url = f"{self.base_url}?p=case_history/case_history"
            data = {
                'state_code': state_code,
                'dist_code': dist_code, 
                'court_code': court_code,
                'case_type': case_type,
                'case_no': case_number,
                'year': case_year,
                'action': 'case_history'
            }
            
            response = self.session.post(search_url, data=data)
            return self._parse_case_response(response.text, case_number=f"{case_type}/{case_number}/{case_year}")
        except Exception as e:
            return {"error": f"Failed to fetch case details: {str(e)}"}

    def _parse_case_response(self, html_content: str, **identifiers) -> Dict:
        """Parse the HTML response to extract case details"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        case_info = {}
        case_info.update(identifiers)
        
        # Extract basic case information
        case_details_table = soup.find('table', class_='table')
        if case_details_table:
            rows = case_details_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).replace(':', '')
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        case_info[key] = value
        
        # Extract hearing dates
        hearing_dates = []
        hearing_table = soup.find('table', class_='table table-bordered')
        if hearing_table:
            rows = hearing_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    hearing_date = cells[0].get_text(strip=True)
                    purpose = cells[1].get_text(strip=True)
                    stage = cells[2].get_text(strip=True)
                    
                    if hearing_date:
                        hearing_dates.append({
                            'date': hearing_date,
                            'purpose': purpose,
                            'stage': stage
                        })
        
        case_info['hearing_dates'] = hearing_dates
        
        # Check if listed today or tomorrow
        today = datetime.now().strftime('%d/%m/%Y')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')
        
        case_info['listed_today'] = False
        case_info['listed_tomorrow'] = False
        case_info['next_hearing'] = None
        case_info['serial_number'] = None
        case_info['court_name'] = None
        
        for hearing in hearing_dates:
            if hearing['date'] == today:
                case_info['listed_today'] = True
                case_info['next_hearing'] = hearing
            elif hearing['date'] == tomorrow:
                case_info['listed_tomorrow'] = True
                case_info['next_hearing'] = hearing
        
        return case_info

    def download_cause_list(self, state_code: str, dist_code: str, court_code: str, date: str = None) -> List[Dict]:
        """Download entire cause list for a specific date"""
        if not date:
            date = datetime.now().strftime('%d-%m-%Y')
            
        try:
            cause_list_url = f"{self.base_url}?p=causelist/index"
            data = {
                'state_code': state_code,
                'dist_code': dist_code,
                'court_code': court_code,
                'causelist_date': date,
                'action': 'causelist'
            }
            
            response = self.session.post(cause_list_url, data=data)
            return self._parse_cause_list(response.text, date)
        except Exception as e:
            return {"error": f"Failed to download cause list: {str(e)}"}

    def _parse_cause_list(self, html_content: str, date: str) -> List[Dict]:
        """Parse cause list HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        cause_list = []
        
        tables = soup.find_all('table', class_='table')
        for table in tables:
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    case_entry = {
                        'date': date,
                        'serial_number': cells[0].get_text(strip=True),
                        'case_number': cells[1].get_text(strip=True),
                        'parties': cells[2].get_text(strip=True),
                        'purpose': cells[3].get_text(strip=True),
                        'court_name': self._extract_court_name(table)
                    }
                    cause_list.append(case_entry)
        
        return cause_list

    def _extract_court_name(self, table_element) -> str:
        """Extract court name from table context"""
        # Look for court name in previous elements or table attributes
        prev_element = table_element.find_previous('h3') or table_element.find_previous('h4')
        if prev_element:
            return prev_element.get_text(strip=True)
        return "Unknown Court"

def save_to_json(data, filename: str):
    """Save data to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_to_text(data, filename: str):
    """Save data to text file"""
    with open(filename, 'w', encoding='utf-8') as f:
        if isinstance(data, list):
            for item in data:
                f.write(f"{json.dumps(item, ensure_ascii=False)}\n")
        else:
            f.write(json.dumps(data, ensure_ascii=False))

def print_case_info(case_info: Dict):
    """Print case information to console"""
    print("\n" + "="*50)
    print("CASE INFORMATION")
    print("="*50)
    
    if 'error' in case_info:
        print(f"Error: {case_info['error']}")
        return
    
    # Print basic info
    for key, value in case_info.items():
        if key not in ['hearing_dates', 'listed_today', 'listed_tomorrow', 'next_hearing']:
            print(f"{key.replace('_', ' ').title()}: {value}")
    
    # Print listing status
    if case_info.get('listed_today'):
        print("\n📅 STATUS: Listed TODAY")
        if case_info.get('next_hearing'):
            hearing = case_info['next_hearing']
            print(f"   Serial Number: {case_info.get('serial_number', 'N/A')}")
            print(f"   Court: {case_info.get('court_name', 'N/A')}")
            print(f"   Purpose: {hearing.get('purpose', 'N/A')}")
            print(f"   Stage: {hearing.get('stage', 'N/A')}")
    elif case_info.get('listed_tomorrow'):
        print("\n📅 STATUS: Listed TOMORROW")
        if case_info.get('next_hearing'):
            hearing = case_info['next_hearing']
            print(f"   Serial Number: {case_info.get('serial_number', 'N/A')}")
            print(f"   Court: {case_info.get('court_name', 'N/A')}")
            print(f"   Purpose: {hearing.get('purpose', 'N/A')}")
            print(f"   Stage: {hearing.get('stage', 'N/A')}")
    else:
        print("\n📅 STATUS: Not listed today or tomorrow")
        if case_info.get('next_hearing'):
            print(f"   Next Hearing: {case_info['next_hearing'].get('date', 'N/A')}")

def main():
    parser = argparse.ArgumentParser(description='eCourts Case Listing Fetcher')
    
    # Case search methods
    case_group = parser.add_argument_group('Case Search Options')
    case_group.add_argument('--cnr', help='Search by CNR number')
    case_group.add_argument('--case-type', help='Case type (e.g., CIVIL, CRIMINAL)')
    case_group.add_argument('--case-number', help='Case number')
    case_group.add_argument('--case-year', help='Case year')
    case_group.add_argument('--state-code', help='State code')
    case_group.add_argument('--dist-code', help='District code') 
    case_group.add_argument('--court-code', help='Court code')
    
    # Date options
    date_group = parser.add_argument_group('Date Options')
    date_group.add_argument('--today', action='store_true', help='Check today\'s listings')
    date_group.add_argument('--tomorrow', action='store_true', help='Check tomorrow\'s listings')
    date_group.add_argument('--causelist', action='store_true', help='Download entire cause list')
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--output', '-o', help='Output filename (without extension)')
    output_group.add_argument('--format', choices=['json', 'text'], default='json', help='Output format')
    
    args = parser.parse_args()
    
    scraper = ECourtsScraper()
    
    # Validate arguments
    if not any([args.cnr, args.case_type, args.causelist]):
        parser.error("Must specify either --cnr, --case-type with other case details, or --causelist")
    
    if args.case_type and not all([args.case_number, args.case_year, args.state_code, args.dist_code, args.court_code]):
        parser.error("When using --case-type, must also provide --case-number, --case-year, --state-code, --dist-code, --court-code")
    
    if args.causelist and not all([args.state_code, args.dist_code, args.court_code]):
        parser.error("When using --causelist, must provide --state-code, --dist-code, --court-code")
    
    try:
        # Case search by CNR
        if args.cnr:
            print(f"Searching for case with CNR: {args.cnr}")
            case_info = scraper.get_case_details_by_cnr(args.cnr)
            print_case_info(case_info)
            
            if args.output:
                filename = f"{args.output}.{args.format}"
                if args.format == 'json':
                    save_to_json(case_info, filename)
                else:
                    save_to_text(case_info, filename)
                print(f"\nResults saved to: {filename}")
        
        # Case search by case details
        elif args.case_type:
            print(f"Searching for case: {args.case_type}/{args.case_number}/{args.case_year}")
            case_info = scraper.get_case_details_by_number(
                args.case_type, args.case_number, args.case_year,
                args.state_code, args.dist_code, args.court_code
            )
            print_case_info(case_info)
            
            if args.output:
                filename = f"{args.output}.{args.format}"
                if args.format == 'json':
                    save_to_json(case_info, filename)
                else:
                    save_to_text(case_info, filename)
                print(f"\nResults saved to: {filename}")
        
        # Download cause list
        if args.causelist:
            date = None
            if args.today:
                date = datetime.now().strftime('%d-%m-%Y')
            elif args.tomorrow:
                date = (datetime.now() + timedelta(days=1)).strftime('%d-%m-%Y')
            
            print(f"Downloading cause list for date: {date or 'today'}")
            cause_list = scraper.download_cause_list(args.state_code, args.dist_code, args.court_code, date)
            
            if 'error' in cause_list:
                print(f"Error: {cause_list['error']}")
            else:
                print(f"Found {len(cause_list)} cases in cause list")
                for case in cause_list[:5]:  # Show first 5 cases
                    print(f"  {case.get('serial_number')}: {case.get('case_number')} - {case.get('purpose')}")
                if len(cause_list) > 5:
                    print(f"  ... and {len(cause_list) - 5} more cases")
                
                if args.output:
                    filename = f"{args.output}_causelist.{args.format}"
                    if args.format == 'json':
                        save_to_json(cause_list, filename)
                    else:
                        save_to_text(cause_list, filename)
                    print(f"\nCause list saved to: {filename}")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()