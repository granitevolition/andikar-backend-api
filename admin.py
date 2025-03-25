from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List, Optional, Any, Union

# Import database and models
from database import get_db
import models
import schemas
from config import settings
from auth import get_admin_user

# Create router
admin_router = APIRouter(prefix="/admin")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Dashboard route
@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, 
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin dashboard main view"""
    
    # Get user stats
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id)).filter(models.User.is_active == True).scalar() or 0
    recent_users = db.query(models.User).order_by(desc(models.User.joined_date)).limit(5).all()
    
    # Get transaction stats
    total_transactions = db.query(func.count(models.Transaction.id)).scalar() or 0
    successful_transactions = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.status == "completed"
    ).scalar() or 0
    total_revenue = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.status == "completed"
    ).scalar() or 0
    
    # Get API usage stats
    total_requests = db.query(func.count(models.APILog.id)).scalar() or 0
    humanize_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/humanize"
    ).scalar() or 0
    detect_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/detect"
    ).scalar() or 0
    
    # Calculate daily stats for the past 30 days
    days = 30
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days-1)
    
    # Daily users query
    daily_users = []
    daily_api_usage = []
    
    # Generate the date series
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        
        # User registrations for this date
        user_count = db.query(func.count(models.User.id)).filter(
            func.date(models.User.joined_date) == current_date
        ).scalar() or 0
        
        daily_users.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "count": user_count
        })
        
        # API usage for this date
        usage = db.query(models.UsageStat).filter(
            models.UsageStat.year == current_date.year,
            models.UsageStat.month == current_date.month,
            models.UsageStat.day == current_date.day
        ).all()
        
        humanize_count = sum(stat.humanize_requests for stat in usage)
        detect_count = sum(stat.detect_requests for stat in usage)
        
        daily_api_usage.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "humanize": humanize_count,
            "detect": detect_count,
            "total": humanize_count + detect_count
        })
    
    # System health and info
    try:
        # Simple database query to verify connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    # Check if services are configured
    humanizer_configured = bool(settings.HUMANIZER_API_URL and 
                               settings.HUMANIZER_API_URL != "https://web-production-3db6c.up.railway.app")
    detector_configured = bool(settings.AI_DETECTOR_API_URL and 
                              settings.AI_DETECTOR_API_URL != "https://ai-detector-api.example.com")
    mpesa_configured = bool(settings.MPESA_CONSUMER_KEY and settings.MPESA_CONSUMER_SECRET)
    
    # Get system environment info
    system_info = {
        "version": settings.PROJECT_VERSION,
        "python_env": os.getenv("PYTHON_ENV", "production"),
        "railway_project": os.getenv("RAILWAY_PROJECT_NAME", "Not on Railway"),
        "railway_service": os.getenv("RAILWAY_SERVICE_NAME", "Not on Railway"),
    }
    
    # Create context for template
    context = {
        "request": request,
        "user": current_user,
        "stats": {
            "users": {
                "total": total_users,
                "active": active_users,
                "recent": recent_users
            },
            "transactions": {
                "total": total_transactions,
                "successful": successful_transactions,
                "revenue": total_revenue
            },
            "api": {
                "total_requests": total_requests,
                "humanize_requests": humanize_requests,
                "detect_requests": detect_requests
            }
        },
        "charts": {
            "daily_users": json.dumps(daily_users),
            "daily_api_usage": json.dumps(daily_api_usage)
        },
        "system": {
            "database": db_status,
            "humanizer": "configured" if humanizer_configured else "not_configured",
            "detector": "configured" if detector_configured else "not_configured",
            "mpesa": "configured" if mpesa_configured else "not_configured",
            "info": system_info
        }
    }
    
    return templates.TemplateResponse("admin/dashboard.html", context)

# Users management
@admin_router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    page: int = 1,
    query: str = None,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin users list view"""
    per_page = 10
    offset = (page - 1) * per_page
    
    # Filter by search query if provided
    users_query = db.query(models.User)
    total_users = users_query.count()
    
    if query:
        users_query = users_query.filter(
            (models.User.username.ilike(f"%{query}%")) |
            (models.User.email.ilike(f"%{query}%")) |
            (models.User.full_name.ilike(f"%{query}%"))
        )
    
    filtered_total = users_query.count()
    
    # Get pagination
    users = users_query.order_by(desc(models.User.joined_date)).offset(offset).limit(per_page).all()
    total_pages = (filtered_total + per_page - 1) // per_page if filtered_total > 0 else 1
    
    # Price plans for dropdown
    plans = db.query(models.PricingPlan).all()
    
    context = {
        "request": request,
        "user": current_user,
        "users": users,
        "plans": plans,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": filtered_total,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1,
            "next_page": page + 1
        },
        "search": {
            "query": query or "",
            "total": filtered_total,
            "all_total": total_users
        }
    }
    
    return templates.TemplateResponse("admin/users.html", context)

