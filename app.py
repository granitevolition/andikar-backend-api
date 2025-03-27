# Keep most of the file the same, but update the admin_dashboard function
# Only updating the admin_dashboard function, other code stays the same

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """
    Admin dashboard index page
    """
    if not templates:
        raise HTTPException(status_code=500, detail="Templates not configured")
    
    # Prepare dashboard stats
    stats = {}
    
    # User stats
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id)).filter(models.User.is_active == True).scalar() or 0
    
    # Get recent users
    recent_users = db.query(models.User).order_by(desc(models.User.joined_date)).limit(5).all()
    
    stats["users"] = {
        "total": total_users,
        "active": active_users,
        "recent": recent_users
    }
    
    # Transaction stats
    successful_payments = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.status == "completed"
    ).scalar() or 0
    
    pending_payments = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.status == "pending"
    ).scalar() or 0
    
    stats["transactions"] = {
        "successful": successful_payments,
        "pending": pending_payments,
        "total": successful_payments + pending_payments
    }
    
    # API stats
    total_requests = db.query(func.count(models.APILog.id)).scalar() or 0
    humanize_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/humanize"
    ).scalar() or 0
    detect_requests = db.query(func.count(models.APILog.id)).filter(
        models.APILog.endpoint == "/api/detect"
    ).scalar() or 0
    
    stats["api"] = {
        "total_requests": total_requests,
        "humanize_requests": humanize_requests,
        "detect_requests": detect_requests
    }
    
    # Chart data - Daily users
    days = 30
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days-1)
    
    daily_users = []
    daily_api_usage = []
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Count users joined on this date
        user_count = db.query(func.count(models.User.id)).filter(
            func.cast(models.User.joined_date, db.Date) == current_date
        ).scalar() or 0
        
        daily_users.append({
            "date": date_str,
            "count": user_count
        })
        
        # Count API requests on this date
        humanize_count = db.query(func.count(models.APILog.id)).filter(
            models.APILog.endpoint == "/api/humanize",
            func.cast(models.APILog.timestamp, db.Date) == current_date
        ).scalar() or 0
        
        detect_count = db.query(func.count(models.APILog.id)).filter(
            models.APILog.endpoint == "/api/detect",
            func.cast(models.APILog.timestamp, db.Date) == current_date
        ).scalar() or 0
        
        daily_api_usage.append({
            "date": date_str,
            "humanize": humanize_count,
            "detect": detect_count
        })
    
    charts = {
        "daily_users": json.dumps(daily_users),
        "daily_api_usage": json.dumps(daily_api_usage)
    }
    
    # System status
    system = {}
    
    # Check DB status
    try:
        db.execute(text("SELECT 1"))
        system["database"] = "healthy"
    except Exception:
        system["database"] = "unhealthy"
    
    # Check Humanizer API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HUMANIZER_API_URL}/", timeout=2.0)
            system["humanizer"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        system["humanizer"] = "unhealthy"
    
    # Check AI Detector (simulated)
    system["detector"] = "not_configured"
    
    # Check M-Pesa (simulated)
    system["mpesa"] = "healthy"
    
    # System info
    system["info"] = {
        "version": PROJECT_VERSION,
        "python_env": os.environ.get("PYTHON_ENV", "production"),
        "railway_project": os.environ.get("RAILWAY_PROJECT_NAME", "Not on Railway"),
        "railway_service": os.environ.get("RAILWAY_SERVICE_NAME", "Not on Railway")
    }
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "title": "Admin Dashboard",
        "user": current_user,
        "active_page": "dashboard",
        "stats": stats,
        "charts": charts,
        "system": system
    })
