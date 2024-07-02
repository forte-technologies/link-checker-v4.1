import os
import logging
from flask import Flask, request, jsonify, render_template, send_file
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
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
    if main_content:
        text = main_content.get_text(separator=' ', strip=True)
    else:
        text = soup.get_text(separator=' ', strip=True)

    words = text.split()
    word_count = len(words)

    logger.info(f"Word count: {word_count}")
    return word_count > 300

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_links', methods=['POST'])
def check_links():
    urls = request.form['urls'].split()
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    logger.info(f"Received request to check {len(urls)} URLs")

    valid_links = []
    invalid_links = []
    links_with_articles = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    for url in urls[:100]:  # Limit to first 100 URLs for safety
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url

        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                valid_links.append(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                if has_significant_content(soup):
                    links_with_articles.append(url)
            else:
                invalid_links.append(url)
        except requests.RequestException as e:
            logger.error(f"Error checking URL {url}: {str(e)}")
            invalid_links.append(url)

    data = {
        "Valid Links Count": [len(valid_links)],
        "Invalid Links Count": [len(invalid_links)],
        "Links with Articles Count": [len(links_with_articles)],
        "Valid Links": [', '.join(valid_links)],
        "Invalid Links": [', '.join(invalid_links)],
        "Links with Articles": [', '.join(links_with_articles)],
    }

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='links_analysis.csv'
    )

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run()