# User detail
@admin_router.get("/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    request: Request,
    user_id: str,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin user detail view"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's transactions
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).order_by(desc(models.Transaction.created_at)).all()
    
    # Get user's API logs
    api_logs = db.query(models.APILog).filter(
        models.APILog.user_id == user_id
    ).order_by(desc(models.APILog.timestamp)).limit(50).all()
    
    # Get user's stats
    usage_stats = db.query(models.UsageStat).filter(
        models.UsageStat.user_id == user_id
    ).order_by(
        desc(models.UsageStat.year),
        desc(models.UsageStat.month),
        desc(models.UsageStat.day)
    ).limit(30).all()
    
    # Get plans for dropdown
    plans = db.query(models.PricingPlan).all()
    
    context = {
        "request": request,
        "user": current_user,
        "target_user": user,
        "transactions": transactions,
        "api_logs": api_logs,
        "usage_stats": usage_stats,
        "plans": plans
    }
    
    return templates.TemplateResponse("admin/user_detail.html", context)

# Update user
@admin_router.post("/users/{user_id}/update")
async def admin_update_user(
    user_id: str,
    full_name: str = Form(None),
    plan_id: str = Form(None),
    is_active: bool = Form(False),
    payment_status: str = Form(None),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user from admin panel"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields
    if full_name is not None:
        user.full_name = full_name
    
    if plan_id is not None:
        # Check if plan exists
        plan = db.query(models.PricingPlan).filter(models.PricingPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=400, detail=f"Plan '{plan_id}' does not exist")
        user.plan_id = plan_id
    
    user.is_active = is_active
    
    if payment_status is not None:
        user.payment_status = payment_status
    
    db.commit()
    
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)

