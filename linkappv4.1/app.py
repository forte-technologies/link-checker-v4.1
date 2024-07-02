import os
import logging
from flask import Flask, request, jsonify, render_template, send_file, Response
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

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/check_links', methods=['POST'])
def check_links():
    urls = request.form['urls'].split()
    download = request.args.get('download')

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    logger.info(f"Received request to check {len(urls)} URLs")

    valid_links = []
    invalid_links = []
    insignificant_content_links = []
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
                    insignificant_content_links.append(url)
            else:
                invalid_links.append(url)
        except requests.RequestException as e:
            logger.error(f"Error checking URL {url}: {str(e)}")
            invalid_links.append(url)

    data = {
        "total_urls": len(urls),
        "valid_links": len(valid_links),
        "invalid_links": len(invalid_links),
        "insignificant_content": len(insignificant_content_links),
    }

    if download == 'csv':
        return generate_csv(valid_links, invalid_links, links_with_articles, insignificant_content_links)
    else:
        return jsonify(data)

def generate_csv(valid_links, invalid_links, links_with_articles, insignificant_content_links):
    data = {
        "Valid Links": valid_links,
        "Invalid Links": invalid_links,
        "Links with Articles": links_with_articles,
        "Insignificant Content Links": insignificant_content_links,
    }

    df = pd.DataFrame(dict([(k, pd.Series(v)) for k,v in data.items()]))
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
    app.run(debug=True)
