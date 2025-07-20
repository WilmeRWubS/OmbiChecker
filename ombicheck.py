import requests
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox
import re
from datetime import datetime
import os
import webbrowser
import time
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

def search_digital_release_google(title, driver):
    """Search Google for digital release date information."""
    try:
        # Construct search query
        search_query = f"{title} 2025 digital release date"
        google_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
        
        driver.get(google_url)
        time.sleep(3)
        
        # Look for date patterns in search results
        page_source = driver.page_source.lower()
        
        # Common patterns for digital release dates
        digital_patterns = [
            r'digital.*?(?:august|july|september|october|november|december)\s+(\d{1,2}),?\s+2025',
            r'(?:vod|streaming|digital).*?(\d{1,2})\s+(?:august|july|september|october|november|december)\s+2025',
            r'(?:august|july|september|october|november|december)\s+(\d{1,2}),?\s+2025.*?(?:digital|vod|streaming)',
        ]
        
        month_map = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }
        
        for pattern in digital_patterns:
            matches = re.finditer(pattern, page_source)
            for match in matches:
                # Extract month and day from the surrounding text
                full_match = match.group(0)
                for month_name, month_num in month_map.items():
                    if month_name in full_match:
                        day_match = re.search(r'(\d{1,2})', full_match)
                        if day_match:
                            day = day_match.group(1).zfill(2)
                            return f"2025-{month_num}-{day}"
        
        return None
        
    except Exception as e:
        print(f"Error searching Google for '{title}': {str(e)}")
        return None

def search_movie_vuniper(title, driver, custom_dates=None):
    """Search for a movie on Vuniper.com and get release information with improved search."""
    try:
        driver.get("https://vuniper.com")
        time.sleep(2)
        
        # Try multiple search variations
        search_variations = [
            title,  # Original title
            title.replace(":", ""),  # Remove colons
            title.replace(":", " "),  # Replace colons with spaces
            title.split(":")[0].strip() if ":" in title else title,  # Take part before colon
            title.replace("The ", "").strip() if title.startswith("The ") else f"The {title}",  # Toggle "The"
        ]
        
        # Remove duplicates while preserving order
        search_variations = list(dict.fromkeys(search_variations))
        
        vuniper_info = None
        
        for search_term in search_variations:
            try:
                print(f"Trying search term: '{search_term}'")
                
                # Find and use search input
                search_input = driver.find_element(By.ID, "search-input")
                search_input.clear()
                search_input.send_keys(search_term)
                time.sleep(3)  # Give more time for suggestions to load
                
                # Try to find suggestions
                suggestions = driver.find_elements(By.CSS_SELECTOR, ".search-suggestion")
                
                if suggestions:
                    # Look for the best match (preferably with 2025 in it)
                    best_suggestion = None
                    for suggestion in suggestions:
                        suggestion_text = suggestion.text.lower()
                        if "2025" in suggestion_text:
                            best_suggestion = suggestion
                            break
                    
                    # If no 2025 match, take the first suggestion
                    if not best_suggestion and suggestions:
                        best_suggestion = suggestions[0]
                    
                    if best_suggestion:
                        print(f"Found suggestion: {best_suggestion.text}")
                        best_suggestion.click()
                        time.sleep(4)  # Give more time for page to load
                        
                        # Try to extract release info
                        vuniper_info = extract_vuniper_release_info(driver)
                        
                        if vuniper_info and (vuniper_info.get('theater_date') or vuniper_info.get('digital_date')):
                            print(f"Successfully found release info for '{search_term}'")
                            break  # Found valid info, stop searching
                        else:
                            print(f"No release info found for '{search_term}', trying next variation")
                            # Go back to search for next variation
                            driver.get("https://vuniper.com")
                            time.sleep(2)
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
            title_lower = title.lower()
            matched_custom_date = None
            
            # Try exact match first
            if title_lower in custom_dates:
                matched_custom_date = custom_dates[title_lower]
            else:
                # Try partial matching
                for custom_title, custom_date in custom_dates.items():
                    # Check if custom title is contained in search title or vice versa
                    if (custom_title in title_lower or title_lower in custom_title or
                        # Check without "the" prefix
                        custom_title.replace("the ", "") in title_lower.replace("the ", "") or
                        title_lower.replace("the ", "") in custom_title.replace("the ", "")):
                        matched_custom_date = custom_date
                        print(f"Matched custom date: '{custom_title}' -> '{title}' = {custom_date}")
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
        
        return vuniper_info
        
    except Exception as e:
        print(f"Error searching Vuniper for '{title}': {str(e)}")
        return None

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

