# 🎬 Movie Downloadability Checker

Check if movies are officially released on digital or physical platforms using TMDb and Vuniper. Includes a GUI for manual checks and a CLI for automation.  
<img width="1495" height="695" alt="ombicheck py" src="https://github.com/user-attachments/assets/286b3a56-7883-4b68-b929-b20c92f419b4" />  

Includes a more advanced GUI styled after Windows 11 using [`Sun Valley ttk theme`](https://github.com/rdbende/Sun-Valley-ttk-theme).  
Supports both `dark` and `light` mode.
<img width="1517" height="696" alt="Windows 11 Style GUI" src="https://github.com/user-attachments/assets/4a72ef8b-4bcc-4b44-a41d-84a38ca2bd4c" />

---

## ✨ Features

- 🔎 Queries Vuniper and TMDb for each movie  
- 🎬 Detects both theatrical and digital release dates  
- 🗓️ Supports custom digital dates via `digital_dates.txt` (for custom possible release dates)  
- ✅ Classifies movies as: **Yes**, **Soon**, **TBD**, or **No**  
- 🔃 Sortable in both HTML and GUI  
- 📄 Generates responsive, styled HTML reports  
- 📥 Pulls movie requests directly from the Ombi database if wanted  

---

## 🖥️ GUI Usage

1. Install requirements:  
   `pip install requests tkinter selenium`

2. Set your TMDb Bearer Token in the script or in the GUI tool:  
   `TMDB_BEARER_TOKEN = "enterhere"`

3. Run the tool:  
   `python ombicheck.py`

4. Paste a movie list (possibly from Ombi), like:  
   `Jurassic World Rebirth (07/01/2025)	Released`

5. Click **“Check Availability”** and optionally generate an HTML report.

---

## 🧪 CLI Usage

Automate checks directly from the terminal. Example:  

`python ombicheck.py --tmdb-token "enterhere" --ombi-db /path/to/ombi.db --output-html report.html`

### Available options:

```
--tmdb-token       Your TMDb v4 Bearer Token (required for html)  
--ombi-db          Path to Ombi’s SQLite database (default: ombi.db)  
--custom-dates     Optional path to digital_dates.txt  
--output-html      Output HTML file for the report  
--language         TMDb metadata language 
--debug            Show debug output  
```

---

## 📆 digital_dates.txt Format

Use this for possible release dates to get a **"Soon"** result.  
If anyone knows where to get good info like this for automation, let me know.

Fallback examples for titles not found on Vuniper (flexible, assumes year 2025 if not given):

```
28 Years Later August 30  
F1 July 15, 2025  
The New Era Movie 26 July 2025  
```

Month names can be abbreviated or full, with or without year.

---

## 🟢 Status Definitions

```
Yes        = Available for digital download  
Soon       = Date is set, not yet released  
No         = Only theatrical or not released  
```

---

## 🧾 HTML Report

- 🎞️ Poster, title, release dates, overview  
- 🔗 Clickable links to Ombi and Vuniper (if enabled)  
- 📊 Filters by availability status  
- 🎨 Customizable background and TMDb language  

---

## ⚙️ Requirements

> Note: On Ubuntu Server, you may need to install Tkinter via apt or remove the GUI import.

- Python 3.7+  
- Google Chrome + ChromeDriver  
- Python packages: `requests`, `selenium`, `tkinter`  

---

## 🔐 TMDb Token

Create your token at:  
https://www.themoviedb.org/settings/api  

Use the Bearer Token in the GUI settings or pass it via `--tmdb-token` in CLI.

---
