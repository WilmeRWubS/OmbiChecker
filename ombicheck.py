import requests
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox
import re
from datetime import datetime
import os
import webbrowser
import time
import sqlite3
import argparse
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse

# Your TMDb Bearer Token (still used for poster images and descriptions)
TMDB_BEARER_TOKEN = "enterhere"

# Configuration for HTML customization
USE_CUSTOM_BACKGROUND = "yes"  # "yes" or "no"
CUSTOM_BACKGROUND_URL = "https://i.imgur.com/9QY51tm.jpeg"  # URL to background image
HTML_LANGUAGE = "nl-NL"  # Language code for TMDb API (e.g., "en-US", "es-ES", "fr-FR", "de-DE")
OMBI_SITE_URL = ""  # Ombi site URL (e.g., "https://ombi.yourdomain.com")

HEADERS = {
    "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
    "accept": "application/json"
}

# Global variable to store movie results for sorting
movie_results = []

def setup_selenium_driver():
    """Setup Chrome driver for web scraping."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        messagebox.showerror("WebDriver Error", 
                           f"Failed to initialize Chrome WebDriver. Please ensure Chrome and ChromeDriver are installed.\n\nError: {str(e)}")
        return None

def connect_db(db_path="ombi.db"):
    return sqlite3.connect(db_path)

def get_pending_requests(conn):
    cursor = conn.cursor()

    # Haal gebruikers op
    cursor.execute("SELECT Id, UserName FROM AspNetUsers")
    user_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT Title, ReleaseDate, Status, RequestedDate, RequestedUserId, Approved, Available
        FROM MovieRequests
        WHERE Approved = 0 AND (Available = 0 OR Available IS NULL)
        ORDER BY ReleaseDate ASC
    """)

    output = []
    for title, release, status, req_date, user_id, approved, available in cursor.fetchall():
        username = user_map.get(user_id, "Onbekend")

        # Status vertaling
        status_nl = {
            "Released": "Uitgebracht",
            "Post Production": "Postproductie"
        }.get(status, status)

        # Format release
        if release and "0001" not in release:
            try:
                release_fmt = datetime.strptime(release.split(" ")[0], "%Y-%m-%d").strftime("(%m/%d/%Y)")
            except:
                release_fmt = "(?)"
        else:
            release_fmt = "(?)"

        # Format aanvraagdatum
        if req_date and "0001" not in req_date:
            try:
                req_fmt = datetime.strptime(req_date.split(" ")[0], "%Y-%m-%d").strftime("%b %d, %Y")
            except:
                req_fmt = "-"
        else:
            req_fmt = "-"

        output.append(f"{title} {release_fmt}\t{username}\t{status_nl}\tWacht op goedkeuring\t{req_fmt}")

    return output

