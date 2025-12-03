from flask import Blueprint, render_template, request, Response, current_app

dev_bp = Blueprint('dev', __name__)


@dev_bp.route('/test-endpoint', methods=['GET', 'POST'])
def test_endpoint():
    """Dev-only testing page: POST a message and receive it back as plain text.

    Methods:
      - GET: renders a simple form for developers
      - POST: returns the raw message body as text/plain so it can be consumed/inspected
    """
    if request.method == 'POST':
        # Read `message` field (form) or request data bytes
        msg = request.form.get('message')
        if msg is None:
            # fallback to raw body
            try:
                msg = request.get_data(as_text=True) or ''
            except Exception:
                msg = ''

        # Return plain text for easy development inspection
        return Response(msg, mimetype='text/plain')

    # GET: render a simple developer form
    return render_template('dev/test_endpoint.html')
