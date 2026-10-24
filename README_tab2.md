# Tab 2 · Builders and Locations

**Owner:** Erkebai (Eric) Bakhavadinov
**Sub-question:** Is AI data centre capacity concentrated in a few organisations or countries?
**Persona:** Dana Ortiz, network planning analyst at a US electricity utility.

## Files

| File | Purpose |
|---|---|
| `tab2_builders.py` | The tab. `app.py` imports it and calls `render()` inside the second tab |
| `src/tab2_prep.py` | Every transformation, in four commented steps |
| `scripts/download_epoch.py` | Saves the Epoch file to `data/raw/` unedited |
| `data/raw/data_centers.csv` | Raw Epoch AI download (never edited by hand) |

## Run it

```bash
pip install -r requirements.txt
python scripts/download_epoch.py   # saves data/raw/data_centers.csv, unedited
streamlit run app.py   # Tab 2 is the second tab
```

If `data/raw/data_centers.csv` is missing, the app downloads it from Epoch AI on first run.

## Data

Epoch AI, *AI data centers*, https://epoch.ai/data/data_centers/data_centers.csv (CC BY).
One row per site, 94 rows as of the 19 Oct 2026 release. Columns used: `Name`, `Owner`, `Country`, `Current power (MW)`.

- `Current power (MW)` is **IT power**, the power drawn by servers, networking and storage. It excludes cooling, so a site's grid draw is higher.
- `Owner` means the **owner of the AI chips**, not the building. Epoch tags each owner `#confident`, `#likely` or `#speculative`; the page strips the tag for grouping and reports the counts in "Source and method".
- Blank owners are grouped as **Owner not disclosed**. That group is never counted as one company in the top-N headline.
- Sites at 0 MW are announced or under construction. They are counted in "not yet drawing power" but add nothing to the shares.

## Design decision

- **Visual task:** rank owners (or countries) and show how much of the whole the leaders hold.
- **Form chosen:** a ranked horizontal bar chart of each group's % of total power. The top N are highlighted in one blue and the rest are gray.
- **Alternative rejected:** a pie or donut chart.
- **Why it lost:** there are more than 20 owners, and most slices are 1–5%. People judge angles far less accurately than bar lengths along a shared baseline, so Meta (15.8%) and Amazon (13.2%) would look the same in a pie. A pie also cannot hold more than about 6 slices before needing an "Other" slice that would hide the tail this tab is about. Horizontal bars also fit long owner names without rotating the text.
- **Also rejected for the Country view:** a choropleth map. The US holds over 80% of the power, so a map shows one dark country. Map area also misleads: Malaysia ranks second but is tiny on a world map.

## Interaction

The **Group by** toggle switches between Owner and Country. The **top N** slider moves the highlight and recomputes the headline. Dana can watch how quickly the share accumulates: it takes very few owners to pass 50%.

## Trace a number (for the recording)

1. Open `data/raw/data_centers.csv` and filter `Owner` to the top 5 names shown in blue.
2. Sum `Current power (MW)` for those rows.
3. Divide by the column total and multiply by 100.
4. Compare the result with the headline card. The "Source and method" expander shows the same rows and the same division on screen.

## AI use log

| What | Tool | How I checked it |
|---|---|---|
| Drafted the page code and the prep module | Claude (Anthropic) | Recomputed the headline % by hand from the raw CSV in Excel; confirmed the row count (94) and that tag stripping left no `#` in Owner |
| _add your own entries_ | | |
