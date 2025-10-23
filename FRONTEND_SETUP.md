# Frontend Data Visibility Guide

## ✅ What's Been Fixed

### 1. **New Feedback Page Added**
- **Route**: `/feedback`
- **Purpose**: View raw crawled data immediately after crawling
- **Location**: `voc_app/frontend/src/pages/Feedback.tsx`
- Shows all feedback records with content, author, dates, and source links

### 2. **Navigation Updated**
- Added "Feedback" menu item in sidebar
- Icon: FileText
- Positioned between Insights and Sources

### 3. **API Integration**
- Added `feedbackApi` to `voc_app/frontend/src/lib/api.ts`
- Backend endpoint already exists at `/api/v1/feedback`
- Frontend now queries this endpoint

## How Data Flows

```
1. Crawl runs → Stores in `feedback` table
2. View in Feedback page → Shows raw crawled data
3. Extract insights → Creates records in `insights` table
4. View in Insights page → Shows processed insights
```

## Viewing Your Crawled Data

### Option 1: Feedback Page (Raw Data)
1. Navigate to **Feedback** in the sidebar
2. See all crawled content immediately
3. No insight extraction needed

### Option 2: Insights Page (Processed Data)
1. Run insight extraction (requires OpenAI API key)
2. Navigate to **Insights** in the sidebar
3. See structured insights with sentiment, themes, etc.

## Current Status

**Crawled Data**: ✅ 5 feedback records stored
- 3 have insights (from demo data)
- 2 are new Reddit crawls (visible in Feedback page)

**Why Insights Page Was Empty**: 
- The Insights page only shows processed insights
- New crawls need insight extraction to appear there
- Feedback page shows raw data immediately

## Next Steps

### To See Raw Data Now
```bash
# Start frontend (if not running)
cd voc_app/frontend
npm run dev
```
Then visit: `http://localhost:5173/feedback`

### To Extract Insights (Optional)
**Note**: Requires OpenAI API key in `.env`

The insight extractor currently has an issue with the model configuration. To fix:

1. Set `OPENAI_API_KEY` in your `.env` file
2. Update the model in `voc_app/config.py` or pass `model="gpt-4o"` when calling extraction

Or skip insight extraction and just use the Feedback page to view crawled data!

## Summary

✅ **Crawlers work** - Data is being stored
✅ **Feedback page added** - Raw data is now visible in frontend
✅ **Navigation updated** - Easy access from sidebar
✅ **API connected** - Frontend queries backend successfully

Your crawled data IS being stored and IS now viewable in the frontend via the new Feedback page!
