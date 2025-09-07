# app.py
import os
import logging
from flask import Flask, request, jsonify
from meta import PostToFacebookPage

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def build_poster_from_headers():
    """Build PostToFacebookPage instance using headers"""
    app_id = request.headers.get("X-APP-ID")
    app_secret = request.headers.get("X-APP-SECRET")
    page_id = request.headers.get("X-PAGE-ID")
    token = request.headers.get("X-ACCESS-TOKEN")

    if not all([app_id, app_secret, page_id, token]):
        return None, jsonify({
            "error": "Missing one of required headers: X-APP-ID, X-APP-SECRET, X-PAGE-ID, X-ACCESS-TOKEN"
        }), 400

    poster = PostToFacebookPage(app_id, app_secret, page_id, token)
    return poster, None, None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/fb/post-images', methods=['POST'])
def fb_post_images():
    poster, err_resp, code = build_poster_from_headers()
    if err_resp: return err_resp, code

    payload = request.get_json() or {}
    posts = payload.get('posts')
    if not posts or not isinstance(posts, list):
        return jsonify({'error': 'posts list is required'}), 400

    try:
        results = poster.fb_post_images(posts)
        return jsonify({'results': results}), 200
    except Exception as e:
        logging.exception("fb_post_images failed")
        return jsonify({'error': str(e)}), 500

@app.route('/fb/upload-reel', methods=['POST'])
def fb_upload_reel():
    poster, err_resp, code = build_poster_from_headers()
    if err_resp: return err_resp, code

    payload = request.get_json() or {}
    video_url = payload.get('video_url')
    caption = payload.get('caption', '')

    if not video_url:
        return jsonify({'error': 'video_url required'}), 400

    try:
        success = poster.fb_upload_reel(video_url, caption)
        return jsonify({'success': bool(success)}), (200 if success else 500)
    except Exception as e:
        logging.exception("upload_reel failed")
        return jsonify({'error': str(e)}), 500

@app.route('/ig/post-carousel', methods=['POST'])
def ig_post_carousel():
    poster, err_resp, code = build_poster_from_headers()
    if err_resp: return err_resp, code

    payload = request.get_json() or {}
    posts = payload.get('posts')
    if not posts:
        return jsonify({'error': 'posts list required'}), 400

    try:
        result = poster.ig_post_carousel(posts)
        return jsonify(result)
    except Exception as e:
        logging.exception("carousel failed")
        return jsonify({'error': str(e)}), 500
    
@app.route('/ig/post-image', methods=['POST'])
def ig_post_image():
    poster, err_resp, code = build_poster_from_headers()
    if err_resp: return err_resp, code

    payload = request.get_json() or {}
    image_url = payload.get('image_url')
    caption = payload.get('caption', '')
    if not image_url:
        return jsonify({'error': 'Image url required'}), 400

    try:
        result = poster.ig_post_image(image_url, caption)
        return jsonify(result)
    except Exception as e:
        logging.exception("carousel failed")
        return jsonify({'error': str(e)}), 500
    

@app.route('/ig/upload-reel', methods=['POST'])
def ig_upload_reel():
    poster, err_resp, code = build_poster_from_headers()
    if err_resp: return err_resp, code

    payload = request.get_json() or {}
    video_url = payload.get('video_url')
    caption = payload.get('caption', '')

    if not video_url:
        return jsonify({'error': 'video_url required'}), 400

    try:
        result = poster.ig_upload_reel(video_url, caption)
        return jsonify(result)
    except Exception as e:
        logging.exception("ig_post failed")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 4000)))