# Step-by-step Mac setup guide

For an Apple Silicon (M1/M2/M3/M4) or Intel MacBook running macOS, using the default **zsh** Terminal. You need about 1 GB of free disk space and an internet connection for the first setup only.

---

## 0. What you will end up with

* A new Conda environment called **`fresherjobs`** (Python 3.12). Your existing environments (`deepfake_env`, `py13`, `venv`, `numericalpython`, …) are **not touched**.
* The Chromium browser that Playwright uses, stored in `~/Library/Caches/ms-playwright` (about 150 MB).
* The app running at **http://localhost:8501** in your normal browser.

**Why Python 3.12?** The pinned versions of NumPy (2.5) and SciPy (1.18) need Python 3.12 or newer. The project was tested on Python 3.13, and `environment.yml` uses 3.12, which is widely supported by Conda.

---

## 1. Unzip the project

1. Double-click `ai-powered-fresher-job-discovery-system.zip` in **Downloads**. Finder creates the folder `ai-powered-fresher-job-discovery-system`.
2. Open **Terminal** (press Cmd + Space, type *Terminal*, press Return).
3. Go into the folder:

```bash
cd ~/Downloads/ai-powered-fresher-job-discovery-system
```

If you put the folder somewhere else, type `cd ` (with a space), drag the folder from Finder into the Terminal window, and press Return.

## 2. Check that Conda works

```bash
conda --version
```

If you see `conda: command not found`, close Terminal, open it again, and retry. If it still fails, run `source ~/miniconda3/bin/activate` once, then `conda init zsh`, and reopen Terminal.

## 3. Run the automatic setup (recommended)

```bash
chmod +x setup.sh run.sh
```

```bash
./setup.sh
```

The script will:

1. create the `fresherjobs` environment from `environment.yml`, or update it if it already exists,
2. install the packages listed in `requirements.txt`,
3. download Chromium for Playwright,
4. run the test suite. You should see **`100 passed`** at the end.

The first run takes about 3–8 minutes, depending on your internet speed.

*No Conda?* Run `USE_VENV=1 ./setup.sh`. This creates a local `.venv` instead. It needs Python 3.12 or 3.13 from python.org or Homebrew.

## 4. Start the app

```bash
./run.sh
```

Terminal prints `Opening http://localhost:8501`. Open that address in Safari or Chrome. If port 8501 is busy, `run.sh` automatically picks 8502, 8503 and so on, and prints the address it chose.

## 5. Use it

1. The **Dashboard** opens with the sample dataset and any previously collected jobs.
2. Go to **Collect Jobs (Playwright)** and click **Start demo crawl**. It finishes in about 20 seconds and does not need the internet.
3. Go to **AI Recommendations** and click **Fill in the demo profile**. You can also upload `data/fixtures/resumes/sample_resume_fictional.pdf`, press *Extract skills*, and then press **Get recommendations**.

## 6. Stop the app safely

* If a crawl is running, first click **Stop crawl** on the Collect Jobs page. The crawler saves its current batch and closes Chromium by itself.
* Then click the Terminal window and press **Ctrl + C**.
* Closing the browser tab alone does not stop the server.

## 7. Next time

```bash
cd ~/Downloads/ai-powered-fresher-job-discovery-system
./run.sh
```

## 8. Doing the steps by hand (optional)

```bash
conda env create -f environment.yml
```

```bash
conda activate fresherjobs
```

```bash
python -m playwright install chromium
```

```bash
python -m pytest
```

```bash
streamlit run app.py
```

In VS Code: open the folder, press Cmd + Shift + P → *Python: Select Interpreter* → choose **fresherjobs**. Then run the commands above in the integrated terminal.

## 9. Troubleshooting

| Message / symptom | What to do |
|---|---|
| `zsh: permission denied: ./setup.sh` | `chmod +x setup.sh run.sh` |
| `conda: command not found` | Reopen Terminal; or `source ~/miniconda3/bin/activate` then `conda init zsh` |
| `CondaHTTPError` / slow download | Check Wi-Fi and run `./setup.sh` again; it resumes where it stopped |
| `Executable doesn't exist at …/chromium…` | `conda activate fresherjobs` then `python -m playwright install chromium` |
| `ModuleNotFoundError: No module named 'streamlit'` | You are in the wrong environment: `conda activate fresherjobs` |
| pip tries to compile numpy/scipy (long C errors) | Python is too old; recreate the env with `conda env create -f environment.yml` |
| `Port 8501 is already in use` | `./run.sh` picks a free port; or run `lsof -i :8501` and close that app |
| macOS asks whether Python may accept incoming connections | Click **Allow**; Streamlit serves only on your computer |
| Live crawl shows HTTP 403 / CAPTCHA / 0 jobs | Expected for protected sites; they are skipped, never bypassed. Use the demo crawl |
| SSL certificate errors in `verify-catalogue` | `pip install --upgrade certifi` inside the environment |
| Page looks stale | *Settings & About → Refresh data from disk* |
| A crawl seems stuck | *Collect Jobs → Stop crawl*; read `logs/crawl_subprocess.log` |
| Remove everything | `conda env remove -n fresherjobs` and delete the folder; Chromium cache: `rm -rf ~/Library/Caches/ms-playwright` |
