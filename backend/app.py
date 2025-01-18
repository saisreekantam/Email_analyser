from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer
from typing import List, Dict, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import msal
import httpx
import asyncio
import logging
import json
import os
from dotenv import load_dotenv
from email_analyzer import EmailAnalyzer  # Custom email analysis module

# Load environment variables
load_dotenv()

# Configuration
class Settings:
    """Application configuration settings."""
    
    MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID")
    MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:3000/auth/callback")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/emaildb")
    SCOPES = ['Mail.Read', 'Mail.ReadWrite', 'User.Read']
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()
engine = create_engine(settings.DATABASE_URL)

class EmailRecord(Base):
    """Database model for storing email records."""
    
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    email_id = Column(String, unique=True, index=True)
    subject = Column(String)
    sender = Column(String)
    received_time = Column(DateTime)
    importance = Column(String)
    analysis_results = Column(JSON)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydantic models
class EmailAnalysisRequest(BaseModel):
    """Request model for email analysis."""
    
    email_id: str
    subject: str
    body: str
    sender: EmailStr
    received_time: datetime
    importance: str = "normal"

class EmailAnalysisResponse(BaseModel):
    """Response model for email analysis results."""
    
    email_id: str
    analysis_results: Dict
    category: str
    priority_score: float
    sentiment: Dict
    summary: str
    suggested_actions: List[str]

class DashboardMetrics(BaseModel):
    """Model for dashboard metrics."""
    
    total_emails: int
    categories: Dict[str, int]
    sentiment_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    avg_response_time: Optional[float]
    update_time: datetime

# Microsoft Graph API client
class MicrosoftGraphClient:
    """Client for interacting with Microsoft Graph API."""
    
    def __init__(self):
        self.client_id = settings.MICROSOFT_CLIENT_ID
        self.client_secret = settings.MICROSOFT_CLIENT_SECRET
        self.tenant_id = settings.MICROSOFT_TENANT_ID
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = settings.SCOPES
        
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        
        self.http_client = httpx.AsyncClient()
    
    async def get_access_token(self, authorization_code: str) -> Dict:
        """
        Get access token using authorization code.
        
        Args:
            authorization_code: OAuth authorization code
            
        Returns:
            Dict containing access token and related information
        """
        try:
            result = await asyncio.to_thread(
                self.msal_app.acquire_token_by_authorization_code,
                authorization_code,
                scopes=self.scopes,
                redirect_uri=settings.MICROSOFT_REDIRECT_URI
            )
            
            if "access_token" not in result:
                logger.error(f"Failed to get access token: {result.get('error_description')}")
                raise HTTPException(status_code=400, detail="Failed to get access token")
                
            return result
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_emails(self, access_token: str, limit: int = 50) -> List[Dict]:
        """
        Fetch emails from Microsoft Graph API.
        
        Args:
            access_token: Valid access token
            limit: Maximum number of emails to fetch
            
        Returns:
            List of email data dictionaries
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await self.http_client.get(
                "https://graph.microsoft.com/v1.0/me/messages",
                headers=headers,
                params={
                    "$top": limit,
                    "$select": "id,subject,sender,receivedDateTime,importance,body",
                    "$orderby": "receivedDateTime desc"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch emails: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch emails"
                )
                
            return response.json()["value"]
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

# Initialize FastAPI app
app = FastAPI(
    title="Email Analysis API",
    description="API for analyzing emails using Microsoft Graph API and AI models",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
graph_client = MicrosoftGraphClient()
email_analyzer = EmailAnalyzer()

# Dependency for database sessions
def get_db():
    """Database session dependency."""
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

# API routes
@app.post("/auth/microsoft")
async def microsoft_auth(code: str):
    """Handle Microsoft OAuth authentication."""
    return await graph_client.get_access_token(code)

@app.get("/emails")
async def get_analyzed_emails(
    access_token: str,
    limit: int = 50,
    filter_category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Fetch and analyze emails.
    
    Args:
        access_token: Valid Microsoft Graph access token
        limit: Maximum number of emails to fetch
        filter_category: Optional category filter
        db: Database session
        
    Returns:
        List of analyzed emails
    """
    try:
        emails = await graph_client.get_emails(access_token, limit)
        analyzed_emails = []
        
        for email in emails:
            # Check if email already analyzed
            existing_record = db.query(EmailRecord).filter_by(
                email_id=email["id"]
            ).first()
            
            if existing_record:
                analyzed_emails.append({
                    "email_id": existing_record.email_id,
                    "subject": existing_record.subject,
                    "analysis_results": existing_record.analysis_results,
                    "category": existing_record.category
                })
                continue
            
            # Analyze new email
            analysis_request = EmailAnalysisRequest(
                email_id=email["id"],
                subject=email["subject"],
                body=email["body"]["content"],
                sender=email["sender"]["emailAddress"]["address"],
                received_time=datetime.fromisoformat(
                    email["receivedDateTime"].replace('Z', '+00:00')
                ),
                importance=email["importance"]
            )
            
            analysis_results = await email_analyzer.analyze_email(analysis_request)
            
            # Store in database
            record = EmailRecord(
                email_id=email["id"],
                subject=email["subject"],
                sender=email["sender"]["emailAddress"]["address"],
                received_time=analysis_request.received_time,
                importance=email["importance"],
                analysis_results=analysis_results.dict(),
                category=analysis_results.category
            )
            db.add(record)
            analyzed_emails.append({
                "email_id": email["id"],
                "subject": email["subject"],
                "analysis_results": analysis_results.dict(),
                "category": analysis_results.category
            })
        
        db.commit()
        
        # Apply category filter if specified
        if filter_category:
            analyzed_emails = [
                email for email in analyzed_emails 
                if email["category"] == filter_category
            ]
        
        return analyzed_emails
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/metrics")
async def get_dashboard_metrics(
    access_token: str,
    db: Session = Depends(get_db)
) -> DashboardMetrics:
    """
    Get aggregated metrics for dashboard.
    
    Args:
        access_token: Valid Microsoft Graph access token
        db: Database session
        
    Returns:
        Dashboard metrics
    """
    try:
        # Get recent emails from database
        recent_emails = db.query(EmailRecord).order_by(
            EmailRecord.received_time.desc()
        ).limit(100).all()
        
        # Calculate metrics
        categories = {}
        sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
        priority_distribution = {"high": 0, "medium": 0, "low": 0}
        
        for email in recent_emails:
            # Update category counts
            categories[email.category] = categories.get(email.category, 0) + 1
            
            # Update sentiment distribution
            sentiment = email.analysis_results.get("sentiment", {}).get("label", "neutral")
            sentiment_distribution[sentiment.lower()] += 1
            
            # Update priority distribution
            priority_score = email.analysis_results.get("priority_score", 0)
            priority = "high" if priority_score > 0.7 else \
                      "medium" if priority_score > 0.3 else "low"
            priority_distribution[priority] += 1
        
        return DashboardMetrics(
            total_emails=len(recent_emails),
            categories=categories,
            sentiment_distribution=sentiment_distribution,
            priority_distribution=priority_distribution,
            avg_response_time=calculate_avg_response_time(recent_emails),
            update_time=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_avg_response_time(emails: List[EmailRecord]) -> Optional[float]:
    """Calculate average response time for emails."""
    response_times = []
    
    for email in emails:
        if email.analysis_results.get("response_time"):
            response_times.append(email.analysis_results["response_time"])
    
    return sum(response_times) / len(response_times) if response_times else None

if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
