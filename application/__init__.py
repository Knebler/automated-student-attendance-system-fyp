from flask import Blueprint

def create_app(app):
    """Initialize the application with BCE structure"""
    
    # Import boundaries (Blueprints)
    from application.boundaries.main_boundary import main_bp
    from application.boundaries.auth_boundary import auth_bp
    from application.boundaries.attendance_boundary import attendance_bp
    from application.boundaries.dashboard_boundary import dashboard_bp
    from application.boundaries.institution_boundary import institution_bp
    from application.boundaries.admin_boundary import admin_bp
    # Dev tooling (only for development)
    try:
        from application.boundaries.dev_boundary import dev_bp
        has_dev = True
    except Exception:
        dev_bp = None
        has_dev = False
    
    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(institution_bp, url_prefix='/institution')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    if has_dev and dev_bp:
        # Register development endpoints under /dev
        app.register_blueprint(dev_bp, url_prefix='/dev')
    
    return app