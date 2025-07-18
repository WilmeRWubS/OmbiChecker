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
    echo "    -i INPUT_FILE    Input file with movie list (one movie per line)"
    echo "    -o OUTPUT_FILE   Output HTML file path"
    echo ""
    echo "  Ombi Database mode:"
    echo "    -d DATABASE_PATH Path to Ombi.db file (default: /opt/Ombi/Ombi.db)"
    echo "    -o OUTPUT_FILE   Output HTML file path"
    echo "    --ombi           Use Ombi database instead of input file"
    echo "    --include-tv     Include TV shows from Ombi database"
    echo "    --all-requests   Include all requests (not just unavailable ones)"
    echo ""
    echo "Optional:"
    echo "  -t TOKEN         TMDb Bearer Token (overrides config)"
    echo "  -l LANGUAGE      Language code (default: nl-NL)"
    echo "  -u URL           Ombi site URL"
    echo "  -b URL           Custom background image URL"
    echo "  -h               Show this help"
    echo ""
    echo "Examples:"
    echo "  File mode:     $0 -i movies.txt -o report.html"
    echo "  Ombi mode:     $0 --ombi -o report.html"
    echo "  Ombi with TV:  $0 --ombi --include-tv -o report.html"
}

check_dependencies() {
    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [[ "$USE_OMBI_DB" == "yes" ]] && ! command -v sqlite3 &> /dev/null; then
        missing_deps+=("sqlite3")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}Error: Missing required dependencies: ${missing_deps[*]}${NC}"
        echo "Please install the missing dependencies and try again."
        exit 1
    fi
}

extract_movies_from_ombi() {
    echo -e "${BLUE}Extracting movies from Ombi database...${NC}"
    
    if [[ ! -f "$OMBI_DB_PATH" ]]; then
        echo -e "${RED}Error: Ombi database not found at $OMBI_DB_PATH${NC}"
        exit 1
    fi
    
    # Check if sqlite3 is available
    if ! command -v sqlite3 &> /dev/null; then
        echo -e "${RED}Error: sqlite3 is required but not installed${NC}"
        exit 1
    fi
    
    local where_clause=""
    if [[ "$FILTER_UNAVAILABLE" == "yes" ]]; then
        where_clause="WHERE Available = 0 AND (Denied IS NULL OR Denied = 0)"
    else
        where_clause="WHERE (Denied IS NULL OR Denied = 0)"
    fi
    
    # Extract movies from MovieRequests table
    local movie_query="SELECT Title, TheMovieDbId FROM MovieRequests $where_clause;"
    
    echo -e "  Querying MovieRequests table..."
    sqlite3 "$OMBI_DB_PATH" "$movie_query" | while IFS='|' read -r title tmdb_id; do
        if [[ -n "$title" && -n "$tmdb_id" ]]; then
            echo "$title|$tmdb_id|movie" >> /tmp/ombi_requests.txt
        fi
    done
    
    # Extract TV shows if requested
    if [[ "$INCLUDE_TV_SHOWS" == "yes" ]]; then
        echo -e "  Querying TvRequests table..."
        # Note: TvRequests uses TvDbId, not TheMovieDbId, so we'll need to handle this differently
        local tv_query="SELECT Title, TvDbId FROM TvRequests;"
        
        sqlite3 "$OMBI_DB_PATH" "$tv_query" | while IFS='|' read -r title tvdb_id; do
            if [[ -n "$title" && -n "$tvdb_id" ]]; then
                echo "$title|$tvdb_id|tv" >> /tmp/ombi_requests.txt
            fi
        done
    fi
    
    local total_count=$(wc -l < /tmp/ombi_requests.txt 2>/dev/null || echo "0")
    echo -e "${GREEN}  Extracted $total_count items from Ombi database${NC}"
}

search_tv_show() {
    local title="$1"
    local encoded_title=$(echo "$title" | sed 's/ /%20/g' | sed 's/&/%26/g')
    
    local response=$(curl -s -H "Authorization: Bearer $TMDB_BEARER_TOKEN" \
        -H "accept: application/json" \
        "https://api.themoviedb.org/3/search/tv?query=$encoded_title&language=$HTML_LANGUAGE")
    
    echo "$response"
}