# Transactions list
@admin_router.get("/transactions", response_class=HTMLResponse)
async def admin_transactions(
    request: Request,
    page: int = 1,
    status: str = None,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin transactions list view"""
    per_page = 10
    offset = (page - 1) * per_page
    
    # Filter by status if provided
    transactions_query = db.query(models.Transaction)
    total_transactions = transactions_query.count()
    
    if status:
        transactions_query = transactions_query.filter(models.Transaction.status == status)
    
    filtered_total = transactions_query.count()
    
    # Get pagination
    transactions = transactions_query.order_by(
        desc(models.Transaction.created_at)
    ).offset(offset).limit(per_page).all()
    
    total_pages = (filtered_total + per_page - 1) // per_page if filtered_total > 0 else 1
    
    # Get users for reference
    user_ids = [t.user_id for t in transactions]
    users = {
        user.id: user for user in db.query(models.User).filter(models.User.id.in_(user_ids)).all() if user_ids
    }

    # Calculate summary statistics
    total_volume = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.status == "completed"
    ).scalar() or 0
    
    completed_count = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.status == "completed"
    ).scalar() or 0
    
    avg_amount = 0
    if completed_count > 0:
        avg_amount = round(total_volume / completed_count, 2)

    stats = {
        "total_volume": total_volume,
        "completed": completed_count,
        "average": avg_amount
    }
    
    context = {
        "request": request,
        "user": current_user,
        "transactions": transactions,
        "users": users,
        "stats": stats,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": filtered_total,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1,
            "next_page": page + 1
        },
        "filter": {
            "status": status or "all",
            "total": filtered_total,
            "all_total": total_transactions
        }
    }
    
    return templates.TemplateResponse("admin/transactions.html", context)

# API logs
@admin_router.get("/logs", response_class=HTMLResponse)
async def admin_logs(
    request: Request,
    page: int = 1,
    endpoint: str = None,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin API logs view"""
    per_page = 20
    offset = (page - 1) * per_page
    
    # Filter by endpoint if provided
    logs_query = db.query(models.APILog)
    total_logs = logs_query.count()
    
    if endpoint:
        logs_query = logs_query.filter(models.APILog.endpoint == endpoint)
    
    filtered_total = logs_query.count()
    
    # Get pagination
    logs = logs_query.order_by(desc(models.APILog.timestamp)).offset(offset).limit(per_page).all()
    total_pages = (filtered_total + per_page - 1) // per_page if filtered_total > 0 else 1
    
    # Get users for reference
    user_ids = [log.user_id for log in logs]
    users = {
        user.id: user for user in db.query(models.User).filter(models.User.id.in_(user_ids)).all() if user_ids
    }
    
    # Get available endpoints for filter
    endpoints = db.query(models.APILog.endpoint).distinct().all()
    endpoints = [e[0] for e in endpoints] if endpoints else []
    
    # Calculate statistics
    success_count = db.query(func.count(models.APILog.id)).filter(
        models.APILog.status_code == 200
    ).scalar() or 0
    
    client_error_count = db.query(func.count(models.APILog.id)).filter(
        models.APILog.status_code >= 400,
        models.APILog.status_code < 500
    ).scalar() or 0
    
    server_error_count = db.query(func.count(models.APILog.id)).filter(
        models.APILog.status_code >= 500
    ).scalar() or 0
    
    other_count = db.query(func.count(models.APILog.id)).filter(
        (models.APILog.status_code < 200) | 
        ((models.APILog.status_code >= 300) & (models.APILog.status_code < 400)) |
        (models.APILog.status_code == None)
    ).scalar() or 0
    
    avg_time = db.query(func.avg(models.APILog.processing_time)).scalar() or 0
    total_words = db.query(func.sum(models.APILog.request_size)).scalar() or 0
    
    success_rate = 0
    if total_logs > 0:
        success_rate = (success_count / total_logs) * 100
    
    endpoint_counts = {}
    for endpoint_name in endpoints:
        count = db.query(func.count(models.APILog.id)).filter(
            models.APILog.endpoint == endpoint_name
        ).scalar() or 0
        endpoint_counts[endpoint_name] = count
    
    endpoint_labels = list(endpoint_counts.keys())
    endpoint_values = list(endpoint_counts.values())
    
    stats = {
        "success_rate": success_rate,
        "avg_time": avg_time,
        "total_words": total_words,
        "status_counts": {
            "success": success_count,
            "client_error": client_error_count,
            "server_error": server_error_count,
            "other": other_count
        },
        "endpoint_labels": endpoint_labels,
        "endpoint_values": endpoint_values
    }
    
    context = {
        "request": request,
        "user": current_user,
        "logs": logs,
        "users": users,
        "endpoints": endpoints,
        "stats": stats,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": filtered_total,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1,
            "next_page": page + 1
        },
        "filter": {
            "endpoint": endpoint or "all",
            "total": filtered_total,
            "all_total": total_logs
        }
    }
    
    return templates.TemplateResponse("admin/logs.html", context)

# Settings page
@admin_router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin settings view"""
    # Get pricing plans
    plans = db.query(models.PricingPlan).all()
    
    # Get environment settings
    env_settings = {
        "HUMANIZER_API_URL": settings.HUMANIZER_API_URL,
        "AI_DETECTOR_API_URL": settings.AI_DETECTOR_API_URL,
        "MPESA_CONFIGURED": bool(settings.MPESA_CONSUMER_KEY),
        "RATE_LIMIT_REQUESTS": settings.RATE_LIMIT_REQUESTS,
        "RATE_LIMIT_PERIOD": settings.RATE_LIMIT_PERIOD,
        "VERSION": settings.PROJECT_VERSION
    }
    
    context = {
        "request": request,
        "user": current_user,
        "plans": plans,
        "settings": env_settings
    }
    
    return templates.TemplateResponse("admin/settings.html", context)

# Update pricing plan
@admin_router.post("/settings/plan/{plan_id}/update")
async def admin_update_plan(
    plan_id: str,
    name: str = Form(None),
    description: str = Form(None),
    price: float = Form(None),
    word_limit: int = Form(None),
    requests_per_day: int = Form(None),
    is_active: bool = Form(False),
    current_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update pricing plan"""
    plan = db.query(models.PricingPlan).filter(models.PricingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Update plan fields
    if name is not None:
        plan.name = name
    
    if description is not None:
        plan.description = description
    
    if price is not None:
        plan.price = price
    
    if word_limit is not None:
        plan.word_limit = word_limit
    
    if requests_per_day is not None:
        plan.requests_per_day = requests_per_day
    
    plan.is_active = is_active
    plan.updated_at = datetime.utcnow()
    
    db.commit()
    
    return RedirectResponse("/admin/settings", status_code=303)
