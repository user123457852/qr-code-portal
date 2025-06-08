# main.py
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

import pprint
from app import create_app
from app.qr import generate_static_qrcodes

# Create the Flask application using factory
app = create_app()

# Debug helper: print all registered routes at startup
pprint.pprint({rule.rule: rule.endpoint for rule in app.url_map.iter_rules()})

if __name__ == '__main__':
    # Generate static QR codes (e.g., for the login page) when the app starts.
    generate_static_qrcodes()
    # Run on all interfaces port 8080, with debug mode on
    app.run(host="0.0.0.0", port=8080, debug=True)
