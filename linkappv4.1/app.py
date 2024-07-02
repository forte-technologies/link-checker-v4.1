from flask import Flask, request, jsonify, render_template, send_file, Response
from bs4 import BeautifulSoup
import requests
import pandas as pd
from io import BytesIO

app = Flask(__name__)

def has_significant_content(soup):
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
    if main_content:
        text = main_content.get_text(separator=' ', strip=True)
    else:
        text = soup.get_text(separator=' ', strip=True)

    return len(text.split()) > 300

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
    errors = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    for url in urls:
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url

        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                if has_significant_content(soup):
                    valid_links.append(url)
                else:
                    links_with_articles.append(url)
            else:
                invalid_links.append((url, response.status_code))
        except requests.RequestException as e:
            invalid_links.append((url, str(e)))

    df = pd.DataFrame({
        "URL": [url for url, _ in invalid_links] + valid_links + links_with_articles,
        "Status": ["Invalid: " + str(code) for _, code in invalid_links] + ["Valid"] * len(valid_links) + ["Insignificant content"] * len(links_with_articles)
    })

    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        attachment_filename="url_analysis.csv"
    )

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)

