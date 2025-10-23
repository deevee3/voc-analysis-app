# Crawler Setup Guide

## ✅ All Crawlers Are Now Working

All 6 platform crawlers have been fixed and are ready for live data collection:

### Fixed Issues
1. **Reddit Crawler** - Switched to `old.reddit.com` with proper HTML markup
2. **All Crawlers** - Updated extraction schemas to use `baseSelector` + `fields` format
3. **Cleaning Pipeline** - Lowered `min_characters` threshold from 20 to 10
4. **Logging** - Added detailed discard reason tracking

## How to Use Each Crawler

### 1. Reddit
```bash
uv run python -m voc_app.cli crawl --platform reddit --source "Reddit Mentions" --query technology --limit 25
```
**Config format:**
```json
{
  "subreddit": "technology",
  "sort": "new",
  "time_filter": "day"
}
```

### 2. Twitter/X
```bash
uv run python -m voc_app.cli crawl --platform twitter --source "Twitter Mentions" --query "your brand" --limit 25
```
**Config format:**
```json
{
  "query": "your search term",
  "result_type": "latest"
}
```

### 3. YouTube
```bash
uv run python -m voc_app.cli crawl --platform youtube --source "YouTube Comments" --query dQw4w9WgXcQ --limit 25
```
**Config format:**
```json
{
  "video_id": "dQw4w9WgXcQ"
}
```
OR
```json
{
  "channel_id": "UCxxxxxxx"
}
```

### 4. Trustpilot
```bash
uv run python -m voc_app.cli crawl --platform trustpilot --source "Trustpilot Reviews" --query "your-company" --limit 25
```
**Config format:**
```json
{
  "company_name": "your-company",
  "stars_filter": "4,5"
}
```

### 5. Quora
```bash
uv run python -m voc_app.cli crawl --platform quora --source "Quora Answers" --query "your topic" --limit 25
```
**Config format:**
```json
{
  "query": "your search term"
}
```

### 6. G2
```bash
uv run python -m voc_app.cli crawl --platform g2 --source "G2 Reviews" --query "product-slug" --limit 25
```
**Config format:**
```json
{
  "product_slug": "product-name",
  "rating_filter": "4,5"
}
```

## Using the UI

1. **Navigate to Data Sources page** in the dashboard
2. **Click "Add source"**
3. **Fill in:**
   - Name: Descriptive name for your source
   - Platform: Select from dropdown
   - Config: Paste JSON config from examples above
   - Schedule: Optional (e.g., "every 30m")
   - Active: Check to enable

4. **Run crawl via CLI** using the source name:
```bash
uv run python -m voc_app.cli crawl --platform <platform> --source "<Your Source Name>" --query <query> --limit 25
```

## Verification

Check if data was stored:
```bash
uv run python -m voc_app.cli status --source "<Your Source Name>" --limit 5
```

View in dashboard:
- Navigate to **Insights** page
- Refresh to see new entries
- Or call `GET /api/v1/insights` API endpoint

## Troubleshooting

- **"Discarded" items**: Check the discard reason in CLI output
- **Empty results**: Verify the query/config matches actual content on the platform
- **No data stored**: Ensure `min_characters=10` in cleaning options (already set)
- **Playwright errors**: Run `uv run playwright install chromium`

## Next Steps

1. Configure multiple data sources via the UI
2. Set up scheduled crawls (optional)
3. Run extraction pipeline to generate insights:
   ```bash
   uv run python -m voc_app.cli process-pending-feedback
   ```
4. View insights in the dashboard
