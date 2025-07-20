#!/bin/bash

# Configuration
TMDB_BEARER_TOKEN="enterhere"
USE_CUSTOM_BACKGROUND="yes"
CUSTOM_BACKGROUND_URL="https://i.imgur.com/9QY51tm.jpeg"
HTML_LANGUAGE="nl-NL"
OMBI_SITE_URL=""  # example : https://your-ombi-site.com
INPUT_FILE="/root/movies.txt"   # if not using database this is used
OUTPUT_FILE="/root/test.html"
OMBI_DB_PATH="/opt/Ombi/Ombi.db"
USE_OMBI_DB="yes"  # "yes" or "no"
INCLUDE_TV_SHOWS="no"  # "yes" or "no"
FILTER_UNAVAILABLE="yes"  # "yes" to only process unavailable items, "no" for all
DIGITAL_DATES_FILE="./digital_dates.txt"  # Custom digital dates file
CHROME_BINARY="/usr/bin/google-chrome"  # Path to Chrome binary
CHROMEDRIVER_PATH="/usr/bin/chromedriver"  # Path to ChromeDriver

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 [MODE] [OPTIONS]"
    echo ""
    echo "Modes:"
    echo "  File mode (default):"
    echo "    $0 -f INPUT_FILE -o OUTPUT_FILE"
    echo ""
    echo "  Database mode:"
    echo "    $0 -d OMBI_DB_PATH -o OUTPUT_FILE"
    echo ""
    echo "Options:"
    echo "  -f FILE         Input file with movie titles"
    echo "  -d DATABASE     Ombi database path"
    echo "  -o OUTPUT       Output HTML file"
    echo "  -u              Filter unavailable items only"
    echo "  -t              Include TV shows (database mode only)"
    echo "  -h              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 -f movies.txt -o report.html"
    echo "  $0 -d /opt/Ombi/Ombi.db -o report.html -u"
}

