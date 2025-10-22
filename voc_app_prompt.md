# Voice of Customer Data Collection App - Development Prompt

## Project Overview
I need you to develop a comprehensive Voice of Customer (VoC) data collection application using Crawl4AI (https://github.com/unclecode/crawl4ai) that scrapes and analyzes customer sentiment, opinions, and feedback from forums, social media platforms, and search engines.

## Core Objectives
1. **Multi-Source Data Collection**: Scrape customer feedback from diverse sources including:
   - Forums (Reddit, specialized industry forums, Q&A sites like Quora)
   - Social media platforms (Twitter/X, Facebook, LinkedIn, Instagram)
   - Search engine results (Google, Bing for blogs, reviews, articles)
   - Review sites (Trustpilot, G2, Capterra, Yelp, Google Reviews)
   - YouTube comments and video descriptions

2. **Intelligent Data Extraction**: Use Crawl4AI's LLM-friendly features to extract:
   - Customer pain points and complaints
   - Feature requests and desires
   - Positive experiences and praise
   - Competitive comparisons
   - Buying journey insights
   - Emotional sentiment indicators
   - User demographics and context

3. **Sentiment & Theme Analysis**: Process extracted data to identify:
   - Sentiment scores (positive, negative, neutral)
   - Recurring themes and topics
   - Trending issues over time
   - Customer journey stages
   - Product/feature-specific feedback

## Technical Requirements

### 1. Application Architecture
- **Backend**: Python-based using Crawl4AI as the core scraping engine
- **Database**: Structure for storing:
  - Raw scraped data with metadata (source URL, timestamp, platform)
  - Processed/cleaned text
  - Sentiment analysis results
  - Categorized themes and tags
  - User/author information (anonymized)
- **API Layer**: RESTful API for data access and configuration
- **Frontend Dashboard**: Visualization interface for insights

### 2. Crawl4AI Implementation
Implement the following Crawl4AI features:
```python
# Key features to utilize:
- Fit Markdown: Remove noise from scraped content
- Citations: Track source attribution for each insight
- Adaptive Crawling: Intelligently determine when sufficient data is collected
- LLM Integration: Use for intelligent extraction and classification
- Stealth Crawling: Handle bot-protected sites
```

### 3. Data Source Configuration
Create configurable crawlers for:

**Forums:**
- Reddit (specific subreddits related to industry/product)
- Discord (if accessible)
- Specialized forums (XDA Developers, Stack Overflow, etc.)
- Quora topic pages

**Social Media:**
- Twitter/X (hashtags, mentions, user searches)
- LinkedIn posts and comments
- Facebook public groups/pages
- Instagram comments and captions

**Search Engines:**
- Blog post aggregation
- News article mentions
- Review site content
- Forum thread discovery

### 4. Key Features to Develop

#### A. Query & Target Management
- Allow users to define:
  - Product/brand names to monitor
  - Competitor brands
  - Industry keywords
  - Specific features or topics
  - Date ranges for historical analysis
  - Geographic regions (if relevant)

#### B. Smart Extraction Logic
Use LLMs to extract:
```
- Main topic/theme
- Sentiment (1-5 scale or positive/negative/neutral)
- Pain points mentioned
- Feature requests
- Competitive mentions
- Context (buying stage, use case, user type)
- Urgency indicators
- Actionable insights
```

#### C. Data Processing Pipeline
1. **Crawl** → Raw HTML/content collection
2. **Clean** → Remove ads, navigation, irrelevant content
3. **Extract** → Pull relevant customer voice data
4. **Classify** → Categorize by theme, sentiment, priority
5. **Deduplicate** → Remove duplicate insights
6. **Store** → Save with metadata and relationships
7. **Analyze** → Generate insights and trends

#### D. Insights Dashboard
Create visualizations for:
- Sentiment trend over time
- Top pain points (word clouds, frequency charts)
- Feature request ranking
- Competitive comparison matrix
- Customer journey stage distribution
- Source breakdown (which platforms provide most insights)
- Emerging themes detection
- Geographic sentiment mapping

#### E. Alert System
- Real-time notifications for:
  - Sudden sentiment shifts
  - Viral negative feedback
  - New trending topics
  - Competitive activity
  - Urgent customer issues

### 5. Ethical & Legal Considerations
Implement:
- Respect for robots.txt
- Rate limiting to avoid overwhelming servers
- User privacy protection (anonymize PII)
- Terms of Service compliance checker
- Data retention policies
- GDPR/privacy law compliance features

### 6. Advanced Features (Nice-to-Have)
- **AI-Powered Insights**: Use LLM to generate:
  - Executive summaries
  - Recommended actions
  - Root cause analysis
  - Predictive trending
  
- **Multi-Language Support**: Translate and analyze non-English feedback

- **Integration Capabilities**:
  - Export to CSV/Excel
  - Slack/Teams notifications
  - CRM integration (Salesforce, HubSpot)
  - Product management tools (Jira, Linear)

- **Competitive Intelligence**: Side-by-side comparison of your brand vs competitors

- **Historical Tracking**: Show how sentiment/topics evolve over months/years

## Implementation Phases

### Phase 1: MVP (Minimum Viable Product)
- Basic crawler for Reddit and Twitter
- Simple keyword-based extraction
- Basic sentiment analysis
- SQLite database
- Command-line interface
- CSV export

### Phase 2: Enhanced Data Collection
- Add more sources (forums, review sites)
- Implement Crawl4AI's adaptive crawling
- LLM-based intelligent extraction
- PostgreSQL database
- RESTful API

### Phase 3: Analytics & Visualization
- Web dashboard with charts
- Theme clustering
- Trend analysis
- Alert system
- User authentication

### Phase 4: Advanced Features
- Real-time monitoring
- AI-generated insights
- Multi-language support
- Third-party integrations

## Deliverables Expected

1. **Source Code**: Well-documented, modular Python codebase
2. **Documentation**:
   - Setup and installation guide
   - Configuration documentation
   - API documentation
   - User manual
3. **Database Schema**: Clear data model with relationships
4. **Sample Queries**: Pre-configured searches for common use cases
5. **Dashboard**: Interactive web interface
6. **Test Suite**: Unit and integration tests
7. **Deployment Guide**: Docker/cloud deployment instructions

## Example Use Cases to Support

1. **Product Manager**: "What are the top 5 feature requests for our mobile app this month?"
2. **Customer Success**: "What are customers saying about our onboarding process?"
3. **Marketing**: "How does sentiment for our brand compare to Competitor X?"
4. **Executive**: "What's the overall health of customer satisfaction this quarter?"
5. **Support Team**: "What emerging issues should we prepare for?"

## Technical Stack Recommendations

**Required:**
- Python 3.9+
- Crawl4AI library
- LLM API (OpenAI, Anthropic Claude, or open-source)

**Suggested:**
- FastAPI or Flask (API)
- PostgreSQL or MongoDB (database)
- Redis (caching/queue management)
- Celery (task scheduling)
- React or Vue.js (frontend)
- Plotly or D3.js (visualizations)
- Docker (containerization)

## Success Metrics

The application should be able to:
- ✅ Scrape at least 1000 data points per day across multiple sources
- ✅ Process and categorize data with 80%+ accuracy
- ✅ Detect sentiment with 75%+ accuracy
- ✅ Load dashboard insights in under 3 seconds
- ✅ Handle multiple concurrent users
- ✅ Respect rate limits and avoid being blocked

## Questions to Address in Your Implementation

1. How will you handle authentication for platforms that require it?
2. What's your strategy for dealing with dynamic content (JavaScript-heavy sites)?
3. How will you ensure data freshness while managing crawl frequency?
4. What's your approach to handling duplicate content from cross-posting?
5. How will you scale the system as data volume grows?
6. What's your plan for handling API rate limits from various platforms?

## Additional Context

Please provide:
- Architectural diagrams
- Sample configuration files
- Example API requests/responses
- Screenshots or mockups of the dashboard
- Performance benchmarks
- Cost estimates for running at scale

---

## Getting Started

Begin by:
1. Setting up Crawl4AI and testing basic scraping on 2-3 sources
2. Designing the database schema for VoC data
3. Creating a simple extraction pipeline
4. Building a proof-of-concept dashboard
5. Iterating based on data quality and insights value

Let me know if you need clarification on any aspect of this project!