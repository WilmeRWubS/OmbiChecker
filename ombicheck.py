import requests
import tkinter as tk
from tkinter import scrolledtext, ttk
import re
from datetime import datetime

# Your TMDb Bearer Token
TMDB_BEARER_TOKEN = "enterhere"

HEADERS = {
    "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
    "accept": "application/json"
}

RELEASE_TYPE_MAP = {
    1: "Premiere",
    2: "Theatrical (Limited)",
    3: "Theatrical",
    4: "Digital",
    5: "Physical"
}

VALID_TYPES = [4, 5]  # Only count Digital or Physical releases

# Global variable to store movie results for sorting
movie_results = []

def search_movie(title):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {"query": title}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if data.get("results"):
        return data["results"][0]["id"]
    return None

def get_valid_release(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/release_dates"
    response = requests.get(url, headers=HEADERS)
    release_data = response.json()
    
    # Look for the earliest valid release
    earliest_release = None
    
    for country in release_data.get("results", []):
        for release in country.get("release_dates", []):
            release_type = release.get("type")
            if release_type in VALID_TYPES:
                release_date = release.get("release_date", "")
                if release_date:
                    # Take only the date part (first 10 characters)
                    release_date = release_date[:10]
                
                current_release = {
                    "type": RELEASE_TYPE_MAP.get(release_type, "Other"),
                    "date": release_date
                }
                
                # If we don't have a release yet, or this one is earlier
                if earliest_release is None:
                    earliest_release = current_release
                elif release_date and (not earliest_release["date"] or release_date < earliest_release["date"]):
                    earliest_release = current_release
    
    return earliest_release

def determine_downloadable_status(release_info):
    """Determine downloadable status based on release info."""
    if not release_info:
        return "No"
    
    release_date = release_info.get("date", "")
    
    if not release_date:
        return "TBD"
    
    try:
        # Parse the release date
        release_datetime = datetime.strptime(release_date, "%Y-%m-%d")
        current_datetime = datetime.now()
        
        if release_datetime <= current_datetime:
            return "Yes"
        else:
            return "Soon"
    except ValueError:
        # If date parsing fails
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
    """Display the results in the output text widget."""
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    
    output_text.insert(tk.END, f"{'Title':<45} | {'Type':<10} | {'Release Date':<12} | Downloadable?\n")
    output_text.insert(tk.END, "-" * 90 + "\n")
    
    for result in results:
        output_text.insert(tk.END, f"{result['title']:<45} | {result['type']:<10} | {result['date']:<12} | {result['status']}\n")
    
    output_text.config(state=tk.DISABLED)

def sort_results():
    """Sort the results based on the selected criteria."""
    if not movie_results:
        return
    
    sort_by = sort_var.get()
    
    if sort_by == "Title":
        sorted_results = sorted(movie_results, key=lambda x: x['title'].lower())
    elif sort_by == "Type":
        sorted_results = sorted(movie_results, key=lambda x: x['type'])
    elif sort_by == "Release Date":
        def date_sort_key(x):
            if x['date'] == "TBD" or x['date'] == "-":
                return "9999-12-31"  # Put TBD/missing dates at the end
            return x['date']
        sorted_results = sorted(movie_results, key=date_sort_key)
    elif sort_by == "Downloadable":
        # Sort by downloadable status: Yes, Soon, TBD, No
        status_order = {"Yes": 1, "Soon": 2, "TBD": 3, "No": 4}
        sorted_results = sorted(movie_results, key=lambda x: status_order.get(x['status'], 5))
    else:
        sorted_results = movie_results
    
    display_results(sorted_results)

def check_movies():
    global movie_results
    movie_results = []
    
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.config(state=tk.DISABLED)
    
    lines = input_text.get("1.0", tk.END).strip().split('\n')

    if not lines:
        output_text.config(state=tk.NORMAL)
        output_text.insert(tk.END, "Please paste some movie data.\n")
        output_text.config(state=tk.DISABLED)
        return

    for line in lines:
        title = extract_title(line)
        if not title:
            continue
        movie_id = search_movie(title)
        if not movie_id:
            movie_results.append({
                'title': title,
                'type': 'Not Found',
                'date': '-',
                'status': '-'
            })
            continue
        
        release_info = get_valid_release(movie_id)
        downloadable_status = determine_downloadable_status(release_info)
        
        if release_info:
            release_type = release_info['type']
            release_date = release_info['date'] if release_info['date'] else "TBD"
            movie_results.append({
                'title': title,
                'type': release_type,
                'date': release_date,
                'status': downloadable_status
            })
        else:
            movie_results.append({
                'title': title,
                'type': '-',
                'date': 'TBD',
                'status': 'No'
            })
    
    display_results(movie_results)

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
tk.Button(controls_frame, text="Sort", command=sort_results).pack(side=tk.LEFT)

tk.Label(window, text="Results:").pack(anchor='w', padx=10)
output_text = scrolledtext.ScrolledText(window, height=15, width=110, state=tk.DISABLED)
output_text.pack(padx=10, pady=5)

window.mainloop()