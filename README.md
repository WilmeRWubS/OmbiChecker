# Movie Downloadability Checker  
Simple Python GUI to check if movies have been officially released on digital (VOD) or physical (DVD/Blu-ray) platforms using TMDb.  

# Bash Variant for Automation
A Bash version of the tool is also available, built for automation and integration with Ombi database.  

## Features  
- Checks TMDb for each movie  
- Detects Digital or Physical releases only  
- Classifies as Yes, Soon, TBD, or No  
- Sortable results (Title, Type, Date, Status)
- Export to nice looking html file  

## Usage  
1. Install requirements:  
   pip install requests
   pip install tkinter  

3. Get a TMDb v4 Bearer Token from:  
   https://www.themoviedb.org/settings/api  

4. Add your token in the script:  
   TMDB_BEARER_TOKEN = "enterhere"  

5. Run:  
   python ombicheck.py 

6. Paste a tab-separated movie list and click "Check Availability".  

Example input:  
Jurassic World Rebirth (07/01/2025)	Emma	Released  
The Fantastic Four: First Steps (07/23/2025)	Emma	Post Production  

Status meanings:  
Yes    = Proper release, available  
Soon   = Coming soon (date in future)  
TBD    = Release type known, no date  
No     = Not yet released  
Not Found = Not in TMDb
