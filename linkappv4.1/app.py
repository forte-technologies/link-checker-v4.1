import os
import logging
from flask import Flask, request, jsonify, render_template, send_file, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = app.logger

def has_significant_content(soup):
    text = soup.get_text(separator=' ', strip=True)
    words = text.split()
    word_count = len(words)
    return word_count > 300

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_links', methods=['POST'])
def check_links():
    urls = request.form['urls'].split()
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    valid_links = []
    invalid_links = []
    links_with_articles = []
    error_details = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    for url in urls:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                valid_links.append(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                if has_significant_content(soup):
                    links_with_articles.append(url)
            else:
                invalid_links.append(url)
                error_details.append(f"{url} - HTTP {response.status_code}")
        except requests.RequestException as e:
            invalid_links.append(url)
            error_details.append(f"{url} - Exception {str(e)}")

    data = {
        "total_urls": len(urls),
        "valid_links": len(valid_links),
        "invalid_links": len(invalid_links),
        "insignificant_content": len(urls) - len(links_with_articles),
        "valid_urls": valid_links,
        "invalid_urls": invalid_links,
        "urls_with_articles": links_with_articles
    }

    return jsonify(data)  # Return JSON data for AJAX call

@app.route('/download_csv', methods=['GET'])
def download_csv():
    # Retrieve data stored in session or another store (need to implement storage logic)
    data = session.get('last_check_results', {})
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='links_analysis.csv')

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run()


