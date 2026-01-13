from flask import Blueprint, render_template, request, Response, current_app
from application.boundaries.dev_actions import get_actions, get_action

dev_bp = Blueprint('dev', __name__)


@dev_bp.route('/test-endpoint', methods=['GET', 'POST'])
def test_endpoint():
    """Dev-only testing page: POST a message and receive it back as plain text.

    Methods:
      - GET: renders a simple form for developers
      - POST: returns the raw message body as text/plain so it can be consumed/inspected
    """
    if request.method == 'POST':
        # The UI posts an `action` parameter determining which helper to run
        action = request.form.get('action') or request.args.get('action')

        # dispatch via registry
        try:
            meta = None
            if action:
                meta = get_action(action)

            if not meta:
                return Response(f"Unknown action: {action}", mimetype='text/plain', status=400)

            func = meta.get('func')
            # build kwargs from declared params
            params = {}
            import json
            for p in meta.get('params', []):
                name = p.get('name')
                if name:
                    raw = request.form.get(name)
                    # try to coerce JSON-like strings or integers when applicable
                    if raw is None:
                        params[name] = None
                    else:
                        raw = raw.strip()
                        if (raw.startswith('{') and raw.endswith('}')) or (raw.startswith('[') and raw.endswith(']')):
                            try:
                                params[name] = json.loads(raw)
                            except Exception:
                                params[name] = raw
                        else:
                            # coerce integer-looking values
                            if raw.isdigit():
                                params[name] = int(raw)
                            else:
                                params[name] = raw

            # call the function with current_app as first arg
            result = func(current_app, **params)

            # Normalize responses: dicts -> readable text + status code based on 'success'
            if isinstance(result, dict):
                status_code = 200 if result.get('success') else 400
                return Response(str(result), mimetype='text/plain', status=status_code)

            return Response(str(result), mimetype='text/plain')

        except Exception as e:
            current_app.logger.exception('Dev endpoint exception')
            return Response(f"Error: {e}", mimetype='text/plain', status=500)

    # GET: render a simple developer form
    # Ensure known control modules are imported so module-level register_action hooks run
    try:
        import importlib
        # Attempt to import controls so their register_action calls execute
        for m in ['application.controls.database_control',
              'application.controls.auth_control',
              'application.controls.attendance_control',
              'application.controls.institution_control',
              # also import boundary modules that register dev actions
              'application.boundaries.attendance_boundary',
              'application.boundaries.auth_boundary',
              # include main boundary which registers init_database
              'application.boundaries.main_boundary']:
            try:
                importlib.import_module(m)
            except Exception:
                # ignore import-time errors in environments where DB is not configured
                current_app.logger.debug(f'Failed to import {m} for dev registry: ignore')
    except Exception:
        # safest fallback: do nothing
        pass

    actions = get_actions()
    return render_template('dev/test_endpoint.html', actions=actions)
