# Final submission checklist

## A. Fill in your details (the report contains yellow-highlighted placeholders in the DOCX)
- [ ] Cover page: student name, enrollment number, supervisor name, designation
- [ ] Declaration: name, enrollment number, date, place — sign after printing
- [ ] Certificate: student name and enrollment number; leave the supervisor and HOD signatures for them
- [ ] Acknowledgement: names of the supervisor, HOD and Principal/Director
- [ ] Acknowledgement: complete or delete the bracketed note on AI-assistant use, following your institute's academic-integrity policy
- [ ] Spine text for hard binding: “AI-POWERED FRESHER JOB DISCOVERY SYSTEM USING PLAYWRIGHT ([your batch, e.g. 2023-27])”

## B. Report files
- [ ] Open `docs/project_report.docx` in Word, press **Ctrl/Cmd + A**, then **F9** (or right-click the table of contents → *Update Field* → *Update entire table*) so the TOC page numbers match Word's own layout
- [ ] Check the page numbers in the *List of Figures* and *List of Tables* (they come from the PDF layout and may shift by a page in Word)
- [ ] Export the edited DOCX to PDF (*File → Save As → PDF*) for printing, or use the supplied `project_report.pdf` if you did not edit anything
- [ ] Print single-sided on A4; hard bound (maroon, golden print) as per the guidelines

## C. Project
- [ ] `./setup.sh` completes on your Mac and reports `100 passed`
- [ ] `./run.sh` opens the app; the demo crawl completes (14 jobs, 1 duplicate removed)
- [ ] Optional: run one live crawl the day before the evaluation and note the result (live sites change)
- [ ] Take one screenshot of the `100 passed` test output for the presentation

## D. Evaluation day
- [ ] Laptop charged; Terminal open in the project folder; `./run.sh` already running
- [ ] Browser open at http://localhost:8501; other apps using port 8501 closed
- [ ] `docs/demo_script.md` and `docs/presentation_outline.md` reviewed
- [ ] `docs/viva_questions.md` revised (79 questions)
- [ ] Fallback ready: if Wi-Fi fails, use the offline demo crawl and sample data only

## E. Files to submit
- [ ] Project ZIP (`ai-powered-fresher-job-discovery-system.zip`)
- [ ] Report DOCX and PDF
- [ ] Presentation slides (build from `docs/presentation_outline.md`)