def determine_downloadable_status(release_info):
    """Determine downloadable status based on Vuniper release info."""
    if not release_info:
        return "TBD"
    return release_info.get('status', 'TBD')

def extract_title(line):
    """Extract clean movie title from input line."""
    # Match until the first ( (e.g., "Movie Title (07/01/2025)")
    match = re.match(r"^(.*?)\s*\(", line)
    if match:
        return match.group(1).strip()
    
    # Fallback: take the first tab-split section
    return line.split('\t')[0].strip()

def display_results(results):
    """Display the results in the output text widget."""
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    
    output_text.insert(tk.END, f"{'Title':<45} | {'Release Type':<15} | {'Release Date':<12} | Downloadable?\n")
    output_text.insert(tk.END, "-" * 95 + "\n")
    
    for result in results:
        release_type = "Digital/Streaming" if result['status'] in ['Yes', 'Soon'] else "Theater Only"
        output_text.insert(tk.END, f"{result['title']:<45} | {release_type:<15} | {result['date']:<12} | {result['status']}\n")
    
    output_text.config(state=tk.DISABLED)

def sort_results():
    """Sort the results based on the selected criteria."""
    if not movie_results:
        return
    
    sort_by = sort_var.get()
    
    if sort_by == "Title":
        sorted_results = sorted(movie_results, key=lambda x: x['title'].lower())
    elif sort_by == "Release Date":
        def date_sort_key(x):
            if x['date'] == "TBD" or x['date'] == "-":
                return "9999-12-31"
            return x['date']
        sorted_results = sorted(movie_results, key=date_sort_key)
    elif sort_by == "Downloadable":
        status_order = {"Yes": 1, "Soon": 2, "TBD": 3, "No": 4}
        sorted_results = sorted(movie_results, key=lambda x: status_order.get(x['status'], 5))
    else:
        sorted_results = movie_results
    
    display_results(sorted_results)

