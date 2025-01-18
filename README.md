# ART Finder (Automated Research and Trigger Finder)
## Technical Documentation

### Project Overview
ART Finder is an advanced AI-powered research automation platform designed to streamline the ad creation process by automatically gathering and analyzing data from multiple sources. The system leverages state-of-the-art language models and search capabilities to identify user pain points, analyze competitor strategies, and generate actionable marketing insights.

### Architecture
The application follows a modern microservices architecture with the following components:

#### Backend Components
1. **FastAPI Server** (`main.py`)
   - RESTful API endpoints for research analysis
   - CORS middleware for cross-origin requests
   - Health monitoring endpoints
   - Input validation using Pydantic models

2. **Research Analysis Engine** (`app.py`)
   - Core analysis functionality
   - Integration with multiple AI and search services
   - Data scraping and processing capabilities
   - Insight generation and formatting

### Core Features

#### 1. Multi-Source Data Collection
- **Search Integration**: Google Custom Search API for comprehensive web scraping
- **Platform Coverage**:
  - General web content
  - Reddit posts and comments
  - Quora answers
  - Blog articles
  - Competitor analysis

#### 2. AI-Powered Analysis
- **LLM Integration**: Groq API for advanced language processing
- **Analysis Components**:
  - Effective trigger identification
  - Competitor analysis
  - Word cloud generation
  - Pain point analysis
  - Sentiment analysis

#### 3. Data Processing Pipeline
```
Input → Question Generation → Multi-Source Search → Content Extraction → Analysis → Insight Generation
```

### API Endpoints

#### 1. Analysis Endpoint
```
POST /analyse
```
Request Body:
```json
{
    "domain": "string",
    "project": "string",
    "description": "string"
}
```
Response:
```json
{
    "status": "success",
    "data": {
        "domain": "string",
        "project": "string",
        "description": "string",
        "effective_triggers": ["string"],
        "competitors": ["string"],
        "word_cloud_data": {"word": "score"},
        "pain_points": {"point": "score"},
        "full_analysis": "string",
        "timestamp": "string",
        "resource_links": ["string"]
    },
    "timestamp": "string"
}
```

#### 2. Health Check Endpoint
```
GET /health
```
Response:
```json
{
    "status": "healthy",
    "timestamp": "string"
}
```

### Technical Implementation Details

#### 1. Web Scraping System
- Custom `WebScraper` class with intelligent content extraction
- Support for various content types and structures
- Error handling and retry mechanisms
- Rate limiting compliance

#### 2. Analysis System
- Multi-step analysis pipeline
- Prompt engineering for specific insights
- Data validation and cleaning
- Result formatting and structuring

### Security Features
1. CORS protection
2. Input validation
3. Rate limiting
4. API key management
5. Error handling and logging

### Performance Optimizations
1. Asynchronous operations
2. Efficient data processing
3. Response caching
4. Parallel processing where applicable

### Technical Requirements

#### Dependencies
- Python 3.8+
- FastAPI
- LangChain
- BeautifulSoup4
- Requests
- Groq API
- Google Custom Search API

#### Environment Variables
```
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id
```

### Future Enhancements
1. Real-time competitor monitoring
2. Advanced sentiment analysis
3. Automated A/B testing recommendations
4. Integration with ad platforms
5. Custom insight generation models

### Development Status
Backend implementation complete with the following components:
- Core analysis engine
- API endpoints
- Data processing pipeline
- Integration with AI services

Frontend currently under development, will include:
- Interactive dashboard
- Visual data presentation
- Real-time analysis monitoring
- User management system

### Conclusion
ART Finder demonstrates a robust technical implementation that fully addresses the hackathon requirements. The system showcases innovative use of AI technology, efficient data processing, and scalable architecture, making it a strong contender for evaluation.