# Function to check dependencies
check_dependencies() {
    local missing_deps=()
    local chrome_missing=false
    local chromedriver_missing=false
    
    echo -e "${BLUE}Checking dependencies...${NC}"
    
    # Check for required commands
    for cmd in curl jq sqlite3; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
            echo -e "${RED}✗ Missing: $cmd${NC}"
        else
            echo -e "${GREEN}✓ Found: $cmd${NC}"
        fi
    done
    
    # Check for Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        missing_deps+=("python3")
        echo -e "${RED}✗ Missing: python3${NC}"
    else
        echo -e "${GREEN}✓ Found: python3${NC}"
    fi
    
    # Check for Chrome/Chromium
    echo "Checking for Chrome..."
    if [[ -f "$CHROME_BINARY" ]]; then
        echo -e "${GREEN}✓ Found Chrome at: $CHROME_BINARY${NC}"
    elif command -v google-chrome &> /dev/null; then
        CHROME_BINARY="google-chrome"
        echo -e "${GREEN}✓ Found Chrome: google-chrome${NC}"
    elif command -v chromium-browser &> /dev/null; then
        CHROME_BINARY="chromium-browser"
        echo -e "${GREEN}✓ Found Chromium: chromium-browser${NC}"
    elif command -v chromium &> /dev/null; then
        CHROME_BINARY="chromium"
        echo -e "${GREEN}✓ Found Chromium: chromium${NC}"
    else
        chrome_missing=true
        echo -e "${RED}✗ Chrome/Chromium not found${NC}"
    fi
    
    # Check for Selenium
    echo "Checking for Selenium..."
    if python3 -c "import selenium" 2>/dev/null; then
        echo -e "${GREEN}✓ Selenium available for python3${NC}"
    elif python -c "import selenium" 2>/dev/null; then
        echo -e "${GREEN}✓ Selenium available for python${NC}"
    else
        missing_deps+=("python3-selenium")
        echo -e "${RED}✗ Missing: python3-selenium${NC}"
    fi
    
    # Check for webdriver-manager (optional but recommended)
    echo "Checking for webdriver-manager..."
    if python3 -c "import webdriver_manager" 2>/dev/null; then
        echo -e "${GREEN}✓ webdriver-manager available (ChromeDriver will be auto-managed)${NC}"
    elif python -c "import webdriver_manager" 2>/dev/null; then
        echo -e "${GREEN}✓ webdriver-manager available (ChromeDriver will be auto-managed)${NC}"
    else
        echo -e "${YELLOW}⚠ webdriver-manager not found (will try system ChromeDriver)${NC}"
        # Check for ChromeDriver manually
        if [[ -f "$CHROMEDRIVER_PATH" ]]; then
            echo -e "${GREEN}✓ Found ChromeDriver at: $CHROMEDRIVER_PATH${NC}"
        elif command -v chromedriver &> /dev/null; then
            echo -e "${GREEN}✓ Found ChromeDriver in PATH${NC}"
        else
            chromedriver_missing=true
            echo -e "${RED}✗ ChromeDriver not found${NC}"
        fi
    fi
    
    # If dependencies are missing, provide installation guide
    if [[ ${#missing_deps[@]} -gt 0 || "$chrome_missing" == true || "$chromedriver_missing" == true ]]; then
        echo -e "${RED}Missing dependencies detected!${NC}"
        echo ""
        
        # Basic dependencies
        if [[ ${#missing_deps[@]} -gt 0 ]]; then
            echo -e "${YELLOW}Step 1: Install basic dependencies${NC}"
            echo "Run the following command:"
            echo -e "${GREEN}sudo apt-get update && sudo apt-get install -y curl jq sqlite3 python3 python3-pip${NC}"
            echo ""
        fi
        
        # Chrome installation
        if [[ "$chrome_missing" == true ]]; then
            echo -e "${YELLOW}Step 2: Install Google Chrome${NC}"
            echo "Run these commands one by one:"
            echo -e "${GREEN}# Download Chrome package"
            echo "wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
            echo ""
            echo "# Install Chrome"
            echo "sudo apt-get install -y ./google-chrome-stable_current_amd64.deb"
            echo ""
            echo "# Clean up"
            echo "rm google-chrome-stable_current_amd64.deb${NC}"
            echo ""
            echo "If you encounter dependency issues, run:"
            echo -e "${GREEN}sudo apt-get install -f${NC}"
            echo ""
        fi
        
        # Selenium installation
        if [[ " ${missing_deps[@]} " =~ " python3-selenium " ]]; then
            echo -e "${YELLOW}Step 3: Install Selenium and WebDriver Manager${NC}"
            echo "Run these commands:"
            echo -e "${GREEN}pip3 install selenium webdriver-manager${NC}"
            echo ""
        fi
        
        # ChromeDriver note
        if [[ "$chromedriver_missing" == true ]]; then
            echo -e "${YELLOW}Step 4: Install webdriver-manager (recommended)${NC}"
            echo "This will automatically manage ChromeDriver:"
            echo -e "${GREEN}pip3 install webdriver-manager${NC}"
            echo ""
            echo "Or manually install ChromeDriver:"
            echo -e "${GREEN}# Download ChromeDriver"
            echo "CHROME_VERSION=\$(google-chrome --version | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+')"
            echo "wget -O /tmp/chromedriver.zip \"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_\${CHROME_VERSION%.*.*}/chromedriver_linux64.zip\""
            echo "unzip /tmp/chromedriver.zip -d /tmp/"
            echo "sudo mv /tmp/chromedriver /usr/bin/chromedriver"
            echo "sudo chmod +x /usr/bin/chromedriver${NC}"
            echo ""
        fi
        
        echo -e "${BLUE}After installing the dependencies, run this script again.${NC}"
        echo ""
        echo -e "${YELLOW}Quick install (all at once):${NC}"
        echo -e "${GREEN}sudo apt-get update && sudo apt-get install -y curl jq sqlite3 python3 python3-pip && \\"
        echo "wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \\"
        echo "sudo apt-get install -y ./google-chrome-stable_current_amd64.deb && \\"
        echo "rm google-chrome-stable_current_amd64.deb && \\"
        echo "pip3 install selenium webdriver-manager${NC}"
        
        exit 1
    fi
    
    echo -e "${GREEN}✓ All dependencies are satisfied${NC}"
    echo ""
}

# Function to standardize date format
standardize_date() {
    local date_str="$1"
    
    if [[ -z "$date_str" ]]; then
        echo ""
        return
    fi
    
    # Try different date formats and convert to YYYY-MM-DD
    if date -d "$date_str" "+%Y-%m-%d" 2>/dev/null; then
        date -d "$date_str" "+%Y-%m-%d"
    elif [[ "$date_str" =~ ^[0-9]{4}$ ]]; then
        # Year only - assume January 1st
        echo "${date_str}-01-01"
    else
        echo ""
    fi
}

# Function to load custom digital dates
load_custom_digital_dates() {
    declare -A custom_dates
    
    if [[ -f "$DIGITAL_DATES_FILE" ]]; then
        echo -e "${BLUE}Loading custom digital dates from $DIGITAL_DATES_FILE${NC}"
        
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            
            # Parse format: "Movie Title MONTH DAY" or "Movie Title DAY MONTH" or with year
            if [[ "$line" =~ ^(.+)[[:space:]]+([A-Za-z]+)[[:space:]]+([0-9]{1,2})(,[[:space:]]*([0-9]{4}))?$ ]]; then
                title="${BASH_REMATCH[1]}"
                month="${BASH_REMATCH[2]}"
                day="${BASH_REMATCH[3]}"
                year="${BASH_REMATCH[5]:-2025}"
                
                # Convert month name to number
                case "${month,,}" in
                    january|jan) month_num="01" ;;
                    february|feb) month_num="02" ;;
                    march|mar) month_num="03" ;;
                    april|apr) month_num="04" ;;
                    may) month_num="05" ;;
                    june|jun) month_num="06" ;;
                    july|jul) month_num="07" ;;
                    august|aug) month_num="08" ;;
                    september|sep) month_num="09" ;;
                    october|oct) month_num="10" ;;
                    november|nov) month_num="11" ;;
                    december|dec) month_num="12" ;;
                    *) continue ;;
                esac
                
                formatted_date="${year}-${month_num}-$(printf "%02d" "$day")"
                custom_dates["${title,,}"]="$formatted_date"
                echo "  Loaded: $title -> $formatted_date"
            fi
        done < "$DIGITAL_DATES_FILE"
    fi
    
    # Export the associative array for use in other functions
    declare -p custom_dates > /tmp/custom_dates.sh
}