def standardize_date(date_str):
    """Convert various date formats to YYYY-MM-DD format with improved parsing."""
    if not date_str:
        return None
        
    try:
        date_str = date_str.strip()
        
        # Handle "Jul 24, 2025" format
        if re.match(r'[A-Za-z]{3}\s+\d{1,2},\s+\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%b %d, %Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "July 24, 2025" format (full month name)
        elif re.match(r'[A-Za-z]+\s+\d{1,2},\s+\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%B %d, %Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "Jul 24 2025" format (no comma)
        elif re.match(r'[A-Za-z]{3}\s+\d{1,2}\s+\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%b %d %Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "24 Jul 2025" format (day first)
        elif re.match(r'\d{1,2}\s+[A-Za-z]{3}\s+\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%d %b %Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "1/15/2025" format
        elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%m/%d/%Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "15/1/2025" format (day/month/year - European style)
        elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            # Try both formats and see which makes more sense
            try:
                # Try MM/DD/YYYY first
                date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # If that fails, try DD/MM/YYYY
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                return date_obj.strftime("%Y-%m-%d")
        
        # Handle "2025-01-15" format (already standard)
        elif re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "15-01-2025" format (DD-MM-YYYY)
        elif re.match(r'\d{1,2}-\d{1,2}-\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%d-%m-%Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "Jan 2025" format (month and year only - assume 1st day)
        elif re.match(r'[A-Za-z]{3}\s+\d{4}', date_str):
            date_obj = datetime.strptime(f"01 {date_str}", "%d %b %Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "January 2025" format (full month name and year only)
        elif re.match(r'[A-Za-z]+\s+\d{4}', date_str):
            date_obj = datetime.strptime(f"01 {date_str}", "%d %B %Y")
            return date_obj.strftime("%Y-%m-%d")
        
        # Handle "2025" format (year only - assume January 1st)
        elif re.match(r'^\d{4}$', date_str):
            return f"{date_str}-01-01"
        
        return None
        
    except Exception as e:
        print(f"Error parsing date '{date_str}': {str(e)}")
        return None

def search_movie_vuniper(title, driver, custom_dates=None, expected_year=None):
    """Search for a movie on Vuniper.com and get release information with improved search and year matching."""
    try:
        driver.get("https://vuniper.com")
        time.sleep(2)
        
        # Load custom digital dates first
        if not custom_dates:
            custom_dates = load_custom_digital_dates()
        
        # Extract year from title if present and not provided separately
        title_year = None
        clean_title = title
        
        # Check if title contains a year in parentheses like "Movie Title (2025)"
        year_match = re.search(r'\((\d{4})\)', title)
        if year_match:
            title_year = int(year_match.group(1))
            clean_title = re.sub(r'\s*\(\d{4}\)', '', title).strip()
        
        # Use expected_year if provided, otherwise use extracted year
        target_year = expected_year or title_year
        
        # Create comprehensive search variations
        search_variations = []
        
        # Use clean title for variations
        base_title = clean_title
        
        # Original title variations
        search_variations.extend([
            base_title,  # Original title
            base_title.replace(":", ""),  # Remove colons
            base_title.replace(":", " "),  # Replace colons with spaces
        ])
        
        # Handle subtitle variations (before colon)
        if ":" in base_title:
            main_title = base_title.split(":")[0].strip()
            search_variations.append(main_title)
        
        # Handle "The" prefix variations
        if base_title.startswith("The "):
            search_variations.append(base_title.replace("The ", "").strip())
        else:
            search_variations.append(f"The {base_title}")
        
        # Handle "Movie" suffix variations
        if " Movie" in base_title:
            search_variations.append(base_title.replace(" Movie", "").strip())
            search_variations.append(base_title.replace(" The Movie", "").strip())
        
        # Individual word search for difficult cases
        words = base_title.split()
        # Filter out common words that don't help with search
        skip_words = {'the', 'a', 'an', 'and', 'or', 'but', 'movie', 'film'}
        important_words = [word for word in words if word.lower() not in skip_words and len(word) > 2]
        
        if important_words:
            # Try combinations of important words
            if len(important_words) >= 2:
                search_variations.append(f"{important_words[0]} {important_words[1]}")
            
            # Try just the first important word
            search_variations.append(important_words[0])
        
        # Remove duplicates while preserving order
        search_variations = list(dict.fromkeys(search_variations))
        
        print(f"Search variations for '{title}' (target year: {target_year}): {search_variations}")
        
        vuniper_info = None
        vuniper_url = None
        
        for search_term in search_variations:
            try:
                print(f"Trying search term: '{search_term}'")
                
                # Find and use search input
                search_input = driver.find_element(By.ID, "search-input")
                search_input.clear()
                search_input.send_keys(search_term)
                time.sleep(3)  # Give time for suggestions to load
                
                # Try to find suggestions
                suggestions = driver.find_elements(By.CSS_SELECTOR, ".search-suggestion")
                
                if suggestions:
                    # Look for the best match with year consideration
                    best_suggestion = None
                    best_score = -1
                    
                    for suggestion in suggestions:
                        suggestion_text = suggestion.text.strip()
                        print(f"Evaluating suggestion: '{suggestion_text}'")
                        
                        # Extract year from suggestion text
                        suggestion_year = None
                        year_match = re.search(r'(\d{4})', suggestion_text)
                        if year_match:
                            suggestion_year = int(year_match.group(1))
                        
                        # Calculate match score
                        score = 0
                        suggestion_lower = suggestion_text.lower()
                        
                        # Check if this is a "no results" message
                        if any(phrase in suggestion_lower for phrase in ['no results', 'searched movies', 'view results']):
                            print(f"Skipping 'no results' suggestion: {suggestion_text}")
                            continue
                        
                        # Year matching (highest priority)
                        if target_year and suggestion_year:
                            if suggestion_year == target_year:
                                score += 1000  # Exact year match gets highest priority
                                print(f"Exact year match: {suggestion_year}")
                            elif abs(suggestion_year - target_year) <= 1:
                                score += 500  # Close year match
                                print(f"Close year match: {suggestion_year} vs {target_year}")
                            else:
                                score -= 200  # Wrong year penalty
                                print(f"Year mismatch: {suggestion_year} vs {target_year}")
                        elif not target_year and suggestion_year:
                            # If no target year, prefer older movies (likely the original)
                            if suggestion_year < 2020:
                                score += 100
                        
                        # Title matching
                        if important_words:
                            word_matches = sum(1 for word in important_words if word.lower() in suggestion_lower)
                            score += word_matches * 50
                            print(f"Word matches: {word_matches}/{len(important_words)}")
                        
                        # Exact title match bonus
                        clean_suggestion = re.sub(r'\s*\d{4}', '', suggestion_text).strip().lower()
                        if clean_suggestion == base_title.lower():
                            score += 200
                            print(f"Exact title match bonus")
                        
                        print(f"Suggestion '{suggestion_text}' scored: {score}")
                        
                        if score > best_score:
                            best_score = score
                            best_suggestion = suggestion
                    
                    if best_suggestion:
                        print(f"Selected best suggestion: '{best_suggestion.text}' (score: {best_score})")
                        
                        best_suggestion.click()
                        time.sleep(4)  # Give time for page to load
                        
                        # Capture the current URL after clicking
                        vuniper_url = driver.current_url
                        print(f"Vuniper URL found: {vuniper_url}")
                        
                        # Try to extract release info
                        vuniper_info = extract_vuniper_release_info(driver)
                        
                        if vuniper_info and (vuniper_info.get('theater_date') or vuniper_info.get('digital_date')):
                            print(f"Successfully found release info for '{search_term}': {vuniper_info}")
                            break  # Found valid info, stop searching
                        else:
                            print(f"No release info found for '{search_term}', trying next variation")
                            # Go back to search for next variation
                            driver.get("https://vuniper.com")
                            time.sleep(2)
                            vuniper_url = None  # Reset URL if no valid info found
                else:
                    print(f"No suggestions found for '{search_term}'")
                    
            except Exception as e:
                print(f"Error with search term '{search_term}': {str(e)}")
                # Try to go back to main page for next attempt
                try:
                    driver.get("https://vuniper.com")
                    time.sleep(2)
                except:
                    pass
                continue
        
        # If no digital date from Vuniper, check custom dates file
        if vuniper_info and not vuniper_info.get('digital_date') and custom_dates:
            # Try to match against custom dates with flexible matching
            title_lower = base_title.lower()
            matched_custom_date = None
            
            # Create title variations for matching
            title_variations = [
                title_lower,
                title_lower.replace(":", ""),  # Remove colons
                title_lower.replace(":", " "),  # Replace colons with spaces
            ]
            
            # Handle "The" prefix
            if title_lower.startswith("the "):
                title_variations.append(title_lower.replace("the ", "").strip())
            else:
                title_variations.append(f"the {title_lower}")
            
            # Try exact matches first
            for variation in title_variations:
                if variation in custom_dates:
                    matched_custom_date = custom_dates[variation]
                    print(f"Exact match found: '{variation}' = {matched_custom_date}")
                    break
            
            # If no exact match, try partial matching
            if not matched_custom_date:
                for custom_title, custom_date in custom_dates.items():
                    for variation in title_variations:
                        # Check if titles are similar (contains each other)
                        if (custom_title in variation or variation in custom_title):
                            matched_custom_date = custom_date
                            print(f"Partial match found: '{custom_title}' -> '{variation}' = {matched_custom_date}")
                            break
                    if matched_custom_date:
                        break
            
            if matched_custom_date:
                vuniper_info['digital_date'] = matched_custom_date
                print(f"Using custom digital date for '{title}': {matched_custom_date}")
                
                # Update status based on custom digital date
                current_date = datetime.now()
                try:
                    digital_obj = datetime.strptime(matched_custom_date, "%Y-%m-%d")
                    vuniper_info['status'] = 'Yes' if digital_obj <= current_date else 'Soon'
                except:
                    vuniper_info['status'] = 'Soon'
        
        # If still no info found, try custom dates as fallback
        if not vuniper_info and custom_dates:
            title_lower = base_title.lower()
            matched_custom_date = None
            
            # Try exact match first
            if title_lower in custom_dates:
                matched_custom_date = custom_dates[title_lower]
            else:
                # Try partial matching with important words
                if important_words:
                    for custom_title, custom_date in custom_dates.items():
                        # Check if any important words match
                        if any(word.lower() in custom_title for word in important_words):
                            matched_custom_date = custom_date
                            print(f"Matched custom date by keywords: '{custom_title}' -> '{title}' = {custom_date}")
                            break
            
            if matched_custom_date:
                current_date = datetime.now()
                try:
                    digital_obj = datetime.strptime(matched_custom_date, "%Y-%m-%d")
                    status = 'Yes' if digital_obj <= current_date else 'Soon'
                except:
                    status = 'Soon'
                
                vuniper_info = {
                    'theater_date': None,
                    'digital_date': matched_custom_date,
                    'status': status
                }
                print(f"Using custom date as primary source for '{title}': {matched_custom_date}")
        
        # Add the Vuniper URL to the result if we found valid info
        if vuniper_info and vuniper_url:
            vuniper_info['vuniper_url'] = vuniper_url
        
        return vuniper_info
        
    except Exception as e:
        print(f"Error searching Vuniper for '{title}': {str(e)}")
        return None
    
def load_custom_digital_dates():
    """Load custom digital release dates from a text file."""
    custom_dates = {}
    try:
        # Look for digital_dates.txt in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dates_file = os.path.join(script_dir, "digital_dates.txt")
        
        if os.path.exists(dates_file):
            with open(dates_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):  # Skip empty lines and comments
                        continue
                    
                    # Parse format: "Movie Title MONTH DAY" or "Movie Title DAY MONTH" or with year
                    # Examples: "F1 August 26", "28 Years Later 30 july", "Superman August 26, 2025"
                    
                    # Handle comma-separated year first
                    if ',' in line:
                        # Format: "Movie Title Month Day, Year"
                        parts_before_comma = line.split(',')[0].strip().split()
                        year_part = line.split(',')[1].strip()
                        
                        if len(parts_before_comma) >= 3:
                            title = ' '.join(parts_before_comma[:-2]).strip()
                            month_str = parts_before_comma[-2]
                            day_str = parts_before_comma[-1]
                            year_str = year_part
                        else:
                            print(f"Warning: Invalid format on line {line_num}: {line}")
                            continue
                    else:
                        # Format without comma
                        parts = line.split()
                        if len(parts) >= 3:
                            # Check if last part is a year (4 digits)
                            if len(parts) >= 4 and parts[-1].isdigit() and len(parts[-1]) == 4:
                                # Format: "Movie Title Month Day Year"
                                title = ' '.join(parts[:-3]).strip()
                                month_str = parts[-3]
                                day_str = parts[-2]
                                year_str = parts[-1]
                            else:
                                # Check if it's "DAY MONTH" format (day first)
                                if parts[-2].isdigit():
                                    # Format: "Movie Title DAY MONTH" (assume 2025)
                                    title = ' '.join(parts[:-2]).strip()
                                    day_str = parts[-2]
                                    month_str = parts[-1]
                                    year_str = "2025"
                                else:
                                    # Format: "Movie Title MONTH DAY" (assume 2025)
                                    title = ' '.join(parts[:-2]).strip()
                                    month_str = parts[-2]
                                    day_str = parts[-1]
                                    year_str = "2025"
                        else:
                            print(f"Warning: Invalid format on line {line_num}: {line}")
                            continue
                    
                    # Convert month name to number
                    month_map = {
                        'january': '01', 'february': '02', 'march': '03', 'april': '04',
                        'may': '05', 'june': '06', 'july': '07', 'august': '08',
                        'september': '09', 'october': '10', 'november': '11', 'december': '12',
                        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                    }
                    
                    month_num = month_map.get(month_str.lower())
                    if month_num and day_str.isdigit():
                        # Format as YYYY-MM-DD
                        formatted_date = f"{year_str}-{month_num}-{day_str.zfill(2)}"
                        
                        # Store multiple variations of the title for better matching
                        title_variations = [
                            title.lower(),
                            title.lower().replace(":", ""),  # Remove colons
                            title.lower().replace(":", " "),  # Replace colons with spaces
                        ]
                        
                        # Handle "The" prefix variations
                        if title.lower().startswith("the "):
                            title_variations.append(title.lower().replace("the ", "").strip())
                        else:
                            title_variations.append(f"the {title.lower()}")
                        
                        # Store all variations
                        for variation in title_variations:
                            custom_dates[variation] = formatted_date
                        
                        print(f"Loaded custom date: '{title}' -> {formatted_date}")
                    else:
                        print(f"Warning: Could not parse date on line {line_num}: {line}")
        else:
            print("No digital_dates.txt file found. Create one in the same directory as this script.")
            print("Format examples:")
            print("'Movie Title Month Day' -> 'F1 August 26'")
            print("'Movie Title Day Month' -> '28 Years Later 30 july'")
            print("'Movie Title Month Day, Year' -> 'Superman August 26, 2025'")
    
    except Exception as e:
        print(f"Error loading custom digital dates: {str(e)}")
    
    return custom_dates

def extract_vuniper_release_info(driver):
    """Extract release information from Vuniper movie page with improved detection."""
    try:
        release_info = {'theater_date': None, 'digital_date': None, 'status': 'TBD'}
        
        # Wait a bit for page to fully load
        time.sleep(2)
        
        # Try multiple selectors for theater release date
        theater_selectors = [
            "//span[contains(text(), 'Theaters')]/preceding-sibling::span[@class='semibold']",
            "//span[contains(text(), 'Theater')]/preceding-sibling::span[@class='semibold']",
            "//span[contains(text(), 'Cinema')]/preceding-sibling::span[@class='semibold']",
            "//img[@alt='Icon of cinema film']/../..//span[@class='semibold']",
            "//div[contains(@class, 'media-viewer-line')]//span[@class='semibold'][contains(text(), '2025')]",
        ]
        
        for selector in theater_selectors:
            try:
                theater_element = driver.find_element(By.XPATH, selector)
                theater_date_text = theater_element.text.strip()
                theater_date = standardize_date(theater_date_text)
                if theater_date:
                    release_info['theater_date'] = theater_date
                    print(f"Found theater date: {theater_date_text} -> {theater_date}")
                    break
            except:
                continue
        
        # Try multiple selectors for streaming/digital release date
        streaming_selectors = [
            "//span[contains(text(), 'Streaming')]/preceding-sibling::span[@class='semibold']",
            "//span[contains(text(), 'Digital')]/preceding-sibling::span[@class='semibold']",
            "//span[contains(text(), 'VOD')]/preceding-sibling::span[@class='semibold']",
            "//span[text()='Digital release date']/preceding-sibling::span[@class='semibold']",
            "//img[@alt='Streaming icon']/../..//span[@class='semibold']",
        ]
        
        for selector in streaming_selectors:
            try:
                streaming_element = driver.find_element(By.XPATH, selector)
                streaming_date_text = streaming_element.text.strip()
                streaming_date = standardize_date(streaming_date_text)
                if streaming_date:
                    release_info['digital_date'] = streaming_date
                    print(f"Found digital date: {streaming_date_text} -> {streaming_date}")
                    break
            except:
                continue
        
        # If no specific streaming date found, look for any additional dates on the page
        if not release_info['digital_date']:
            try:
                # Look for all semibold spans that might contain dates
                all_date_elements = driver.find_elements(By.XPATH, "//span[@class='semibold']")
                for element in all_date_elements:
                    date_text = element.text.strip()
                    standardized = standardize_date(date_text)
                    if standardized and standardized != release_info['theater_date']:
                        # This might be a digital release date
                        release_info['digital_date'] = standardized
                        print(f"Found potential digital date: {date_text} -> {standardized}")
                        break
            except:
                pass
        
        # Determine status based on available dates
        current_date = datetime.now()
        
        if release_info['digital_date']:
            try:
                digital_obj = datetime.strptime(release_info['digital_date'], "%Y-%m-%d")
                release_info['status'] = 'Yes' if digital_obj <= current_date else 'Soon'
            except:
                release_info['status'] = 'Soon'
        elif release_info['theater_date']:
            try:
                theater_obj = datetime.strptime(release_info['theater_date'], "%Y-%m-%d")
                # If theater date is in the past but no digital date, it might be available
                if theater_obj <= current_date:
                    release_info['status'] = 'No'  # Theater only, but released
                else:
                    release_info['status'] = 'No'  # Theater only, not yet released
            except:
                release_info['status'] = 'No'
        else:
            release_info['status'] = 'TBD'
        
        print(f"Final release info: {release_info}")
        return release_info
        
    except Exception as e:
        print(f"Error extracting release info: {str(e)}")
        return None

def extract_date_from_text(text):
    """Extract date from text in various formats."""
    # Look for patterns like "Jul 15, 2025", "Jun 26, 2025", etc.
    date_patterns = [
        r'([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})',  # Jul 15, 2025
        r'(\d{1,2})/(\d{1,2})/(\d{4})',           # 7/15/2025
        r'(\d{4})-(\d{1,2})-(\d{1,2})',           # 2025-07-15
    ]
    
    month_map = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if pattern == date_patterns[0]:  # Month name format
                month_name = match.group(1).lower()
                day = match.group(2).zfill(2)
                year = match.group(3)
                month = month_map.get(month_name[:3])
                if month:
                    return f"{year}-{month}-{day}"
            elif pattern == date_patterns[1]:  # MM/DD/YYYY
                month = match.group(1).zfill(2)
                day = match.group(2).zfill(2)
                year = match.group(3)
                return f"{year}-{month}-{day}"
            elif pattern == date_patterns[2]:  # YYYY-MM-DD
                return match.group(0)
    
    return None

def search_movie_tmdb(title):
    """Search for movie on TMDb to get poster and description."""
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "query": title,
        "language": HTML_LANGUAGE
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        data = response.json()
        if data.get("results"):
            return data["results"][0]
    except Exception as e:
        print(f"TMDb search error for '{title}': {str(e)}")
    return None

def determine_downloadable_status(release_info, theater_date=None, digital_date=None):
    """Determine downloadable status based on release info with improved logic for older movies."""
    current_date = datetime.now()
    
    # If we have explicit status from Vuniper, use it (unless overridden by old theater date)
    if release_info and release_info.get('status'):
        status = release_info.get('status')
        
        # Override status for old theater releases
        if theater_date and theater_date != "TBD":
            try:
                theater_obj = datetime.strptime(theater_date, "%Y-%m-%d")
                # If theater release was more than 4 months ago, assume it's available
                months_since_theater = (current_date - theater_obj).days / 30.44  # Average days per month
                if months_since_theater >= 4:
                    print(f"Theater release was {months_since_theater:.1f} months ago, marking as available")
                    return "Yes"
            except ValueError:
                pass
        
        return status
    
    # Fallback logic when no Vuniper info
    if theater_date and theater_date != "TBD":
        try:
            theater_obj = datetime.strptime(theater_date, "%Y-%m-%d")
            months_since_theater = (current_date - theater_obj).days / 30.44
            
            # If theater release was more than 4 months ago, assume available
            if months_since_theater >= 4:
                return "Yes"
            # If theater release was 2-4 months ago, probably coming soon
            elif months_since_theater >= 2:
                return "Soon"
            # If very recent theater release, probably not available yet
            else:
                return "No"
        except ValueError:
            pass
    
    # Check digital date if available
    if digital_date and digital_date != "TBD":
        try:
            digital_obj = datetime.strptime(digital_date, "%Y-%m-%d")
            return "Yes" if digital_obj <= current_date else "Soon"
        except ValueError:
            pass
    
    return "TBD"

def extract_title(line):
    """Extract clean movie title from input line."""
    # Match until the first ( (e.g., "Movie Title (07/01/2025)")
    match = re.match(r"^(.*?)\s*\(", line)
    if match:
        return match.group(1).strip()
    
    # Fallback: take the first tab-split section
    return line.split('\t')[0].strip()

def display_results(results):
    """Display the results in the output text widget with both theatrical and digital dates."""
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    
    output_text.insert(tk.END, f"{'Title':<40} | {'Theater Date':<12} | {'Digital Date':<12} | {'Status':<12}\n")
    output_text.insert(tk.END, "-" * 85 + "\n")
    
    for result in results:
        theater_date = result.get('theater_date', 'TBD') or 'TBD'
        digital_date = result.get('digital_date', 'TBD') or 'TBD'
        
        output_text.insert(tk.END, f"{result['title']:<40} | {theater_date:<12} | {digital_date:<12} | {result['status']:<12}\n")
    
    output_text.config(state=tk.DISABLED)

def sort_results():
    """Sort the results based on the selected criteria."""
    if not movie_results:
        return
    
    sort_by = sort_var.get()
    
    if sort_by == "Title":
        sorted_results = sorted(movie_results, key=lambda x: x['title'].lower())
    elif sort_by == "Theater Date":
        def date_sort_key(x):
            date = x.get('theater_date', 'TBD')
            if date == "TBD" or date == "-":
                return "9999-12-31"
            return date
        sorted_results = sorted(movie_results, key=date_sort_key)
    elif sort_by == "Digital Date":
        def date_sort_key(x):
            date = x.get('digital_date', 'TBD')
            if date == "TBD" or date == "-":
                return "9999-12-31"
            return date
        sorted_results = sorted(movie_results, key=date_sort_key)
    elif sort_by == "Downloadable":
        status_order = {"Yes": 1, "Soon": 2, "TBD": 3, "No": 4}
        sorted_results = sorted(movie_results, key=lambda x: status_order.get(x['status'], 5))
    else:
        sorted_results = movie_results
    
    display_results(sorted_results)

def load_from_ombi_db():
    try:
        conn = connect_db()
        pending_lines = get_pending_requests(conn)
        conn.close()
    except Exception as e:
        messagebox.showerror("Databasefout", f"Kan Ombi-database niet openen of lezen:\n{str(e)}")
        return

    if not pending_lines:
        messagebox.showinfo("Geen verzoeken", "Er zijn geen openstaande filmverzoeken in Ombi.")
    else:
        input_text.delete("1.0", tk.END)
        input_text.insert(tk.END, "\n".join(pending_lines))

def check_movies():
    global movie_results
    movie_results = []
    
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, "Initializing web browser...\n")
    output_text.config(state=tk.DISABLED)
    output_text.update()
    
    # Setup Selenium driver
    driver = setup_selenium_driver()
    if not driver:
        return
    
    try:
        lines = input_text.get("1.0", tk.END).strip().split('\n')
        
        if not lines:
            output_text.config(state=tk.NORMAL)
            output_text.insert(tk.END, "Please paste some movie data.\n")
            output_text.config(state=tk.DISABLED)
            return
        
        total_movies = len([line for line in lines if extract_title(line)])
        current_movie = 0
        
        for line in lines:
            title = extract_title(line)
            if not title:
                continue
            
            current_movie += 1
            
            # Extract year from the original line if available
            expected_year = None
            
            # Look for year in parentheses in the title
            year_match = re.search(r'\((\d{4})\)', title)
            if year_match:
                expected_year = int(year_match.group(1))
            else:
                # Look for year in the full line (e.g., release date info)
                year_match = re.search(r'(\d{4})', line)
                if year_match:
                    potential_year = int(year_match.group(1))
                    # Only use if it's a reasonable movie year (1900-2030)
                    if 1900 <= potential_year <= 2030:
                        expected_year = potential_year
            
            # Update progress with year info if available
            year_info = f" ({expected_year})" if expected_year else ""
            output_text.config(state=tk.NORMAL)
            output_text.delete("1.0", tk.END)
            output_text.insert(tk.END, f"Processing movie {current_movie}/{total_movies}: {title}{year_info}\n")
            output_text.config(state=tk.DISABLED)
            output_text.update()
            
            # Search Vuniper for release info with year information
            vuniper_info = search_movie_vuniper(title, driver, expected_year=expected_year)
            
            # Search TMDb for poster and description
            tmdb_data = search_movie_tmdb(title)
            
            # If TMDb found a different year, log it for debugging
            if tmdb_data and expected_year:
                tmdb_year = tmdb_data.get('release_date', '')[:4] if tmdb_data.get('release_date') else None
                if tmdb_year and tmdb_year.isdigit():
                    tmdb_year = int(tmdb_year)
                    if tmdb_year != expected_year:
                        print(f"Year mismatch for '{title}': Expected {expected_year}, TMDb found {tmdb_year}")
            
            # Prepare movie result with separate theater and digital dates
            theater_date = "TBD"
            digital_date = "TBD"
            status = "TBD"
            vuniper_url = None
            
            if vuniper_info:
                theater_date = vuniper_info.get('theater_date') or "TBD"
                digital_date = vuniper_info.get('digital_date') or "TBD"
                vuniper_url = vuniper_info.get('vuniper_url')
            
            # Use improved status determination
            status = determine_downloadable_status(vuniper_info, theater_date, digital_date)
            
            poster_url = ''
            overview = 'No description available.'
            movie_id = None
            
            if tmdb_data:
                poster_path = tmdb_data.get('poster_path', '')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
                overview = tmdb_data.get('overview', 'No description available.')
                movie_id = tmdb_data.get('id')
            
            movie_results.append({
                'title': title,
                'theater_date': theater_date,
                'digital_date': digital_date,
                'status': status,
                'poster_url': poster_url,
                'overview': overview,
                'movie_id': movie_id,
                'vuniper_url': vuniper_url,
                'expected_year': expected_year
            })
            
            # Add delay between requests to be respectful
            time.sleep(2)
        
        display_results(movie_results)
        
    finally:
        driver.quit()

def open_settings_window():
    """Open a settings window for HTML customization."""
    global USE_CUSTOM_BACKGROUND, CUSTOM_BACKGROUND_URL, HTML_LANGUAGE, OMBI_SITE_URL, TMDB_BEARER_TOKEN, HEADERS
    
    settings_window = tk.Toplevel(window)
    settings_window.title("HTML Report Settings")
    settings_window.geometry("580x520")
    settings_window.resizable(False, False)
    
    # Make window modal
    settings_window.transient(window)
    settings_window.grab_set()
    
    # Center the window
    settings_window.update_idletasks()
    x = (settings_window.winfo_screenwidth() // 2) - (580 // 2)
    y = (settings_window.winfo_screenheight() // 2) - (520 // 2)
    settings_window.geometry(f"580x520+{x}+{y}")
    
    # Create main frame with scrollbar if needed
    main_frame = tk.Frame(settings_window)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # TMDb API Section
    tmdb_frame = tk.LabelFrame(main_frame, text="TMDb API Configuration", padx=10, pady=10)
    tmdb_frame.pack(fill="x", pady=(0, 10))
    
    # Configure grid weights for proper expansion
    tmdb_frame.grid_columnconfigure(1, weight=1)
    
    tk.Label(tmdb_frame, text="TMDb Bearer Token:").grid(row=0, column=0, sticky="w", pady=5)
    tmdb_token_var = tk.StringVar(value=TMDB_BEARER_TOKEN)
    tmdb_token_entry = tk.Entry(tmdb_frame, textvariable=tmdb_token_var, width=40, show="*")
    tmdb_token_entry.grid(row=0, column=1, sticky="ew", padx=(10, 5), pady=5)
    
    # Show/Hide token button
    def toggle_token_visibility():
        if tmdb_token_entry.cget('show') == '*':
            tmdb_token_entry.config(show='')
            show_token_btn.config(text="👁️‍🗨️ Hide")
        else:
            tmdb_token_entry.config(show='*')
            show_token_btn.config(text="👁️ Show")
    
    show_token_btn = tk.Button(tmdb_frame, text="👁️ Show", command=toggle_token_visibility, 
                              font=("Arial", 8), padx=5, pady=2)
    show_token_btn.grid(row=0, column=2, padx=(5, 5), pady=5)
    
    # Get Token button - opens TMDb API page in user's default browser
    def open_tmdb_api_page():
        try:
            webbrowser.open("https://www.themoviedb.org/settings/api")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open browser: {str(e)}")
    
    get_token_btn = tk.Button(tmdb_frame, text="🌐 Get Token", command=open_tmdb_api_page,
                             bg="#01b4e4", fg="white", font=("Arial", 8, "bold"), 
                             padx=8, pady=2)
    get_token_btn.grid(row=0, column=3, padx=(5, 0), pady=5)
    
    tk.Label(tmdb_frame, text="(Click 'Get Token' to open TMDb API settings in your browser)", 
             font=("Arial", 8), fg="gray").grid(row=1, column=1, columnspan=3, sticky="w", padx=(10, 0))
    
    # Ombi Site Section
    ombi_frame = tk.LabelFrame(main_frame, text="Ombi Integration", padx=10, pady=10)
    ombi_frame.pack(fill="x", pady=(0, 10))
    
    # Configure grid weights for proper expansion
    ombi_frame.grid_columnconfigure(1, weight=1)
    
    tk.Label(ombi_frame, text="Ombi Site URL:").grid(row=0, column=0, sticky="w", pady=5)
    ombi_url_var = tk.StringVar(value=OMBI_SITE_URL)
    ombi_url_entry = tk.Entry(ombi_frame, textvariable=ombi_url_var, width=50)
    ombi_url_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=5)
    
    tk.Label(ombi_frame, text="(e.g., https://ombi.yourdomain.com - leave empty to disable links)", 
             font=("Arial", 8), fg="gray").grid(row=1, column=1, columnspan=3, sticky="w", padx=(10, 0))
    
    # Custom Background Section
    bg_frame = tk.LabelFrame(main_frame, text="Custom Background", padx=10, pady=10)
    bg_frame.pack(fill="x", pady=(0, 10))
    
    # Configure grid weights for proper expansion
    bg_frame.grid_columnconfigure(1, weight=1)
    
    use_bg_var = tk.StringVar(value=USE_CUSTOM_BACKGROUND)
    tk.Label(bg_frame, text="Use Custom Background:").grid(row=0, column=0, sticky="w", pady=5)
    bg_combo = ttk.Combobox(bg_frame, textvariable=use_bg_var, values=["no", "yes"], 
                           state="readonly", width=10)
    bg_combo.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
    
    tk.Label(bg_frame, text="Background Image URL:").grid(row=1, column=0, sticky="w", pady=5)
    bg_url_var = tk.StringVar(value=CUSTOM_BACKGROUND_URL)
    bg_url_entry = tk.Entry(bg_frame, textvariable=bg_url_var, width=50)
    bg_url_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=5)
    
    tk.Label(bg_frame, text="(Must be a direct link to an image file)", 
             font=("Arial", 8), fg="gray").grid(row=2, column=1, columnspan=3, sticky="w", padx=(10, 0))
    
    # Language Section
    lang_frame = tk.LabelFrame(main_frame, text="Language Settings", padx=10, pady=10)
    lang_frame.pack(fill="x", pady=(0, 10))
    
    # Configure grid weights for proper expansion
    lang_frame.grid_columnconfigure(1, weight=1)
    
    tk.Label(lang_frame, text="TMDb Language:").grid(row=0, column=0, sticky="w", pady=5)
    lang_var = tk.StringVar(value=HTML_LANGUAGE)
    lang_combo = ttk.Combobox(lang_frame, textvariable=lang_var, width=15,
                             values=["en-US", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", 
                                   "ja-JP", "ko-KR", "zh-CN", "ru-RU", "nl-NL", "sv-SE"])
    lang_combo.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
    
    tk.Label(lang_frame, text="(Affects movie descriptions and some metadata)", 
             font=("Arial", 8), fg="gray").grid(row=1, column=1, sticky="w", padx=(10, 0))
    
    # Buttons Frame - Fixed at bottom
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill="x", pady=(20, 0))
    
    def save_settings():
        global USE_CUSTOM_BACKGROUND, CUSTOM_BACKGROUND_URL, HTML_LANGUAGE, OMBI_SITE_URL, TMDB_BEARER_TOKEN, HEADERS
        
        # Validate TMDb token
        new_token = tmdb_token_var.get().strip()
        if not new_token:
            messagebox.showerror("Error", "TMDb Bearer Token is required!")
            return
        
        # Update global variables
        USE_CUSTOM_BACKGROUND = use_bg_var.get()
        CUSTOM_BACKGROUND_URL = bg_url_var.get()
        HTML_LANGUAGE = lang_var.get()
        OMBI_SITE_URL = ombi_url_var.get().rstrip('/')  # Remove trailing slash
        TMDB_BEARER_TOKEN = new_token
        
        # Update headers with new token
        HEADERS = {
            "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
            "accept": "application/json"
        }
        
        messagebox.showinfo("Settings Saved", "Settings have been saved successfully!")
        settings_window.destroy()
    
    def cancel_settings():
        settings_window.destroy()
    
    # Make buttons more prominent
    save_btn = tk.Button(button_frame, text="💾 Save Settings", command=save_settings, 
                        bg="#28a745", fg="white", font=("Arial", 10, "bold"), 
                        padx=20, pady=8)
    save_btn.pack(side=tk.RIGHT, padx=(10, 0))
    
    cancel_btn = tk.Button(button_frame, text="❌ Cancel", command=cancel_settings,
                          bg="#6c757d", fg="white", font=("Arial", 10, "bold"),
                          padx=20, pady=8)
    cancel_btn.pack(side=tk.RIGHT)

def generate_html_report():
    """Generate an HTML report with movie posters and download status."""
    if not movie_results:
        messagebox.showwarning("No Data", "Please check movies first before generating HTML report.")
        return
    
    # Ask user where to save the HTML file
    file_path = filedialog.asksaveasfilename(
        defaultextension=".html",
        filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
        title="Save HTML Report As"
    )
    
    if not file_path:
        return
    
    # Generate HTML content
    html_content = generate_html_content()
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        messagebox.showinfo("Success", f"HTML report saved to:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save HTML report:\n{str(e)}")

def generate_html_content():
    """Generate the HTML content for the movie report."""
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Calculate statistics
    total_movies = len(movie_results)
    available_count = len([m for m in movie_results if m['status'] == 'Yes'])
    soon_count = len([m for m in movie_results if m['status'] == 'Soon'])
    unavailable_count = len([m for m in movie_results if m['status'] in ['No', 'TBD']])
    
    # Determine background style
    if USE_CUSTOM_BACKGROUND.lower() == "yes" and CUSTOM_BACKGROUND_URL:
        background_style = f"""
            background: url('{CUSTOM_BACKGROUND_URL}') center center fixed;
            background-size: cover;
        """
        # Add overlay for better readability
        overlay_style = """
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.3);
            z-index: -1;
        }
        """
    else:
        background_style = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
        overlay_style = ""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movie Download Status Report</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            {background_style}
            min-height: 100vh;
        }}
        {overlay_style}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
            position: relative;
            z-index: 1;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.8;
            font-size: 1.1em;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        .stat {{
            text-align: center;
            cursor: pointer;
            padding: 10px;
            border-radius: 8px;
            transition: all 0.3s ease;
            user-select: none;
        }}
        .stat:hover {{
            background: rgba(0,0,0,0.05);
            transform: translateY(-2px);
        }}
        .stat.active {{
            background: rgba(0,123,255,0.1);
            border: 2px solid #007bff;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .filter-info {{
            text-align: center;
            padding: 10px 20px;
            background: #e3f2fd;
            color: #1976d2;
            font-weight: bold;
            display: none;
        }}
        .movies-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .movie-card {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            text-decoration: none;
            color: inherit;
            display: block;
        }}
        .movie-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        }}
        .movie-card.hidden {{
            display: none;
        }}
        .movie-poster {{
            width: 100%;
            height: 400px;
            object-fit: cover;
            background: linear-gradient(45deg, #f0f0f0 25%, transparent 25%), 
                        linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), 
                        linear-gradient(45deg, transparent 75%, #f0f0f0 75%), 
                        linear-gradient(-45deg, transparent 75%, #f0f0f0 75%);
            background-size: 20px 20px;
            background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
        }}
        .movie-info {{
            padding: 20px;
        }}
        .movie-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
            line-height: 1.3;
        }}
        .movie-overview {{
            color: #6c757d;
            font-size: 0.9em;
            line-height: 1.4;
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .movie-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .release-date {{
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            color: #495057;
        }}
        .status-badge {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .status-yes {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .status-soon {{
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }}
        .status-no {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .status-tbd {{
            background: #e2e3e5;
            color: #383d41;
            border: 1px solid #d6d8db;
        }}
        .ombi-link {{
            display: inline-block;
            background: #007bff;
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: bold;
            transition: background-color 0.3s ease;
            margin-right: 8px;
        }}
        .ombi-link:hover {{
            background: #0056b3;
            color: white;
            text-decoration: none;
        }}
        .vuniper-link {{
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: bold;
            transition: background-color 0.3s ease;
        }}
        .vuniper-link:hover {{
            background: #1e7e34;
            color: white;
            text-decoration: none;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }}
        .footer a {{
            color: #007bff;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        @media (max-width: 768px) {{
            .movies-grid {{
                grid-template-columns: 1fr;
                padding: 15px;
            }}
            .stats {{
                flex-direction: column;
                gap: 15px;
            }}
            .header h1 {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Movie Download Status Report</h1>
            <p>Generated on {current_date}</p>
        </div>
        
        <div class="stats">
            <div class="stat" data-filter="all" onclick="filterMovies('all')">
                <div class="stat-number">{total_movies}</div>
                <div class="stat-label">Total Movies</div>
            </div>
            <div class="stat" data-filter="yes" onclick="filterMovies('yes')">
                <div class="stat-number" style="color: #28a745;">{available_count}</div>
                <div class="stat-label">Available Now</div>
            </div>
            <div class="stat" data-filter="soon" onclick="filterMovies('soon')">
                <div class="stat-number" style="color: #ffc107;">{soon_count}</div>
                <div class="stat-label">Coming Soon</div>
            </div>
            <div class="stat" data-filter="unavailable" onclick="filterMovies('unavailable')">
                <div class="stat-number" style="color: #dc3545;">{unavailable_count}</div>
                <div class="stat-label">Not Available</div>
            </div>
        </div>
        
        <div class="filter-info" id="filterInfo">
            Showing all movies
        </div>
        
        <div class="movies-grid" id="moviesGrid">"""
    
    # Generate movie cards
    for movie in movie_results:
        # Determine status class and text
        status_class = f"status-{movie['status'].lower()}"
        if movie['status'] == 'TBD':
            status_class = "status-tbd"
        
        # Determine filter category
        if movie['status'] == 'Yes':
            filter_category = 'yes'
        elif movie['status'] == 'Soon':
            filter_category = 'soon'
        else:  # 'No' or 'TBD'
            filter_category = 'unavailable'
        
        # Format dates for display
        theater_date = movie.get('theater_date', 'TBD')
        digital_date = movie.get('digital_date', 'TBD')
        
        if theater_date == 'TBD':
            theater_date = 'TBD'
        if digital_date == 'TBD':
            digital_date = 'TBD'
        
        # Generate links HTML
        links_html = ""
        if OMBI_SITE_URL and movie.get('movie_id'):
            ombi_url = f"{OMBI_SITE_URL}/details/movie/{movie['movie_id']}"
            links_html += f'<a href="{ombi_url}" class="ombi-link" target="_blank">Ombi</a>'

        if movie.get('vuniper_url'):
            links_html += f'<a href="{movie["vuniper_url"]}" class="vuniper-link" target="_blank">Vuniper</a>'
        
        # Generate movie card HTML
        html += f"""
            <div class="movie-card" data-filter="{filter_category}">
                <img src="{movie['poster_url']}" alt="{movie['title']} Poster" class="movie-poster" 
                     onerror="this.style.display='none';">
                <div class="movie-info">
                    <div class="movie-title">{movie['title']}</div>
                    <div class="movie-overview">{movie['overview']}</div>
                    <div class="movie-meta">
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <span class="release-date">🎭 Theater: {theater_date}</span>
                            <span class="release-date">💿 Digital: {digital_date}</span>
                        </div>
                        <span class="status-badge {status_class}">{movie['status']}</span>
                    </div>
                    {links_html}
                </div>
            </div>"""
    
    html += f"""
        </div>
        
        <div class="footer">
            <p>Generated by ombicheck.py | Data from The Movie Database (TMDb) and Vuniper | <a href="https://github.com/WilmeRWubS/OmbiChecker" target="_blank" rel="noopener noreferrer">https://github.com/WilmeRWubS/OmbiChecker</a></p>
        </div>
    </div>
    
    <script>
        let currentFilter = 'all';
        
        function filterMovies(filter) {{
            currentFilter = filter;
            const movieCards = document.querySelectorAll('.movie-card');
            const filterInfo = document.getElementById('filterInfo');
            const stats = document.querySelectorAll('.stat');
            
            // Remove active class from all stats
            stats.forEach(stat => stat.classList.remove('active'));
            
            // Add active class to clicked stat
            document.querySelector(`[data-filter="${{filter}}"]`).classList.add('active');
            
            // Show/hide movies based on filter
            movieCards.forEach(card => {{
                if (filter === 'all') {{
                    card.classList.remove('hidden');
                }} else {{
                    const cardFilter = card.getAttribute('data-filter');
                    if (cardFilter === filter) {{
                        card.classList.remove('hidden');
                    }} else {{
                        card.classList.add('hidden');
                    }}
                }}
            }});
            
            // Update filter info
            const visibleCards = document.querySelectorAll('.movie-card:not(.hidden)').length;
            let filterText = '';
            
            switch(filter) {{
                case 'all':
                    filterText = `Showing all {total_movies} movies`;
                    filterInfo.style.display = 'none';
                    break;
                case 'yes':
                    filterText = `Showing ${{visibleCards}} available movies`;
                    filterInfo.style.display = 'block';
                    break;
                case 'soon':
                    filterText = `Showing ${{visibleCards}} movies coming soon`;
                    filterInfo.style.display = 'block';
                    break;
                case 'unavailable':
                    filterText = `Showing ${{visibleCards}} unavailable movies`;
                    filterInfo.style.display = 'block';
                    break;
            }}
            
            filterInfo.textContent = filterText;
        }}
        
        // Initialize with all movies shown
        document.addEventListener('DOMContentLoaded', function() {{
            filterMovies('all');
        }});
    </script>
</body>
</html>"""
    
    return html

import argparse

def run_cli():
    parser = argparse.ArgumentParser(description="Movie Download Checker CLI")
    parser.add_argument("--ombi-db", help="Path to Ombi SQLite database (ombi.db)", default="ombi.db")
    parser.add_argument("--tmdb-token", help="TMDb Bearer Token", required=True)
    parser.add_argument("--language", help="TMDb language code (e.g., nl-NL)", default="nl-NL")
    parser.add_argument("--custom-dates", help="Path to digital_dates.txt", default="digital_dates.txt")
    parser.add_argument("--output-html", help="Path to save HTML report", required=False)
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Set globals based on CLI args
    global TMDB_BEARER_TOKEN, HTML_LANGUAGE, HEADERS
    TMDB_BEARER_TOKEN = args.tmdb_token
    HTML_LANGUAGE = args.language
    HEADERS = {
        "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
        "accept": "application/json"
    }

    # Fetch movie lines from database
    try:
        conn = connect_db(args.ombi_db)
        lines = get_pending_requests(conn)
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return

    if not lines:
        print("Geen openstaande filmverzoeken gevonden in de Ombi-database.")
        return

    print(f"{len(lines)} films gevonden. Start met controleren...\n")

    custom_dates = load_custom_digital_dates()  # automatisch pakt hij digital_dates.txt
    driver = setup_selenium_driver()
    if not driver:
        return

    results = []
    try:
        for idx, line in enumerate(lines, 1):
            title = extract_title(line)
            print(f"[{idx}/{len(lines)}] Verwerk: {title}")
            
            # Extract expected year
            expected_year = None
            year_match = re.search(r'\((\d{4})\)', title)
            if year_match:
                expected_year = int(year_match.group(1))
            else:
                # Fallback: zoek naar een jaartal ergens in de regel
                year_match = re.search(r'(\d{4})', line)
                if year_match:
                    potential_year = int(year_match.group(1))
                    if 1900 <= potential_year <= 2035:
                        expected_year = potential_year

            vuniper_info = search_movie_vuniper(title, driver, custom_dates, expected_year=expected_year)
            tmdb_data = search_movie_tmdb(title)

            result = {
                "title": title,
                "theater_date": vuniper_info.get("theater_date") if vuniper_info else "TBD",
                "digital_date": vuniper_info.get("digital_date") if vuniper_info else "TBD",
                "status": determine_downloadable_status(
                    vuniper_info,
                    vuniper_info.get("theater_date") if vuniper_info else None,
                    vuniper_info.get("digital_date") if vuniper_info else None
                ),
                "poster_url": "",
                "overview": "Geen beschrijving beschikbaar.",
                "movie_id": tmdb_data.get("id") if tmdb_data else None,
                "vuniper_url": vuniper_info.get("vuniper_url") if vuniper_info else None
            }

            if tmdb_data:
                poster_path = tmdb_data.get("poster_path")
                if poster_path:
                    result["poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                result["overview"] = tmdb_data.get("overview", result["overview"])

            results.append(result)
    finally:
        driver.quit()

    # Toon CLI overzicht
    print("\nResultaten:")
    for r in results:
        print(f"{r['title']}: {r['status']} - Digital: {r['digital_date']}")

    # Optioneel HTML rapport
    global movie_results
    movie_results = results
    if args.output_html:
        html = generate_html_content()
        try:
            with open(args.output_html, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\n✅ HTML rapport opgeslagen als: {args.output_html}")
        except Exception as e:
            print(f"❌ Fout bij opslaan van HTML: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli()
    else:
        import tkinter as tk
        from tkinter import scrolledtext, ttk, filedialog, messagebox

        window = tk.Tk()
        window.title("Movie Downloadability Checker (Proper Release)")
        window.geometry("900x650")

        tk.Label(window, text="Paste your tab-separated movie list below:").pack(anchor='w', padx=10, pady=(10, 0))

        input_text = scrolledtext.ScrolledText(window, height=15, width=110)
        input_text.pack(padx=10, pady=5)

        controls_frame = tk.Frame(window)
        controls_frame.pack(pady=10)

        tk.Button(controls_frame, text="Check Availability", command=check_movies).pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(controls_frame, text="Sort by:").pack(side=tk.LEFT, padx=(0, 5))
        sort_var = tk.StringVar(value="Title")
        sort_dropdown = ttk.Combobox(controls_frame, textvariable=sort_var, 
                                    values=["Title", "Theater Date", "Digital Date", "Downloadable"], 
                                    state="readonly", width=15)
        sort_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(controls_frame, text="Sort", command=sort_results).pack(side=tk.LEFT, padx=(0, 20))

        tk.Button(controls_frame, text="Generate HTML Report", command=generate_html_report, 
                bg="#007bff", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(controls_frame, text="Load from Ombi DB", command=load_from_ombi_db).pack(side=tk.LEFT, padx=(0, 20))

        tk.Button(controls_frame, text="Settings", command=open_settings_window, 
                bg="#6c757d", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT)

        tk.Label(window, text="Results:").pack(anchor='w', padx=10)
        output_text = scrolledtext.ScrolledText(window, height=15, width=110, state=tk.DISABLED)
        output_text.pack(padx=10, pady=5)

        window.mainloop()