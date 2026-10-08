# Employability Pathway – Public Dashboard

A public Streamlit dashboard showing **aggregated results only** from ADWSO's Employability Pathway assessment
of vocational training graduates (KoBoToolbox).

## How it keeps children's data private

```
KoBoToolbox ──(API token, GitHub secret)──► aggregate.py ──► data/summary.json ──► app.py (public)
   raw data            runs daily in GitHub Actions          totals only               reads totals only
```

* `aggregate.py` reads only the fields needed for counting. Names, phone numbers, GPS, photos, enumerator
  details, districts/villages and free-text answers are never read or saved.
* Raw submissions exist only in memory during the run; they are never written to the repository.
* Groups (e.g. provinces) are never merged. Any figure based on 1–4 graduates is shown as "<5" (with a second
  figure hidden where needed so it cannot be worked out from the total). For any group of fewer than 10 graduates
  only its size is shown, never its answers. A filter selection is shown only when at least 10 graduates match.
* Submissions marked **Not approved** in KoBo, and interviews without consent, are excluded.
* `app.py` has no KoBo access at all – it only reads `data/summary.json`.

## One-time setup (about 20 minutes)

### 1. Create a read-only KoBo account for the dashboard (recommended)
A KoBo API token gives full access to the account it belongs to. To limit risk:
1. Register a new KoBo account, e.g. `adwso_dashboard` (use plus-addressing such as `you+dashboard@adwso.org`).
2. In the form's **Sharing** settings, give that account **View submissions** only.
3. Log in as that account → **Account settings → Security → API key** → copy the key.

### 2. Create the GitHub repository
1. On GitHub, create a new **public** repository, e.g. `adwso-employability-dashboard`.
2. Upload all files from this folder (including the hidden `.github` and `.streamlit` folders).
3. **Settings → Secrets and variables → Actions → New repository secret**
   * Name: `KOBO_TOKEN` – Value: the API key from step 1.
4. **Actions** tab → *Refresh dashboard data* → **Run workflow**. After about a minute, `data/summary.json` appears.
   It then refreshes automatically every day.

### 3. Deploy on Streamlit Community Cloud
1. Go to share.streamlit.io → **Create app** → choose the repository, branch `main`, file `app.py`.
2. Deploy. No Streamlit secrets are needed – the app holds no credentials.
3. Each daily data refresh commits a new `summary.json`, and the app updates automatically.

## Changing the rules
In `aggregate.py`: `MIN_CELL` (default 5) and `MIN_GROUP` (default 10). The logo is `assets/adwso_logo.png`. Indicators are listed in `INDICATORS`.
If the KoBo form changes (new options or questions), labels update automatically from the form; a brand-new
question must be added to `KEEP` and `INDICATORS` before it appears.

## Testing locally
```
pip install -r requirements.txt
KOBO_TOKEN=xxxx python aggregate.py     # writes data/summary.json
streamlit run app.py
```
Never commit raw exports – `.gitignore` blocks common file names, but check before every commit.