get_tv_show_details() {
    local tv_id="$1"
    
    local response=$(curl -s -H "Authorization: Bearer $TMDB_BEARER_TOKEN" \
        -H "accept: application/json" \
        "https://api.themoviedb.org/3/tv/$tv_id?language=$HTML_LANGUAGE")
    
    echo "$response"
}

# Function to extract movie title from line
extract_title() {
    local line="$1"
    # Remove everything after first parenthesis
    echo "$line" | sed 's/\s*(.*//' | sed 's/\t.*//' | xargs
}

# Function to search movie via TMDb API
search_movie() {
    local title="$1"
    local encoded_title=$(echo "$title" | sed 's/ /%20/g' | sed 's/&/%26/g')
    
    local response=$(curl -s -H "Authorization: Bearer $TMDB_BEARER_TOKEN" \
        -H "accept: application/json" \
        "https://api.themoviedb.org/3/search/movie?query=$encoded_title&language=$HTML_LANGUAGE")
    
    echo "$response"
}

# Function to get release dates for a movie
get_release_dates() {
    local movie_id="$1"
    
    local response=$(curl -s -H "Authorization: Bearer $TMDB_BEARER_TOKEN" \
        -H "accept: application/json" \
        "https://api.themoviedb.org/3/movie/$movie_id/release_dates")
    
    echo "$response"
}

# Function to determine downloadable status
determine_status() {
    local release_date="$1"
    
    if [[ -z "$release_date" || "$release_date" == "null" ]]; then
        echo "TBD"
        return
    fi
    
    local current_date=$(date +%Y-%m-%d)
    
    if [[ "$release_date" < "$current_date" ]] || [[ "$release_date" == "$current_date" ]]; then
        echo "Yes"
    else
        echo "Soon"
    fi
}

