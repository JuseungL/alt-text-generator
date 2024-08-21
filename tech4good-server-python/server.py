from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI 
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup # 크롤링

app = Flask(__name__)
CORS(app)  # CORS 설정 추가

MODEL="gpt-4o-mini"

@app.route('/')
def home():
    return 'Server is running!'

@app.route('/generate-alt-text', methods=['POST'])
def generate_alt_text():
    print("Received request")  
    data = request.json
    image_url = data.get('imageUrl')
    print(image_url)

    if not image_url:
        return jsonify({'error': 'Image URL is required'}), 400

    try:
        # OpenAI API 호출
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Generate detailed and descriptive alt text for the given image that is easy for visually impaired users to understand."},
                {"role": "user", "content": [
                    {"type": "text", 
                     "text":  """
                                시각장애인들을 위해 입력받은 이미지를 분석하여서 너무 길지 않게 중요 정보만 뽑아서 사람이 이해하기 쉽게 이미지를 잘 설명해주세요.
                                이미지에 텍스트가 있는 경우 중요 정보를 모두 뽑아서 출력해주는 대신에 출력값을 시각장애인이 음성으로 듣기 때문에 듣고 이해하는데 지장없어야해
                                예를들어 사이즈라면 S,M,L,XL, 어깨너비 30,40,50,60, 소매길이 60,66,70,75 이런식으로 무작정 나열된대로 읽지말고 S 사이즈 어깨너비 30, 소매길이 60, M사이즈 어깨너비 40, 소매길이 66 이런식으로 사람이 이해하기 쉽게 텍스트로 풀어 출력해주세요.

                                단순 이미지의 경우 그 이미지에 대해 최대한 구체적으로 설명해줬으면 좋겠어 이때 너무 답변이 길진 않았으면해.
                                한국어로 출력되어야한다. 
                                """
                    },
                    {"type": "image_url", "image_url": {
                        "url": image_url}
                    }
                ]}
            ],
            temperature=0.0,
        )
        print(response)
        alt_text = response.choices[0].message.content.strip()
        return jsonify({'altText': alt_text})

    except OpenAI.error.OpenAIError as e:
        return jsonify({'error': 'Failed to generate alt text', 'details': str(e)}), 500
    

def get_html_content(url):
    try:
        # Selenium 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 브라우저 창을 열지 않음
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        driver.get(url)
        html_content = driver.page_source
        
        driver.quit()
        return html_content
    except Exception as e:
        print(f"Error fetching HTML content: {e}")
        return None

@app.route('/summarize-html', methods=['POST'])
def summarize_html():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        # URL로부터 HTML 콘텐츠 가져오기
        html_content = get_html_content(url)
        if html_content is None:
            return jsonify({'error': 'Failed to retrieve HTML content'}), 500
    
        # HTML 파싱
        soup = BeautifulSoup(html_content, 'html.parser')
        head_text = soup.head.get_text(separator=' ', strip=True) if soup.head else ""
        body_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
        # 요약할 텍스트 준비
        full_text = f"Head: {head_text}\nBody: {body_text}"
        
        # OpenAI API를 사용해 요약 생성
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Summarize the following HTML content into 2~3 concise sentences. 이때 한국어로 반환해줘."},
                {"role": "user", "content": full_text}
            ],
            temperature=0.7,
        )
        summary = response.choices[0].message.content.strip()
    
        return jsonify({'summary': summary})

    except OpenAI.error.OpenAIError as e:
        return jsonify({'error': 'Failed to summarize HTML', 'details': str(e)}), 500
    except Exception as e:
        # 포괄적인 에러 핸들링
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)