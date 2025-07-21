import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox

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
            
            # Prepare movie result with separate theater and digital dates
            theater_date = "TBD"
            digital_date = "TBD"
            status = "TBD"
            vuniper_url = None
            
            if vuniper_info:
                theater_date = vuniper_info.get('theater_date') or "TBD"
                digital_date = vuniper_info.get('digital_date') or "TBD"
                status = vuniper_info.get('status', 'TBD')
                vuniper_url = vuniper_info.get('vuniper_url')
            
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
                'vuniper_url': vuniper_url
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