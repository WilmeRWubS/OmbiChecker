Movie Downloadability Checker  
Simple Python GUI to check if movies have been officially released on digital (VOD) or physical (DVD/Blu-ray) platforms using TMDb.  

Features  
- Checks TMDb for each movie  
- Detects Digital or Physical releases only  
- Classifies as Yes, Soon, TBD, or No  
- Sortable results (Title, Type, Date, Status)  

Usage  
1. Install requirements:  
   pip install requests  

2. Get a TMDb v4 Bearer Token from:  
   https://www.themoviedb.org/settings/api  

3. Add your token in the script:  
   TMDB_BEARER_TOKEN = "your_token_here"  

4. Run:  
   python movie_checker.py  

5. Paste a tab-separated movie list and click "Check Availability".  

Example input:  
Jurassic World Rebirth (07/01/2025)	Emma	Released  
The Fantastic Four: First Steps (07/23/2025)	Emma	Post Production  

Status meanings:  
Yes    = Proper release, available  
Soon   = Coming soon (date in future)  
TBD    = Release type known, no date  
No     = Not yet released  
Not Found = Not in TMDb  