# Function to search movie on Vuniper using headless Chrome
search_movie_vuniper() {
    local title="$1"
    local temp_dir="/tmp/vuniper_$$"
    local result_file="$temp_dir/result.json"
    
    mkdir -p "$temp_dir"
    
    # Create a Python script for Selenium automation with webdriver-manager
    cat > "$temp_dir/vuniper_search.py" << 'EOF'
import sys
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Try to use webdriver-manager for automatic ChromeDriver management
try:
    from webdriver_manager.chrome import ChromeDriverManager
    use_webdriver_manager = True
except ImportError:
    use_webdriver_manager = False

def standardize_date(date_str):
    if not date_str:
        return None
    try:
        date_str = date_str.strip()
        # Handle various date formats
        if re.match(r'[A-Za-z]{3}\s+\d{1,2},\s+\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%b %d, %Y")
            return date_obj.strftime("%Y-%m-%d")
        elif re.match(r'[A-Za-z]+\s+\d{1,2},\s+\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%B %d, %Y")
            return date_obj.strftime("%Y-%m-%d")
        elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            date_obj = datetime.strptime(date_str, "%m/%d/%Y")
            return date_obj.strftime("%Y-%m-%d")
        elif re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%Y-%m-%d")
        return None
    except:
        return None

def search_vuniper(title):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    
    try:
        # Use webdriver-manager if available, otherwise try system ChromeDriver
        if use_webdriver_manager:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Try to find ChromeDriver in common locations
            chromedriver_paths = [
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
                "/opt/chromedriver",
                "chromedriver"  # In PATH
            ]
            
            driver = None
            for path in chromedriver_paths:
                try:
                    if path == "chromedriver":
                        driver = webdriver.Chrome(options=chrome_options)
                    else:
                        service = Service(path)
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                    break
                except:
                    continue
            
            if not driver:
                raise Exception("ChromeDriver not found in common locations")
        
        driver.get("https://vuniper.com")
        time.sleep(2)
        
        # Search for the movie
        search_input = driver.find_element(By.ID, "search-input")
        search_input.clear()
        search_input.send_keys(title)
        time.sleep(3)
        
        # Look for suggestions
        suggestions = driver.find_elements(By.CSS_SELECTOR, ".search-suggestion")
        
        if suggestions:
            # Click first relevant suggestion
            best_suggestion = None
            for suggestion in suggestions:
                if "2025" in suggestion.text.lower():
                    best_suggestion = suggestion
                    break
            
            if not best_suggestion and suggestions:
                best_suggestion = suggestions[0]
            
            if best_suggestion:
                best_suggestion.click()
                time.sleep(4)
                
                # Extract release info
                release_info = {'theater_date': None, 'digital_date': None, 'status': 'TBD'}
                
                # Look for theater date
                try:
                    theater_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Theaters')]/preceding-sibling::span[@class='semibold']")
                    theater_date = standardize_date(theater_element.text.strip())
                    if theater_date:
                        release_info['theater_date'] = theater_date
                except:
                    pass
                
                # Look for digital date
                try:
                    digital_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Streaming')]/preceding-sibling::span[@class='semibold']")
                    digital_date = standardize_date(digital_element.text.strip())
                    if digital_date:
                        release_info['digital_date'] = digital_date
                except:
                    pass
                
                # Determine status
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
                        # Assume digital release 90 days after theater
                        digital_estimate = theater_obj.replace(day=theater_obj.day + 90) if theater_obj.day <= 275 else theater_obj.replace(year=theater_obj.year + 1, month=1, day=theater_obj.day - 275)
                        release_info['status'] = 'Yes' if digital_estimate <= current_date else 'Soon'
                    except:
                        release_info['status'] = 'Soon'
                else:
                    release_info['status'] = 'TBD'
                
                driver.quit()
                return json.dumps(release_info)
        
        driver.quit()
        return "null"
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        try:
            driver.quit()
        except:
            pass
        return "null"

if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else ""
    result = search_vuniper(title)
    print(result)
EOF

    # Run the Python script
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
    fi
    
    local vuniper_result=$($python_cmd "$temp_dir/vuniper_search.py" "$title" 2>/dev/null)
    
    # Clean up
    rm -rf "$temp_dir"
    
    echo "$vuniper_result"
}

# Function to get movie info from TMDb
get_tmdb_info() {
    local title="$1"
    local encoded_title=$(printf '%s\n' "$title" | jq -sRr @uri)
    
    local response=$(curl -s -H "Authorization: Bearer $TMDB_BEARER_TOKEN" \
        -H "accept: application/json" \
        "https://api.themoviedb.org/3/search/movie?query=${encoded_title}&language=${HTML_LANGUAGE}")
    
    if [[ $(echo "$response" | jq -r '.results | length') -gt 0 ]]; then
        echo "$response" | jq -r '.results[0]'
    else
        echo "null"
    fi
}

# Function to determine downloadable status
determine_status() {
    local theater_date="$1"
    local digital_date="$2"
    local current_date=$(date +%Y-%m-%d)
    
    if [[ -n "$digital_date" && "$digital_date" != "null" ]]; then
        # Convert dates to seconds for comparison
        local digital_seconds=$(date -d "$digital_date" +%s 2>/dev/null)
        local current_seconds=$(date -d "$current_date" +%s)
        
        if [[ -n "$digital_seconds" && "$digital_seconds" -le "$current_seconds" ]]; then
            echo "Yes"
        else
            echo "Soon"
        fi
    elif [[ -n "$theater_date" && "$theater_date" != "null" ]]; then
        # Estimate digital release 90 days after theater
        local digital_estimate=$(date -d "$theater_date + 90 days" +%Y-%m-%d 2>/dev/null)
        if [[ -n "$digital_estimate" ]]; then
            local estimate_seconds=$(date -d "$digital_estimate" +%s)
            local current_seconds=$(date -d "$current_date" +%s)
            
            if [[ "$estimate_seconds" -le "$current_seconds" ]]; then
                echo "Yes"
            else
                echo "Soon"
            fi
        else
            echo "Soon"
        fi
    else
        echo "TBD"
    fi
}

# Function to extract movies from Ombi database
extract_from_database() {
    local db_path="$1"
    local include_tv="$2"
    local filter_unavailable="$3"
    
    if [[ ! -f "$db_path" ]]; then
        echo -e "${RED}Error: Database file not found: $db_path${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Extracting movies from Ombi database...${NC}" >&2
    
    local query="SELECT Title, Available FROM MovieRequests"
    
    if [[ "$filter_unavailable" == "yes" ]]; then
        query="$query WHERE Available = 0"
    fi
    
    # Add TV shows if requested
    if [[ "$include_tv" == "yes" ]]; then
        local tv_query="SELECT Title, Available FROM TvRequests"
        if [[ "$filter_unavailable" == "yes" ]]; then
            tv_query="$tv_query WHERE Available = 0"
        fi
        query="$query UNION $tv_query"
    fi
    
    sqlite3 "$db_path" "$query" | while IFS='|' read -r title available; do
        if [[ -n "$title" ]]; then
            echo "$title"
        fi
    done
}

# Function to process a single movie
process_movie() {
    local title="$1"
    local custom_dates_file="$2"
    
    echo -e "${YELLOW}Processing: $title${NC}"
    
    # Load custom dates if available
    source /tmp/custom_dates.sh 2>/dev/null || declare -A custom_dates
    
    # Search Vuniper first
    local vuniper_result=$(search_movie_vuniper "$title")
    local theater_date=""
    local digital_date=""
    local status="TBD"
    
    if [[ "$vuniper_result" != "null" && -n "$vuniper_result" ]]; then
        theater_date=$(echo "$vuniper_result" | jq -r '.theater_date // ""')
        digital_date=$(echo "$vuniper_result" | jq -r '.digital_date // ""')
        status=$(echo "$vuniper_result" | jq -r '.status // "TBD"')
    fi
    
    # Check custom dates if no digital date from Vuniper
    if [[ -z "$digital_date" || "$digital_date" == "null" ]]; then
        local title_lower=$(echo "$title" | tr '[:upper:]' '[:lower:]')
        if [[ -n "${custom_dates[$title_lower]}" ]]; then
            digital_date="${custom_dates[$title_lower]}"
            status=$(determine_status "$theater_date" "$digital_date")
            echo -e "${GREEN}  Using custom digital date: $digital_date${NC}"
        fi
    fi
    
    # Get TMDb info for poster and description
    local tmdb_info=$(get_tmdb_info "$title")
    local poster_url=""
    local overview="No description available."
    local movie_id=""
    
    if [[ "$tmdb_info" != "null" ]]; then
        local poster_path=$(echo "$tmdb_info" | jq -r '.poster_path // ""')
        if [[ -n "$poster_path" && "$poster_path" != "null" ]]; then
            poster_url="https://image.tmdb.org/t/p/w500${poster_path}"
        fi
        overview=$(echo "$tmdb_info" | jq -r '.overview // "No description available."')
        movie_id=$(echo "$tmdb_info" | jq -r '.id // ""')
    fi
    
    # Create JSON result
    local result=$(jq -n \
        --arg title "$title" \
        --arg theater_date "$theater_date" \
        --arg digital_date "$digital_date" \
        --arg status "$status" \
        --arg poster_url "$poster_url" \
        --arg overview "$overview" \
        --arg movie_id "$movie_id" \
        '{
            title: $title,
            theater_date: $theater_date,
            digital_date: $digital_date,
            status: $status,
            poster_url: $poster_url,
            overview: $overview,
            movie_id: $movie_id
        }')
    
    echo "$result"
}

# Function to generate HTML report
generate_html_report() {
    local results_file="$1"
    local output_file="$2"
    
    echo -e "${BLUE}Generating HTML report...${NC}"
    
    local current_date=$(date "+%Y-%m-%d %H:%M")
    local total_movies=$(jq length "$results_file")
    local available_now=$(jq '[.[] | select(.status == "Yes")] | length' "$results_file")
    local coming_soon=$(jq '[.[] | select(.status == "Soon")] | length' "$results_file")
    local not_available=$(jq '[.[] | select(.status == "TBD" or .status == "No")] | length' "$results_file")
    
    # Determine background style
    local background_style=""
    local overlay_style=""
    
    if [[ "$USE_CUSTOM_BACKGROUND" == "yes" && -n "$CUSTOM_BACKGROUND_URL" ]]; then
        background_style="background: url('$CUSTOM_BACKGROUND_URL') center center fixed; background-size: cover;"
        overlay_style="body::before { content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.3); z-index: -1; }"
    else
        background_style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
    fi
    
    cat > "$output_file" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movie Download Status Report</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            $background_style
            min-height: 100vh;
        }
        $overlay_style
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
            position: relative;
            z-index: 1;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.8;
            font-size: 1.1em;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        .stat {
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-label {
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .movies-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .movie-card {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .movie-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .movie-card.clickable {
            cursor: pointer;
        }
        .movie-card.clickable:hover .movie-title {
            color: #007bff;
        }
        .movie-poster {
            width: 100%;
            height: 400px;
            object-fit: cover;
            background: #f8f9fa;
        }
        .movie-info {
            padding: 20px;
        }
        .movie-title {
            font-size: 1.3em;
            font-weight: bold;
            margin: 0 0 10px 0;
            color: #2c3e50;
            line-height: 1.3;
            transition: color 0.3s ease;
        }
        .movie-details {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .detail-label {
            font-weight: 600;
            color: #6c757d;
            font-size: 0.9em;
        }
        .detail-value {
            font-weight: 500;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-yes {
            background: #d4edda;
            color: #155724;
        }
        .status-soon {
            background: #fff3cd;
            color: #856404;
        }
        .status-no {
            background: #f8d7da;
            color: #721c24;
        }
        .status-tbd {
            background: #e2e3e5;
            color: #383d41;
        }
        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }
        .footer a {
            color: #007bff;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Movie Download Status Report</h1>
            <p>Generated on $current_date</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number">$available_now</div>
                <div class="stat-label">Available Now</div>
            </div>
            <div class="stat">
                <div class="stat-number">$coming_soon</div>
                <div class="stat-label">Coming Soon</div>
            </div>
            <div class="stat">
                <div class="stat-number">$not_available</div>
                <div class="stat-label">Not Available</div>
            </div>
            <div class="stat">
                <div class="stat-number">$total_movies</div>
                <div class="stat-label">Total Movies</div>
            </div>
        </div>
        
        <div class="movies-grid">
EOF

    # Add movie cards
    jq -r '.[] | @json' "$results_file" | while read -r movie_json; do
        local title=$(echo "$movie_json" | jq -r '.title')
        local theater_date=$(echo "$movie_json" | jq -r '.theater_date // ""')
        local digital_date=$(echo "$movie_json" | jq -r '.digital_date // ""')
        local status=$(echo "$movie_json" | jq -r '.status')
        local poster_url=$(echo "$movie_json" | jq -r '.poster_url // ""')
        local overview=$(echo "$movie_json" | jq -r '.overview // "No description available."')
        local movie_id=$(echo "$movie_json" | jq -r '.movie_id // ""')
        
        # Truncate overview if too long
        if [[ ${#overview} -gt 150 ]]; then
            overview="${overview:0:150}..."
        fi
        
        # Determine status class
        local status_class="status-${status,,}"
        
        # Determine release date to display
        local display_date="$digital_date"
        if [[ -z "$display_date" || "$display_date" == "null" ]]; then
            display_date="$theater_date"
        fi
        if [[ -z "$display_date" || "$display_date" == "null" ]]; then
            display_date="TBD"
        fi
        
        # Determine if card should be clickable
        local card_class="movie-card"
        local card_onclick=""
        if [[ -n "$OMBI_SITE_URL" && -n "$movie_id" && "$movie_id" != "null" ]]; then
            card_class="movie-card clickable"
            card_onclick="onclick=\"window.open('$OMBI_SITE_URL/details/movie/$movie_id', '_blank')\""
        fi
        
        # Default poster if none available
        if [[ -z "$poster_url" || "$poster_url" == "null" ]]; then
            poster_url='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQ1MCIgdmlld0JveD0iMCAwIDMwMCA0NTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNDUwIiBmaWxsPSIjRjhGOUZBIi8+CjxwYXRoIGQ9Ik0xNTAgMjI1QzE2NS4xNTUgMjI1IDE3Ny41IDIxMi42NTUgMTc3LjUgMTk3LjVDMTc3LjUgMTgyLjM0NSAxNjUuMTU1IDE3MCAxNTAgMTcwQzEzNC44NDUgMTcwIDEyMi41IDE4Mi4zNDUgMTIyLjUgMTk3LjVDMTIyLjUgMjEyLjY1NSAxMzQuODQ1IDIyNSAxNTAgMjI1WiIgZmlsbD0iI0RFRTJFNiIvPgo8cGF0aCBkPSJNMTg3LjUgMjU1SDE2Mi41VjI4MEgxMzcuNVYyNTVIMTEyLjVWMjMwSDE4Ny41VjI1NVoiIGZpbGw9IiNERUUyRTYiLz4KPC9zdmc+'
        fi
        
        cat >> "$output_file" << EOF
            <div class="$card_class" $card_onclick>
                <img src="$poster_url" alt="$title poster" class="movie-poster" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQ1MCIgdmlld0JveD0iMCAwIDMwMCA0NTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNDUwIiBmaWxsPSIjRjhGOUZBIi8+CjxwYXRoIGQ9Ik0xNTAgMjI1QzE2NS4xNTUgMjI1IDE3Ny41IDIxMi42NTUgMTc3LjUgMTk3LjVDMTc3LjUgMTgyLjM0NSAxNjUuMTU1IDE3MCAxNTAgMTcwQzEzNC44NDUgMTcwIDEyMi41IDE4Mi4zNDUgMTIyLjUgMTk3LjVDMTIyLjUgMjEyLjY1NSAxMzQuODQ1IDIyNSAxNTAgMjI1WiIgZmlsbD0iI0RFRTJFNiIvPgo8cGF0aCBkPSJNMTg3LjUgMjU1SDE2Mi41VjI4MEgxMzcuNVYyNTVIMTEyLjVWMjMwSDE4Ny41VjI1NVoiIGZpbGw9IiNERUUyRTYiLz4KPC9zdmc+'">
                <div class="movie-info">
                    <h3 class="movie-title">$title</h3>
                    <div class="movie-details">
                        <div class="detail-row">
                            <span class="detail-label">Theater Date:</span>
                            <span class="detail-value">$theater_date</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Digital Date:</span>
                            <span class="detail-value">$digital_date</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Downloadable:</span>
                            <span class="status-badge $status_class">$status</span>
                        </div>
                    </div>
                    <p style="margin-top: 15px; color: #6c757d; font-size: 0.9em; line-height: 1.4;">$overview</p>
                </div>
            </div>
EOF
    done

    cat >> "$output_file" << EOF
        </div>
        
        <div class="footer">
            <p>Generated by ombicheck.sh | Data from Vuniper & The Movie Database (TMDb) | <a href="https://github.com/WilmeRWubS/OmbiChecker" target="_blank" rel="noopener noreferrer">https://github.com/WilmeRWubS/OmbiChecker</a></p>
        </div>
    </div>
</body>
</html>
EOF

    echo -e "${GREEN}HTML report generated: $output_file${NC}"
}

# Function to display help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -f, --file FILE         Input file with movie titles (one per line)
    -d, --database PATH     Extract movies from Ombi database
    -t, --include-tv        Include TV shows when extracting from database
    -u, --unavailable-only  Only process unavailable items from database
    -c, --custom-dates FILE Custom digital release dates file
    -o, --output FILE       Output HTML file (default: movie_report.html)
    -h, --help             Show this help message

Examples:
    $0 -f movies.txt
    $0 -d /path/to/ombi.db -u
    $0 -f movies.txt -c custom_dates.txt -o my_report.html

Custom dates file format:
    Movie Title MONTH DAY
    Movie Title MONTH DAY, YEAR
    
    Example:
    Wicked November 22
    Moana 2 November 27, 2024
EOF
}

# Function to parse command line arguments and run the script
main() {
    local input_file=""
    local database_path=""
    local output_file="$OUTPUT_FILE"  # Use config default
    local include_tv="$INCLUDE_TV_SHOWS"  # Use config default
    local filter_unavailable="$FILTER_UNAVAILABLE"  # Use config default
    local custom_dates_file="$DIGITAL_DATES_FILE"  # Use config default
    
    # If no arguments provided, use configuration defaults
    if [[ $# -eq 0 ]]; then
        if [[ "$USE_OMBI_DB" == "yes" && -n "$OMBI_DB_PATH" ]]; then
            database_path="$OMBI_DB_PATH"
            echo -e "${BLUE}Using database mode with config defaults${NC}"
        elif [[ -n "$INPUT_FILE" ]]; then
            input_file="$INPUT_FILE"
            echo -e "${BLUE}Using file mode with config defaults${NC}"
        else
            echo -e "${RED}Error: No input source configured. Please set INPUT_FILE or OMBI_DB_PATH in the script configuration.${NC}"
            usage
            exit 1
        fi
    else
        # Parse command line arguments
        while [[ $# -gt 0 ]]; do
            case $1 in
                -f|--file)
                    input_file="$2"
                    shift 2
                    ;;
                -d|--database)
                    database_path="$2"
                    shift 2
                    ;;
                -o|--output)
                    output_file="$2"
                    shift 2
                    ;;
                -t|--include-tv)
                    include_tv="yes"
                    shift
                    ;;
                -u|--unavailable-only)
                    filter_unavailable="yes"
                    shift
                    ;;
                -c|--custom-dates)
                    custom_dates_file="$2"
                    shift 2
                    ;;
                -h|--help)
                    usage
                    exit 0
                    ;;
                *)
                    echo -e "${RED}Error: Unknown option $1${NC}"
                    usage
                    exit 1
                    ;;
            esac
        done
    fi
    
    # Validate that we have either input file or database
    if [[ -z "$input_file" && -z "$database_path" ]]; then
        echo -e "${RED}Error: Either input file (-f) or database path (-d) must be specified${NC}"
        usage
        exit 1
    fi
    
    # Set default output file if not specified
    if [[ -z "$output_file" ]]; then
        output_file="movie_report.html"
    fi
    
    # Check dependencies
    check_dependencies
    
    # Load custom digital dates
    load_custom_digital_dates
    
    # Create temporary directory for processing
    local temp_dir="/tmp/ombicheck_$$"
    mkdir -p "$temp_dir"
    local results_file="$temp_dir/results.json"
    
    # Initialize results file
    echo "[]" > "$results_file"
    
    # Process movies
    local movies=()
    
    if [[ -n "$database_path" ]]; then
        echo -e "${BLUE}Extracting movies from database: $database_path${NC}"
        mapfile -t movies < <(extract_from_database "$database_path" "$include_tv" "$filter_unavailable")
    else
        echo -e "${BLUE}Reading movies from file: $input_file${NC}"
        if [[ ! -f "$input_file" ]]; then
            echo -e "${RED}Error: Input file not found: $input_file${NC}"
            exit 1
        fi
        mapfile -t movies < "$input_file"
    fi
    
    if [[ ${#movies[@]} -eq 0 ]]; then
        echo -e "${YELLOW}No movies found to process${NC}"
        exit 0
    fi
    
    echo -e "${BLUE}Processing ${#movies[@]} movies...${NC}"
    
    # Process each movie
    local processed_results=()
    for movie in "${movies[@]}"; do
        if [[ -n "$movie" ]]; then
            echo -e "${YELLOW}➤ Processing: $movie${NC}"
            local result
            result=$(process_movie "$movie" "$custom_dates_file")

            # Gebruik een here-string om echo-artefacten te vermijden
            if jq empty <<< "$result" 2>/dev/null; then
                processed_results+=("$result")
            else
                echo -e "${RED}⚠ Ongeldig JSON-result voor '$movie'. Overgeslagen.${NC}"
                echo "$result"
            fi
        fi
    done
    
    # Combine all results into JSON array
    printf '%s\n' "${processed_results[@]}" | jq -s '.' > "$results_file"
    
    # Generate HTML report
    generate_html_report "$results_file" "$output_file"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    echo -e "${GREEN}Processing complete!${NC}"
    echo -e "${BLUE}Results saved to: $output_file${NC}"
}

# Run main function with all arguments
main "$@"