from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from models.database import get_db_session, User, Report
from models.schemas import AnalysisRequest, AnalysisJobResponse, AnalysisStatusResponse, ReportResponse
from utils.security import get_current_user
from utils.cache import set_job_status, get_job_status, get_job_result, set_job_result, cache_get, cache_set
from agents.crew import run_analysis

router = APIRouter()


def run_analysis_job(job_id: str, ticker: str, user_id: int):
    from models.database import SessionLocal

    db_session = SessionLocal()

    try:
        # Check report cache first, we don't run agents if we have a fresh result
        cached = cache_get(f"report:{ticker}")
        if cached:
            set_job_result(job_id, cached)
            set_job_status(job_id, "done")
            return

        # Run the four CrewAI agents
        report = run_analysis(ticker)

        # Cache the result for 1 hour so other users benefit
        cache_set(f"report:{ticker}", report, expire_seconds=3600)

        # Save permanently to PostgreSQL
        db_report = Report(user_id=user_id, ticker=ticker, company_name=report.get("company"), metrics=report.get("market_metrics"), ai_report=report)
        db_session.add(db_report)
        db_session.commit()

        # Mark job as done with the result
        set_job_result(job_id, report)
        set_job_status(job_id, "done")

    except Exception as e:
        set_job_status(job_id, "error")
        set_job_result(job_id, {"error": str(e)})

    finally:
        db_session.close()

# POST /analysis/analyze
# Starts the analysis process for a given ticker. Returns a job ID for polling status.

@router.post("/analyze", response_model=AnalysisJobResponse)
def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    ticker = request.ticker

    # If a fresh cached report exists, we still create a job
    # but it will complete almost instantly 
    job_id = str(uuid.uuid4())

    # Mark as running immediately so the first poll has something to read
    set_job_status(job_id, "running")

    # Queue the background task. now this returns instantly
    background_tasks.add_task(run_analysis_job, job_id=job_id, ticker=ticker,user_id=current_user.id)

    return AnalysisJobResponse(

        job_id=job_id,
        status="running",
        message=f"Analysis started for {ticker}. Poll /analysis/status/{job_id} for updates.",

    )


# GET /analysis/status/{job_id}
# Polling endpoint for frontend to check job status and get results when ready

@router.get("/status/{job_id}", response_model=AnalysisStatusResponse)
def get_analysis_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    ):
    job_status = get_job_status(job_id)

    # Job not found either expired (>10 min) or invalid ID
    if job_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired. Please start a new analysis.",
        )

    if job_status == "running":
        return AnalysisStatusResponse(job_id=job_id, status="running")

    if job_status == "error":
        error_data = get_job_result(job_id)
        return AnalysisStatusResponse(

            job_id=job_id,
            status="error",
            error=error_data.get("error", "Unknown error") if error_data else "Unknown error",

        )

    if job_status == "done":
        result = get_job_result(job_id)
        return AnalysisStatusResponse(

            job_id=job_id,
            status="done",
            result=result,

        )

    # Fallback 
    return AnalysisStatusResponse(job_id=job_id, status=job_status)


# GET /analysis/price-history/{ticker}
# For the Chart.js price chart on the dashboard

@router.get("/price-history/{ticker}")
def get_price_history(
    ticker: str,
    current_user: User = Depends(get_current_user),
    ):
    try:
        import yfinance as yf
        history = yf.Ticker(ticker).history(period="1y")

        if history.empty:
            raise HTTPException(status_code=404, detail=f"No price history for {ticker}")

        # Chart.js needs two arrays - labels (dates) and data (prices)
        return {

            "ticker": ticker,
            "labels": [str(date.date()) for date in history.index],
            "prices": [round(float(price), 2) for price in history["Close"]],

        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET /analysis/history
# Returns the logged-in user's past reports

@router.get("/history", response_model=list[ReportResponse])
def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    ):
    reports = (db_session.query(Report)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .limit(20)
        .all()
    )

    return reports