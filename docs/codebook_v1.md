# CMCA Publication Audit – Codebook v1

**Version:** v1  
**Date:** 25/08/2025
**Contributors:** initial draft, 20/30 cases uncompleted)  

---

## Purpose
This codebook documents the structure and coding rules for the CMCA Gold Standard dataset (30 cases).  
Version 1 covers the first 20 cases (uncompleted). It defines each column, clarifies coding decisions, and sets expectations for group consistency.  
Later versions will be updated as PDF checks and adjudication progress.

---

## Dataset Overview
- **Rows:** One row per publication (Case 1–30).  
- **Columns:** 20 fields, defined below.  
- **Current Status:** 20/30 coded (titles, authors, platforms, DOI, etc.).  
- **Pending:** Verification against PDFs, adjudicated notes, negative case inclusion.

---

## Field Definitions

1. **Case**  
   - Unique case number (1–30).  

2. **CMCA Platform Used (Yes/No/Ambiguity)**  
   - Whether CMCA platforms/instruments were used.  
   - Options:  
     - `Y` = Yes  
     - `N` = No  
     - `Ambiguous` = Unclear from text  

3. **Authors (Family name, Initial.)**  
   - Author list as written in the paper.  
   - Format: “Familyname, Initials., … and FinalAuthor”  

4. **Title**  
   - Title of the publication.  

5. **Journal**  
   - Journal name (as listed in the article).  

6. **Platform(s)**  
   - Instruments/platforms explicitly mentioned.  
   - Examples: `EM`, `SEM`, `FIB`, `Raman`, etc.  
   - Multiple entries separated by space.  

7. **CMCA Co-author (Yes/No)**  
   - Whether a known CMCA-affiliated researcher is listed as co-author.  

8. **CMCA Co-author Name(s)**  
   - If yes, list the co-author(s).  
   - Example: `PLClode`, `MSaunders`  

9. **CMCA Acknowledged (Yes/No/Unclear)**  
   - Whether CMCA (or associated facilities: NIF, Metabolomics, MicroAust, etc.) were explicitly acknowledged.  

10. **CMCA Ack Exact Text**  
    - Verbatim text of acknowledgement from the paper.  

11. **CMCA Affiliation in Text (Yes/No)**  
    - Whether CMCA is explicitly listed as an affiliation.  

12. **Author on CMCA Staff List (Yes/No)**  
    - Whether the author appears on CMCA’s official staff list.  

13. **Instrument Terms (verbatim)**  
    - Raw text mentioning instrument names/techniques from the article.  

14. **Instrument Code (if matched)**  
    - Normalised code (e.g., `SEM`125, `TEM`458).  

15. **Label (Positive/Negative/Ambiguous)**  
    - Initial coder’s label for relevance.  
    - `Positive` = CMCA-related  
    - `Negative` = Not CMCA-related  
    - `Ambiguous` = Unclear  

16. **Notes**  
    - Free-text notes from coder about issues/uncertainty.  

17. **Adjudicated Label**  
    - Final agreed label after review.  

18. **Adjudicated Notes**  
    - Additional clarification of adjudication decision.  

19. **Negative Type (Random/Hard)**  
    - For negative cases only:  
      - `Random` = randomly selected non-CMCA paper  
      - `Hard` = challenging case (close but not CMCA)  

20. **DOI**  
    - Digital Object Identifier of the publication.  

---

## Coding Rules (v1)
- Always record **verbatim text** where possible (acknowledgements, instrument terms).  
- Use consistent abbreviations for instruments (`SEM`, `TEM`, etc.).  
- If unsure, mark as **Ambiguous** and leave a note for adjudication.  
- Negative cases will be split into **5 random** and **5 hard** (to be added in v2).  

---

## Version Notes
- **v1:** 20/30 cases coded; PDF verification pending.  
- **v2 (planned):** Incorporate adjudicated decisions + 10 negative cases.  
- **v3 (planned):** Full 30-case gold standard with examples of edge cases.


