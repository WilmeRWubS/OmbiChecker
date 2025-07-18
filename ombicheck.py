import requests
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox
import re
from datetime import datetime
import os

# Your TMDb Bearer Token
TMDB_BEARER_TOKEN = "enterhere"

# Configuration for HTML customization
USE_CUSTOM_BACKGROUND = "yes"  # "yes" or "no"
CUSTOM_BACKGROUND_URL = "https://i.imgur.com/9QY51tm.jpeg"  # URL to background image
HTML_LANGUAGE = "nl-NL"  # Language code for TMDb API (e.g., "en-US", "es-ES", "fr-FR", "de-DE")

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
    params = {
        "query": title,
        "language": HTML_LANGUAGE
    }
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if data.get("results"):
        return data["results"][0]  # Return full movie data instead of just ID
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

def open_settings_window():
    """Open a settings window for HTML customization."""
    global USE_CUSTOM_BACKGROUND, CUSTOM_BACKGROUND_URL, HTML_LANGUAGE
    
    settings_window = tk.Toplevel(window)
    settings_window.title("HTML Report Settings")
    settings_window.geometry("500x300")
    settings_window.resizable(False, False)
    
    # Make window modal
    settings_window.transient(window)
    settings_window.grab_set()
    
    # Center the window
    settings_window.update_idletasks()
    x = (settings_window.winfo_screenwidth() // 2) - (500 // 2)
    y = (settings_window.winfo_screenheight() // 2) - (300 // 2)
    settings_window.geometry(f"500x300+{x}+{y}")
    
    # Custom Background Section
    bg_frame = tk.LabelFrame(settings_window, text="Custom Background", padx=10, pady=10)
    bg_frame.pack(fill="x", padx=10, pady=10)
    
    use_bg_var = tk.StringVar(value=USE_CUSTOM_BACKGROUND)
    tk.Label(bg_frame, text="Use Custom Background:").grid(row=0, column=0, sticky="w", pady=5)
    bg_combo = ttk.Combobox(bg_frame, textvariable=use_bg_var, values=["no", "yes"], 
                           state="readonly", width=10)
    bg_combo.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
    
    tk.Label(bg_frame, text="Background Image URL:").grid(row=1, column=0, sticky="w", pady=5)
    bg_url_var = tk.StringVar(value=CUSTOM_BACKGROUND_URL)
    bg_url_entry = tk.Entry(bg_frame, textvariable=bg_url_var, width=50)
    bg_url_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
    
    tk.Label(bg_frame, text="(Must be a direct link to an image file)", 
             font=("Arial", 8), fg="gray").grid(row=2, column=1, columnspan=2, sticky="w", padx=(10, 0))
    
    # Language Section
    lang_frame = tk.LabelFrame(settings_window, text="Language Settings", padx=10, pady=10)
    lang_frame.pack(fill="x", padx=10, pady=10)
    
    tk.Label(lang_frame, text="TMDb Language:").grid(row=0, column=0, sticky="w", pady=5)
    lang_var = tk.StringVar(value=HTML_LANGUAGE)
    lang_combo = ttk.Combobox(lang_frame, textvariable=lang_var, width=15,
                             values=["en-US", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", 
                                   "ja-JP", "ko-KR", "zh-CN", "ru-RU", "nl-NL", "sv-SE"])
    lang_combo.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
    
    tk.Label(lang_frame, text="(Affects movie descriptions and some metadata)", 
             font=("Arial", 8), fg="gray").grid(row=1, column=1, sticky="w", padx=(10, 0))
    
    # Buttons
    button_frame = tk.Frame(settings_window)
    button_frame.pack(fill="x", padx=10, pady=20)
    
    def save_settings():
        global USE_CUSTOM_BACKGROUND, CUSTOM_BACKGROUND_URL, HTML_LANGUAGE
        USE_CUSTOM_BACKGROUND = use_bg_var.get()
        CUSTOM_BACKGROUND_URL = bg_url_var.get()
        HTML_LANGUAGE = lang_var.get()
        messagebox.showinfo("Settings Saved", "Settings have been saved successfully!")
        settings_window.destroy()
    
    def cancel_settings():
        settings_window.destroy()
    
    tk.Button(button_frame, text="Save", command=save_settings, 
              bg="#28a745", fg="white", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=(5, 0))
    tk.Button(button_frame, text="Cancel", command=cancel_settings).pack(side=tk.RIGHT)

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
        }}
        .movie-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        .movie-poster {{
            width: 100%;
            height: 400px;
            object-fit: cover;
            background: #f8f9fa;
        }}
        .movie-info {{
            padding: 20px;
        }}
        .movie-title {{
            font-size: 1.3em;
            font-weight: bold;
            margin: 0 0 10px 0;
            color: #2c3e50;
            line-height: 1.3;
        }}
        .movie-details {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .detail-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .detail-label {{
            font-weight: 600;
            color: #6c757d;
            font-size: 0.9em;
        }}
        .detail-value {{
            font-weight: 500;
        }}
        .status-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .status-yes {{
            background: #d4edda;
            color: #155724;
        }}
        .status-soon {{
            background: #fff3cd;
            color: #856404;
        }}
        .status-no {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-tbd {{
            background: #e2e3e5;
            color: #383d41;
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
                <div class="stat-number">{len([m for m in movie_results if m['status'] == 'Yes'])}</div>
                <div class="stat-label">Available Now</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len([m for m in movie_results if m['status'] == 'Soon'])}</div>
                <div class="stat-label">Coming Soon</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len([m for m in movie_results if m['status'] in ['No', 'TBD']])}</div>
                <div class="stat-label">Not Available</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(movie_results)}</div>
                <div class="stat-label">Total Movies</div>
            </div>
        </div>
        
        <div class="movies-grid">
"""
    
    # Add movie cards
    for movie in movie_results:
        poster_url = movie.get('poster_url', '')
        if not poster_url:
            poster_url = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQ1MCIgdmlld0JveD0iMCAwIDMwMCA0NTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNDUwIiBmaWxsPSIjRjhGOUZBIi8+CjxwYXRoIGQ9Ik0xNTAgMjI1QzE2NS4xNTUgMjI1IDE3Ny41IDIxMi42NTUgMTc3LjUgMTk3LjVDMTc3LjUgMTgyLjM0NSAxNjUuMTU1IDE3MCAxNTAgMTcwQzEzNC44NDUgMTcwIDEyMi41IDE4Mi4zNDUgMTIyLjUgMTk3LjVDMTIyLjUgMjEyLjY1NSAxMzQuODQ1IDIyNSAxNTAgMjI1WiIgZmlsbD0iI0RFRTJFNiIvPgo8cGF0aCBkPSJNMTg3LjUgMjU1SDE2Mi41VjI4MEgxMzcuNVYyNTVIMTEyLjVWMjMwSDE4Ny41VjI1NVoiIGZpbGw9IiNERUUyRTYiLz4KPC9zdmc+'
        
        status_class = f"status-{movie['status'].lower()}"
        
        overview = movie.get('overview', 'No description available.')
        if len(overview) > 150:
            overview = overview[:150] + "..."
        
        html += f"""
            <div class="movie-card">
                <img src="{poster_url}" alt="{movie['title']} poster" class="movie-poster" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQ1MCIgdmlld0JveD0iMCAwIDMwMCA0NTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNDUwIiBmaWxsPSIjRjhGOUZBIi8+CjxwYXRoIGQ9Ik0xNTAgMjI1QzE2NS4xNTUgMjI1IDE3Ny41IDIxMi42NTUgMTc3LjUgMTk3LjVDMTc3LjUgMTgyLjM0NSAxNjUuMTU1IDE3MCAxNTAgMTcwQzEzNC44NDUgMTcwIDEyMi41IDE4Mi4zNDUgMTIyLjUgMTk3LjVDMTIyLjUgMjEyLjY1NSAxMzQuODQ1IDIyNSAxNTAgMjI1WiIgZmlsbD0iI0RFRTJFNiIvPgo8cGF0aCBkPSJNMTg3LjUgMjU1SDE2Mi41VjI4MEgxMzcuNVYyNTVIMTEyLjVWMjMwSDE4Ny41VjI1NVoiIGZpbGw9IiNERUUyRTYiLz4KPC9zdmc+'">
                <div class="movie-info">
                    <h3 class="movie-title">{movie['title']}</h3>
                    <div class="movie-details">
                        <div class="detail-row">
                            <span class="detail-label">Release Type:</span>
                            <span class="detail-value">{movie['type']}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Release Date:</span>
                            <span class="detail-value">{movie['date']}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Downloadable:</span>
                            <span class="status-badge {status_class}">{movie['status']}</span>
                        </div>
                    </div>
                    <p style="margin-top: 15px; color: #6c757d; font-size: 0.9em; line-height: 1.4;">{overview}</p>
                </div>
            </div>
        """
    
    html += """
        </div>
        
        <div class="footer">
            <p>Generated by ombicheck.py | Data from The Movie Database (TMDb) | <a href="https://github.com/WilmeRWubS/OmbiChecker" target="_blank" rel="noopener noreferrer">https://github.com/WilmeRWubS/OmbiChecker</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    return html

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
        
        movie_data = search_movie(title)
        if not movie_data:
            movie_results.append({
                'title': title,
                'type': 'Not Found',
                'date': '-',
                'status': '-',
                'poster_url': '',
                'overview': 'Movie not found in TMDb database.'
            })
            continue
        
        movie_id = movie_data['id']
        poster_path = movie_data.get('poster_path', '')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
        overview = movie_data.get('overview', 'No description available.')
        
        release_info = get_valid_release(movie_id)
        downloadable_status = determine_downloadable_status(release_info)
        
        if release_info:
            release_type = release_info['type']
            release_date = release_info['date'] if release_info['date'] else "TBD"
            movie_results.append({
                'title': title,
                'type': release_type,
                'date': release_date,
                'status': downloadable_status,
                'poster_url': poster_url,
                'overview': overview
            })
        else:
            movie_results.append({
                'title': title,
                'type': '-',
                'date': 'TBD',
                'status': 'No',
                'poster_url': poster_url,
                'overview': overview
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
tk.Button(controls_frame, text="Sort", command=sort_results).pack(side=tk.LEFT, padx=(0, 20))

# HTML Export button
tk.Button(controls_frame, text="Generate HTML Report", command=generate_html_report, 
          bg="#007bff", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT)

tk.Label(window, text="Results:").pack(anchor='w', padx=10)
output_text = scrolledtext.ScrolledText(window, height=15, width=110, state=tk.DISABLED)
output_text.pack(padx=10, pady=5)

window.mainloop()