# ... existing code for open_settings_window, generate_html_report, etc. remains the same ...

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
            
            # Update progress
            output_text.config(state=tk.NORMAL)
            output_text.delete("1.0", tk.END)
            output_text.insert(tk.END, f"Processing movie {current_movie}/{total_movies}: {title}\n")
            output_text.config(state=tk.DISABLED)
            output_text.update()
            
            # Search Vuniper for release info
            vuniper_info = search_movie_vuniper(title, driver)
            
            # Search TMDb for poster and description
            tmdb_data = search_movie_tmdb(title)
            
            # Prepare movie result
            if vuniper_info:
                # Determine which date to show and release type
                if vuniper_info.get('digital_date'):
                    # Has digital/streaming date - use that
                    display_date = vuniper_info['digital_date']
                    release_type = 'Digital/Streaming'
                elif vuniper_info.get('theater_date'):
                    # Only theater date available
                    display_date = vuniper_info['theater_date']
                    release_type = 'Theater Only'
                else:
                    display_date = "TBD"
                    release_type = 'TBD'
                
                status = vuniper_info.get('status', 'TBD')
            else:
                display_date = "TBD"
                release_type = 'TBD'
                status = "TBD"
            
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
                'type': release_type,
                'date': display_date,
                'status': status,
                'poster_url': poster_url,
                'overview': overview,
                'movie_id': movie_id
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
        }}
        .ombi-link:hover {{
            background: #0056b3;
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
            <div class="stat">
                <div class="stat-number">{total_movies}</div>
                <div class="stat-label">Total Movies</div>
            </div>
            <div class="stat">
                <div class="stat-number" style="color: #28a745;">{available_count}</div>
                <div class="stat-label">Available Now</div>
            </div>
            <div class="stat">
                <div class="stat-number" style="color: #ffc107;">{soon_count}</div>
                <div class="stat-label">Coming Soon</div>
            </div>
            <div class="stat">
                <div class="stat-number" style="color: #dc3545;">{unavailable_count}</div>
                <div class="stat-label">Not Available</div>
            </div>
        </div>
        
        <div class="movies-grid">"""
    
    # Generate movie cards
    for movie in movie_results:
        # Determine status class and text
        status_class = f"status-{movie['status'].lower()}"
        if movie['status'] == 'TBD':
            status_class = "status-tbd"
        
        # Handle poster image
        poster_html = ""
        if movie['poster_url']:
            poster_html = f'<img src="{movie["poster_url"]}" alt="{movie["title"]} Poster" class="movie-poster" onerror="this.style.display=\'none\'">'
        else:
            poster_html = '<div class="movie-poster" style="display: flex; align-items: center; justify-content: center; background: #f8f9fa; color: #6c757d; font-size: 3em;">🎬</div>'
        
        # Handle Ombi link
        ombi_link_html = ""
        if OMBI_SITE_URL and movie.get('movie_id'):
            ombi_link_html = f'<a href="{OMBI_SITE_URL}/search/movie/{movie["movie_id"]}" target="_blank" class="ombi-link">Request on Ombi</a>'
        
        # Format release date
        release_date = movie['date'] if movie['date'] != 'TBD' else 'To Be Determined'
        
        html += f"""
            <div class="movie-card">
                {poster_html}
                <div class="movie-info">
                    <div class="movie-title">{movie['title']}</div>
                    <div class="movie-overview">{movie['overview']}</div>
                    <div class="movie-meta">
                        <span class="release-date">📅 {release_date}</span>
                        <span class="status-badge {status_class}">{movie['status']}</span>
                    </div>
                    {ombi_link_html}
                </div>
            </div>"""
    
    html += f"""
        </div>
        
        <div class="footer">
            <p>Generated by Movie Downloadability Checker | Data sourced from Vuniper.com and TMDb</p>
            <p>Report generated on {current_date}</p>
        </div>
    </div>
</body>
</html>"""
    
    return html

# --- GUI setup ---
window = tk.Tk()
window.title("Movie Downloadability Checker (Proper Release)")
window.geometry("900x650")

tk.Label(window, text="Paste your tab-separated movie list below:").pack(anchor='w', padx=10, pady=(10, 0))

input_text = scrolledtext.ScrolledText(window, height=15, width=110)
input_text.pack(padx=10, pady=5)

# Button and sort controls frame
controls_frame = tk.Frame(window)
controls_frame.pack(pady=10)

tk.Button(controls_frame, text="Check Availability", command=check_movies).pack(side=tk.LEFT, padx=(0, 20))

# Sort controls
tk.Label(controls_frame, text="Sort by:").pack(side=tk.LEFT, padx=(0, 5))
sort_var = tk.StringVar(value="Title")
sort_dropdown = ttk.Combobox(controls_frame, textvariable=sort_var, 
                            values=["Title", "Type", "Release Date", "Downloadable"], 
                            state="readonly", width=15)
sort_dropdown.pack(side=tk.LEFT, padx=(0, 10))
tk.Button(controls_frame, text="Sort", command=sort_results).pack(side=tk.LEFT, padx=(0, 20))

# HTML Export button
tk.Button(controls_frame, text="Generate HTML Report", command=generate_html_report, 
          bg="#007bff", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))

# Settings button
tk.Button(controls_frame, text="Settings", command=open_settings_window, 
          bg="#6c757d", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT)

tk.Label(window, text="Results:").pack(anchor='w', padx=10)
output_text = scrolledtext.ScrolledText(window, height=15, width=110, state=tk.DISABLED)
output_text.pack(padx=10, pady=5)

window.mainloop()