# Function to generate HTML content
generate_html() {
    local current_date=$(date '+%Y-%m-%d %H:%M')
    local total_movies=0
    local available_now=0
    local coming_soon=0
    local not_available=0
    
    # Count movies by status
    while IFS='|' read -r title type date status poster_url overview movie_id; do
        ((total_movies++))
        case "$status" in
            "Yes") ((available_now++)) ;;
            "Soon") ((coming_soon++)) ;;
            *) ((not_available++)) ;;
        esac
    done < /tmp/movie_results.txt
    
    # Determine background style
    local background_style=""
    local overlay_style=""
    
    if [[ "$USE_CUSTOM_BACKGROUND" == "yes" && -n "$CUSTOM_BACKGROUND_URL" ]]; then
        background_style="background: url('$CUSTOM_BACKGROUND_URL') center center fixed; background-size: cover;"
        overlay_style="body::before { content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.3); z-index: -1; }"
    else
        background_style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
    fi
    
    cat > "$OUTPUT_FILE" << EOF
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
    while IFS='|' read -r title type date status poster_url overview movie_id; do
        local status_class="status-${status,,}"
        local card_class="movie-card"
        local card_onclick=""
        
        if [[ -n "$OMBI_SITE_URL" && -n "$movie_id" && "$movie_id" != "null" ]]; then
            card_class="movie-card clickable"
            card_onclick="onclick=\"window.open('$OMBI_SITE_URL/details/movie/$movie_id', '_blank')\""
        fi
        
        # Truncate overview if too long
        if [[ ${#overview} -gt 150 ]]; then
            overview="${overview:0:150}..."
        fi
        
        # Use default poster if empty
        if [[ -z "$poster_url" || "$poster_url" == "null" ]]; then
            poster_url='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQ1MCIgdmlld0JveD0iMCAwIDMwMCA0NTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNDUwIiBmaWxsPSIjRjhGOUZBIi8+CjxwYXRoIGQ9Ik0xNTAgMjI1QzE2NS4xNTUgMjI1IDE3Ny41IDIxMi42NTUgMTc3LjUgMTk3LjVDMTc3LjUgMTgyLjM0NSAxNjUuMTU1IDE3MCAxNTAgMTcwQzEzNC44NDUgMTcwIDEyMi41IDE4Mi4zNDUgMTIyLjUgMTk3LjVDMTIyLjUgMjEyLjY1NSAxMzQuODQ1IDIyNSAxNTAgMjI1WiIgZmlsbD0iI0RFRTJFNiIvPgo8cGF0aCBkPSJNMTg3LjUgMjU1SDE2Mi41VjI4MEgxMzcuNVYyNTVIMTEyLjVWMjMwSDE4Ny41VjI1NVoiIGZpbGw9IiNERUUyRTYiLz4KPC9zdmc+'
        fi
        
                cat >> "$OUTPUT_FILE" << EOF
            <div class="$card_class" $card_onclick>
                <img src="$poster_url" alt="$title poster" class="movie-poster" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQ1MCIgdmlld0JveD0iMCAwIDMwMCA0NTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNDUwIiBmaWxsPSIjRjhGOUZBIi8+CjxwYXRoIGQ9Ik0xNTAgMjI1QzE2NS4xNTUgMjI1IDE3Ny41IDIxMi42NTUgMTc3LjUgMTk3LjVDMTc3LjUgMTgyLjM0NSAxNjUuMTU1IDE3MCAxNTAgMTcwQzEzNC44NDUgMTcwIDEyMi41IDE4Mi4zNDUgMTIyLjUgMTk3LjVDMTIyLjUgMjEyLjY1NSAxMzQuODQ1IDIyNSAxNTAgMjI1WiIgZmlsbD0iI0RFRTJFNiIvPgo8cGF0aCBkPSJNMTg3LjUgMjU1SDE2Mi41VjI4MEgxMzcuNVYyNTVIMTEyLjVWMjMwSDE4Ny41VjI1NVoiIGZpbGw9IiNERUUyRTYiLz4KPC9zdmc+'">
                <div class="movie-info">
                    <h3 class="movie-title">$title</h3>
                    <div class="movie-details">
                        <div class="detail-row">
                            <span class="detail-label">Release Type:</span>
                            <span class="detail-value">$type</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Release Date:</span>
                            <span class="detail-value">$date</span>
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
    done < /tmp/movie_results.txt

    cat >> "$OUTPUT_FILE" << EOF
        </div>
        
        <div class="footer">
            <p>Generated by ombicheck.sh | Data from The Movie Database (TMDb) | <a href="https://github.com/WilmeRWubS/OmbiChecker" target="_blank" rel="noopener noreferrer">https://github.com/WilmeRWubS/OmbiChecker</a></p>
        </div>
    </div>
</body>
</html>
EOF
}

# Function to process movies
process_movies() {
    if [[ "$USE_OMBI_DB" == "yes" ]]; then
        process_ombi_requests
    else
        process_file_input
    fi
}

process_file_input() {
    echo -e "${BLUE}Processing movies from $INPUT_FILE...${NC}"
    
    # Clear temporary results file
    > /tmp/movie_results.txt
    
    local count=0
    local total=$(wc -l < "$INPUT_FILE")
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        ((count++))
        
        # Skip empty lines
        [[ -z "$line" ]] && continue
        
        echo -e "${YELLOW}[$count/$total] Processing: $line${NC}"
        
        local title=$(extract_title "$line")
        
        if [[ -z "$title" ]]; then
            echo -e "${RED}  ✗ Could not extract title${NC}"
            continue
        fi
        
        echo -e "  Searching for: $title"
        
        # Search for movie
        local search_result=$(search_movie "$title")
        
        if [[ -z "$search_result" || "$search_result" == "null" ]]; then
            echo -e "${RED}  ✗ Movie not found in TMDb${NC}"
            echo "$title|Not Found|-|No||Movie not found in TMDb database.|null" >> /tmp/movie_results.txt
            continue
        fi
        
        # Extract movie data using jq
        local movie_id=$(echo "$search_result" | jq -r '.results[0].id // "null"')
        local poster_path=$(echo "$search_result" | jq -r '.results[0].poster_path // ""')
        local overview=$(echo "$search_result" | jq -r '.results[0].overview // "No description available."' | sed 's/|/;/g')
        
        if [[ "$movie_id" == "null" ]]; then
            echo -e "${RED}  ✗ Invalid movie data${NC}"
            echo "$title|Not Found|-|No||Movie not found in TMDb database.|null" >> /tmp/movie_results.txt
            continue
        fi
        
        # Build poster URL
        local poster_url=""
        if [[ -n "$poster_path" && "$poster_path" != "null" ]]; then
            poster_url="https://image.tmdb.org/t/p/w500$poster_path"
        fi
        
        echo -e "  Getting release dates..."
        
        # Get release dates
        local release_data=$(get_release_dates "$movie_id")
        
        # Parse release data to find earliest digital/physical release
        local earliest_date=""
        local release_type="TBD"
        
        if [[ -n "$release_data" && "$release_data" != "null" ]]; then
            # Extract digital (type 4) and physical (type 5) releases
            local digital_dates=$(echo "$release_data" | jq -r '.results[].release_dates[] | select(.type == 4) | .release_date' 2>/dev/null | head -10)
            local physical_dates=$(echo "$release_data" | jq -r '.results[].release_dates[] | select(.type == 5) | .release_date' 2>/dev/null | head -10)
            
            # Find earliest date
            for date in $digital_dates $physical_dates; do
                if [[ -n "$date" && "$date" != "null" ]]; then
                    # Extract just the date part (first 10 characters)
                    date="${date:0:10}"
                    if [[ -z "$earliest_date" || "$date" < "$earliest_date" ]]; then
                        earliest_date="$date"
                        # Determine if it's digital or physical
                        if echo "$digital_dates" | grep -q "$date"; then
                            release_type="Digital"
                        else
                            release_type="Physical"
                        fi
                    fi
                fi
            done
        fi
        
        # Determine status
        local status=$(determine_status "$earliest_date")
        
        # Format date for display
        local display_date="TBD"
        if [[ -n "$earliest_date" ]]; then
            display_date="$earliest_date"
        fi
        
        echo -e "${GREEN}  ✓ $title - $release_type ($display_date) - $status${NC}"
        
        # Save to results file
        echo "$title|$release_type|$display_date|$status|$poster_url|$overview|$movie_id" >> /tmp/movie_results.txt
        
        # Small delay to be nice to the API
        sleep 0.1
        
    done < "$INPUT_FILE"
    
    echo -e "${GREEN}Processing complete!${NC}"
}

process_ombi_requests() {
    echo -e "${BLUE}Processing requests from Ombi database...${NC}"
    
    # Clear temporary results file
    > /tmp/movie_results.txt
    
    # Extract requests from Ombi database
    extract_movies_from_ombi
    
    if [[ ! -f /tmp/ombi_requests.txt ]]; then
        echo -e "${RED}No requests found in Ombi database${NC}"
        return
    fi
    
    local count=0
    local total=$(wc -l < /tmp/ombi_requests.txt)
    
    while IFS='|' read -r title external_id media_type; do
        ((count++))
        
        # Skip empty lines
        [[ -z "$title" ]] && continue
        
        echo -e "${YELLOW}[$count/$total] Processing: $title ($media_type)${NC}"
        
        local tmdb_id=""
        local search_result=""
        local poster_path=""
        local overview=""
        
        if [[ "$media_type" == "movie" ]]; then
            # For movies, we already have the TMDb ID
            tmdb_id="$external_id"
            
            # Get movie details directly
            search_result=$(curl -s -H "Authorization: Bearer $TMDB_BEARER_TOKEN" \
                -H "accept: application/json" \
                "https://api.themoviedb.org/3/movie/$tmdb_id?language=$HTML_LANGUAGE")
            
            if [[ -n "$search_result" && "$search_result" != "null" ]]; then
                poster_path=$(echo "$search_result" | jq -r '.poster_path // ""')
                overview=$(echo "$search_result" | jq -r '.overview // "No description available."' | sed 's/|/;/g')
            fi
            
        elif [[ "$media_type" == "tv" ]]; then
            # For TV shows, we need to search by title since we have TvDbId, not TMDb ID
            echo -e "  Searching for TV show: $title"
            search_result=$(search_tv_show "$title")
            
            if [[ -n "$search_result" && "$search_result" != "null" ]]; then
                tmdb_id=$(echo "$search_result" | jq -r '.results[0].id // "null"')
                poster_path=$(echo "$search_result" | jq -r '.results[0].poster_path // ""')
                overview=$(echo "$search_result" | jq -r '.results[0].overview // "No description available."' | sed 's/|/;/g')
            fi
        fi
        
        if [[ -z "$tmdb_id" || "$tmdb_id" == "null" ]]; then
            echo -e "${RED}  ✗ Could not find TMDb ID for $title${NC}"
            echo "$title|Not Found|-|No||$media_type not found in TMDb database.|null" >> /tmp/movie_results.txt
            continue
        fi
        
        # Build poster URL
        local poster_url=""
        if [[ -n "$poster_path" && "$poster_path" != "null" ]]; then
            poster_url="https://image.tmdb.org/t/p/w500$poster_path"
        fi
        
        if [[ "$media_type" == "movie" ]]; then
            echo -e "  Getting release dates..."
            
            # Get release dates for movies
            local release_data=$(get_release_dates "$tmdb_id")
            
            # Parse release data to find earliest digital/physical release
            local earliest_date=""
            local release_type="TBD"
            
            if [[ -n "$release_data" && "$release_data" != "null" ]]; then
                # Extract digital (type 4) and physical (type 5) releases
                local digital_dates=$(echo "$release_data" | jq -r '.results[].release_dates[] | select(.type == 4) | .release_date' 2>/dev/null | head -10)
                local physical_dates=$(echo "$release_data" | jq -r '.results[].release_dates[] | select(.type == 5) | .release_date' 2>/dev/null | head -10)
                
                # Find earliest date
                for date in $digital_dates $physical_dates; do
                    if [[ -n "$date" && "$date" != "null" ]]; then
                        # Extract just the date part (first 10 characters)
                        date="${date:0:10}"
                        if [[ -z "$earliest_date" || "$date" < "$earliest_date" ]]; then
                            earliest_date="$date"
                            # Determine if it's digital or physical
                            if echo "$digital_dates" | grep -q "$date"; then
                                release_type="Digital"
                            else
                                release_type="Physical"
                            fi
                        fi
                    fi
                done
            fi
            
            # Determine status
            local status=$(determine_status "$earliest_date")
            
            # Format date for display
            local display_date="TBD"
            if [[ -n "$earliest_date" ]]; then
                display_date="$earliest_date"
            fi
            
            echo -e "${GREEN}  ✓ $title - $release_type ($display_date) - $status${NC}"
            
            # Save to results file
            echo "$title|$release_type|$display_date|$status|$poster_url|$overview|$tmdb_id" >> /tmp/movie_results.txt
            
        elif [[ "$media_type" == "tv" ]]; then
            # For TV shows, get air date from details
            echo -e "  Getting TV show details..."
            
            local tv_details=$(get_tv_show_details "$tmdb_id")
            local first_air_date=""
            local last_air_date=""
            local status_text=""
            
            if [[ -n "$tv_details" && "$tv_details" != "null" ]]; then
                first_air_date=$(echo "$tv_details" | jq -r '.first_air_date // ""')
                last_air_date=$(echo "$tv_details" | jq -r '.last_air_date // ""')
                status_text=$(echo "$tv_details" | jq -r '.status // ""')
            fi
            
            # Determine TV show status
            local tv_status="TBD"
            local display_date="TBD"
            local release_type="TV Series"
            
            if [[ -n "$first_air_date" && "$first_air_date" != "null" ]]; then
                display_date="$first_air_date"
                local current_date=$(date +%Y-%m-%d)
                
                if [[ "$first_air_date" < "$current_date" ]] || [[ "$first_air_date" == "$current_date" ]]; then
                    if [[ "$status_text" == "Ended" || "$status_text" == "Canceled" ]]; then
                        tv_status="Yes"
                        release_type="TV Series (Ended)"
                    else
                        tv_status="Soon"
                        release_type="TV Series (Ongoing)"
                    fi
                else
                    tv_status="Soon"
                    release_type="TV Series (Upcoming)"
                fi
            fi
            
            echo -e "${GREEN}  ✓ $title - $release_type ($display_date) - $tv_status${NC}"
            
            # Save to results file
            echo "$title|$release_type|$display_date|$tv_status|$poster_url|$overview|$tmdb_id" >> /tmp/movie_results.txt
        fi
        
        # Small delay to be nice to the API
        sleep 0.1
        
    done < /tmp/ombi_requests.txt
    
    echo -e "${GREEN}Processing complete!${NC}"
}

# Parse command line arguments
while getopts "i:o:t:l:u:b:h" opt; do
    case $opt in
        i) INPUT_FILE="$OPTARG" ;;
        o) OUTPUT_FILE="$OPTARG" ;;
        t) TMDB_BEARER_TOKEN="$OPTARG" ;;
        l) HTML_LANGUAGE="$OPTARG" ;;
        u) OMBI_SITE_URL="$OPTARG" ;;
        b) CUSTOM_BACKGROUND_URL="$OPTARG" ;;
        h) usage; exit 0 ;;
        \?) echo "Invalid option -$OPTARG" >&2; usage; exit 1 ;;
    esac
done

# Handle remaining arguments
shift $((OPTIND-1))
for arg in "$@"; do
    case $arg in
        --ombi)
            USE_OMBI_DB="yes"
            ;;
        --include-tv)
            INCLUDE_TV_SHOWS="yes"
            ;;
        --all-requests)
            FILTER_UNAVAILABLE="no"
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ "$USE_OMBI_DB" == "yes" ]]; then
    # For Ombi mode, only output file is required
    if [[ -z "$OUTPUT_FILE" ]]; then
        echo -e "${RED}Error: Output file is required${NC}"
        usage
        exit 1
    fi
else
    # For file mode, both input and output files are required
    if [[ -z "$INPUT_FILE" || -z "$OUTPUT_FILE" ]]; then
        echo -e "${RED}Error: Input file and output file are required${NC}"
        usage
        exit 1
    fi

    # Check if input file exists
    if [[ ! -f "$INPUT_FILE" ]]; then
        echo -e "${RED}Error: Input file '$INPUT_FILE' not found${NC}"
        exit 1
    fi
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    echo "Please install jq: https://stedolan.github.io/jq/download/"
    exit 1
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is required but not installed${NC}"
    exit 1
fi

main() {
    echo -e "${BLUE}Starting Movie Downloadability Checker...${NC}"

    # Check dependencies
    check_dependencies

    # Validate TMDb token
    if [[ -z "$TMDB_BEARER_TOKEN" || "$TMDB_BEARER_TOKEN" == "enterhere" ]]; then
        echo -e "${RED}Error: Please set a valid TMDb Bearer Token${NC}"
        exit 1
    fi

    # Create temporary directory
    mkdir -p /tmp

    # Clean up temporary files
    rm -f /tmp/movie_results.txt /tmp/ombi_requests.txt

    # Process movies
    process_movies

    # Check if we have results
    if [[ ! -f /tmp/movie_results.txt ]] || [[ ! -s /tmp/movie_results.txt ]]; then
        echo -e "${RED}No results to generate HTML report${NC}"
        exit 1
    fi

    # Generate HTML report
    echo -e "${BLUE}Generating HTML report...${NC}"
    generate_html

    echo -e "${GREEN}HTML report generated: $OUTPUT_FILE${NC}"

    # Clean up
    rm -f /tmp/movie_results.txt /tmp/ombi_requests.txt
}

# Run main function
main "$@"

# Optional: Open the HTML file in default browser (uncomment if desired)
# if command -v xdg-open &> /dev/null; then
#     xdg-open "$OUTPUT_FILE"
# elif command -v open &> /dev/null; then
#     open "$OUTPUT_FILE"
# fi