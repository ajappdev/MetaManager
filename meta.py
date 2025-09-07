import requests  # Import the requests library to handle HTTP requests
import os
import time
import json

class PostToFacebookPage():
    def __init__(self, app_id, app_secret, page_id, long_lived_token_file):
        self.app_id = app_id
        self.app_secret = app_secret
        self.page_id = page_id
        self.long_lived_token_file = long_lived_token_file

    def refresh_long_lived_token(self, current_long_lived_token):
        """
        Refresh a long-lived user access token before it expires.
        """
        url = 'https://graph.facebook.com/oauth/access_token'
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': current_long_lived_token
        }

        response = requests.get(url, params=params)
        data = response.json()

        if 'access_token' in data:
            print(data['access_token'])
            return data['access_token']
        else:
            print("Failed to refresh long-lived token:", data)
            return None

    def get_page_access_token(self, user_access_token):
        """
        Function to retrieve the Page Access Token using the user access token and page ID.
        """

        api_url_token = f'https://graph.facebook.com/{self.page_id}?fields=access_token&access_token={user_access_token}'
        
        try:
            # Make a GET request to the Facebook Graph API to fetch the Page Access Token
            response = requests.get(api_url_token)
            response.raise_for_status()  # Raise an exception if the request returns an HTTP error

            # Parse the response as JSON and return the access token
            data = response.json()
            return data['access_token']
        
        except requests.exceptions.RequestException as e:
            # Handle any exceptions (e.g., network issues, API errors) and print the error
            print("Error:", e)
            return None  # Return None if the access token retrieval fails
        
    def fb_post_images(self, posts: list):
        """
        Function to publish a post to the Facebook Page using the Page Access
        Token.
        """

        new_long_lived_token = self.refresh_long_lived_token(self.long_lived_token_file)
        page_access_token = self.get_page_access_token(new_long_lived_token)

        media_fbids = []

        for post in posts:
            image_url = post['image_url']
            upload_url = f"https://graph.facebook.com/{self.page_id}/photos"
            upload_payload = {
                'url': image_url,
                'published': 'false',
                'access_token': page_access_token
            }

            upload_response = requests.post(upload_url, data=upload_payload)
            try:
                upload_data = upload_response.json()
            except Exception as e:
                print("Error parsing upload response:", upload_response.text)
                continue

            if 'id' in upload_data:
                media_fbids.append({'media_fbid': upload_data['id']})
            else:
                print("Failed to upload image:", upload_data)

        # Final post with all images
        if media_fbids:
            post_url = f"https://graph.facebook.com/{self.page_id}/feed"
            post_payload = {
                'access_token': page_access_token,
                'message': post['caption']
            }

            for i, media in enumerate(media_fbids):
                post_payload[f'attached_media[{i}]'] = str(media)

            final_response = requests.post(post_url, data=post_payload)
            if final_response.status_code == 200:
                print("🎉 Multi-image post published to Facebook!")
            else:
                print("❌ Failed to publish multi-image post:", final_response.text)
    

    def fb_upload_reel(self, video_url: str, caption: str = "") -> bool:
        """
        Uploads a Reel video to a Facebook Page as a Reel post from an S3 URL.
        Requires video to follow Facebook's specifications for Reels.
        """
        new_long_lived_token = self.refresh_long_lived_token(self.long_lived_token_file)
        page_access_token = self.get_page_access_token(new_long_lived_token)

        # Step 1: Initialize upload
        start_upload_url = f"https://graph.facebook.com/v22.0/{self.page_id}/video_reels"
        start_payload = {
            "upload_phase": "start",
            "access_token": page_access_token
        }

        start_response = requests.post(start_upload_url, json=start_payload)
        if start_response.status_code != 200:
            print("❌ Failed to start video upload:", start_response.text)
            return False

        upload_data = start_response.json()
        video_id = upload_data["video_id"]
        upload_url = upload_data["upload_url"]

        # Step 2: Download video from S3 and upload to rupload.facebook.com
        try:
            # Download video from S3 URL
            video_response = requests.get(video_url, stream=True)
            if video_response.status_code != 200:
                print("❌ Failed to download video from S3:", video_response.status_code)
                return False

            # Get video data and file size
            video_data = video_response.content
            file_size = len(video_data)

            headers = {
                "Authorization": f"OAuth {page_access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }

            upload_response = requests.post(upload_url, headers=headers, data=video_data)
            if upload_response.status_code != 200:
                print("❌ Video upload failed:", upload_response.text)
                return False
        except Exception as e:
            print("❌ Exception during video download/upload:", e)
            return False

        # Step 3: Finish upload
        finish_url = f"https://graph.facebook.com/v22.0/{self.page_id}/video_reels"
        finish_payload = {
            "upload_phase": "finish",
            "video_id": video_id,
            "access_token": page_access_token,
            "video_state":"PUBLISHED"
        }
        if caption:
            finish_payload["description"] = caption

        finish_response = requests.post(finish_url, json=finish_payload)
        if finish_response.status_code == 200:
            print("🎉 Reel successfully uploaded to Facebook!")
            return True
        else:
            print("❌ Failed to finalize reel upload:", finish_response.text)
            return False
                            
    def get_instagram_account_id(self, page_access_token):
        """
        Function to get the Instagram Business Account ID linked to the Facebook Page.
        """
        url = f'https://graph.facebook.com/{self.page_id}?fields=instagram_business_account&access_token={page_access_token}'
        
        response = requests.get(url)
        data = response.json()
        if 'instagram_business_account' in data:
            return data['instagram_business_account']['id']
        else:
            print("Instagram Business Account not found:", data)
            return None

    def ig_post_carousel(self, posts: list):
        """
        Function to publish a carousel to the Instagram Business Account.
        """
        post_posted = False

        new_long_lived_token = self.refresh_long_lived_token(self.long_lived_token_file)
        page_access_token = self.get_page_access_token(new_long_lived_token)
        instagram_account_id = self.get_instagram_account_id(page_access_token)

        if not instagram_account_id:
            print("Instagram account ID not found.")
            return False

        # Step 1: Upload each image with is_carousel_item=true
        creation_ids = []

        for post in posts:
            image_url = post['image_url']
            create_image_url = f'https://graph.facebook.com/{instagram_account_id}/media'
            image_payload = {
                'image_url': image_url,
                'is_carousel_item': 'true',
                'access_token': page_access_token
            }

            img_response = requests.post(create_image_url, data=image_payload)

            try:
                img_data = img_response.json()
            except Exception as e:
                print("Failed to parse image response:", img_response.text)
                continue

            if 'id' in img_data:
                creation_ids.append(img_data['id'])
            else:
                print("Image upload failed:", img_data)

        if not creation_ids:
            print("No images were uploaded.")
            return False

        # Step 2: Create carousel container
        create_carousel_url = f'https://graph.facebook.com/{instagram_account_id}/media'
        carousel_payload = {
            'media_type': 'CAROUSEL',
            'children': ','.join(creation_ids),
            'caption': posts[0]['caption'] if posts else '',
            'access_token': page_access_token
        }

        carousel_response = requests.post(create_carousel_url, data=carousel_payload)

        try:
            carousel_data = carousel_response.json()
        except Exception as e:
            print("Failed to parse carousel response:", carousel_response.text)
            return False

        if 'id' not in carousel_data:
            print("Carousel creation failed:", carousel_data)
            return False

        carousel_id = carousel_data['id']

        # Step 3: Publish carousel
        publish_url = f'https://graph.facebook.com/{instagram_account_id}/media_publish'
        publish_payload = {
            'creation_id': carousel_id,
            'access_token': page_access_token
        }

        publish_response = requests.post(publish_url, data=publish_payload)

        if publish_response.status_code == 200:
            print("🎉 Carousel successfully published to Instagram!")
            post_posted = True
        else:
            print(f"❌ Failed to publish carousel: {publish_response.text}")

        return post_posted

    def ig_post_image(self, image_url: str, caption: str = ""):
        """
        Function to publish an image to the Instagram Business Account.
        """
        post_posted = False

        new_long_lived_token = self.refresh_long_lived_token(self.long_lived_token_file)
        page_access_token = self.get_page_access_token(new_long_lived_token)
        instagram_account_id = self.get_instagram_account_id(page_access_token)

        if not instagram_account_id:
            print("Instagram account ID not found.")
            return False

        # Step 1: Create a Media Object
        create_media_url = f'https://graph.facebook.com/{instagram_account_id}/media'
        media_payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': page_access_token
        }

        media_response = requests.post(create_media_url, data=media_payload)
        media_data = media_response.json()

        if 'id' in media_data:
            creation_id = media_data['id']

            # Step 2: Publish the Media Object
            publish_url = f'https://graph.facebook.com/{instagram_account_id}/media_publish'
            publish_payload = {
                'creation_id': creation_id,
                'access_token': page_access_token
            }

            publish_response = requests.post(publish_url, data=publish_payload)

            if publish_response.status_code == 200:
                print("Post successfully published to Instagram!")
                post_posted = True
            else:
                print(f"Failed to publish post: {publish_response.status_code}")
                print(publish_response.json())
        else:
            print("Failed to create media object:", media_data)
            
        return post_posted

    def ig_upload_reel(self, video_url, video_caption):

        new_long_lived_token = self.refresh_long_lived_token(self.long_lived_token_file)
        page_access_token = self.get_page_access_token(new_long_lived_token)

        # Get Instagram account ID
        try:
            instagram_account_id = self.get_instagram_account_id(page_access_token)
            if not instagram_account_id:
                print("Failed to get Instagram account ID.")
                return False
        except Exception as e:
            print(f"Error getting Instagram account ID: {str(e)}")
            return False

        try:
            # Create media container
            create_media_url = f"https://graph.facebook.com/v20.0/{instagram_account_id}/media"
            media_payload = {
                "video_url": video_url,
                "caption": video_caption,
                "media_type": "REELS",
                "share_to_feed": "true",  # Ensure Reel appears in feed
                "access_token": page_access_token
            }

            media_response = requests.post(create_media_url, data=media_payload)
            media_data = media_response.json()

            if media_response.status_code != 200 or "id" not in media_data:
                print(f"Failed to create media object: {json.dumps(media_data, indent=2)}")
                print(f"Status Code: {media_response.status_code}")
                return
            
            creation_id = media_data["id"]

            # Poll for media processing status
            status_url = f"https://graph.facebook.com/{creation_id}?fields=status_code,status&access_token={page_access_token}"
            for attempt in range(50):  # Up to ~250 seconds
                time.sleep(5)
                status_response = requests.get(status_url)
                status_data = status_response.json()

                status_code = status_data.get("status_code")
                print(f"Attempt {attempt + 1}: Status - {status_code}")

                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    print(f"Media processing failed: {json.dumps(status_data, indent=2)}")
                    return False
                elif status_response.status_code != 200:
                    print(f"Polling error: {json.dumps(status_data, indent=2)}")
                    return False
            else:
                print("Media processing timed out after 50 seconds.")
                return False

            # Publish the Reel
            publish_url = f"https://graph.facebook.com/v20.0/{instagram_account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": page_access_token
            }

            publish_response = requests.post(publish_url, data=publish_payload)
            publish_data = publish_response.json()

            if publish_response.status_code == 200 and "id" in publish_data:
                print("Reel successfully published to Instagram!")
                return True
            else:
                print(f"Failed to publish Reel: {json.dumps(publish_data, indent=2)}")
                print(f"Status Code: {publish_response.status_code}")
                return False

        except Exception as e:
            print(f"Error processing post {post_url}: {str(e)}")
            return False

    # Step 1: Get the hashtag ID
    def post_comments_about_hashtag(self, hashtag):
        try:
            current_long_lived_token = self.read_access_token()
        except Exception as e:
            print(f"Error reading access token: {str(e)}")
            return False

        if not current_long_lived_token:
            print("No valid access token found.")
            return False

        # Refresh long-lived token
        try:
            new_long_lived_token = self.refresh_long_lived_token(current_long_lived_token)
            if not new_long_lived_token:
                print("Failed to refresh long-lived token.")
                return False
            self.save_access_token(new_long_lived_token)
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            return False

        # Get page access token
        try:
            page_access_token = self.get_page_access_token(new_long_lived_token)
            if not page_access_token:
                print("Failed to get page access token.")
                return False
        except Exception as e:
            print(f"Error getting page access token: {str(e)}")
            return False

        # Get Instagram account ID
        try:
            instagram_account_id = self.get_instagram_account_id(page_access_token)
            if not instagram_account_id:
                print("Failed to get Instagram account ID.")
                return False
        except Exception as e:
            print(f"Error getting Instagram account ID: {str(e)}")
            return False

        url = f"https://graph.facebook.com/v22.0/ig_hashtag_search"
        params = {
            "user_id": instagram_account_id,
            "q": hashtag,
            "access_token": page_access_token
        }
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("data") and len(data["data"]) > 0:
            hashtag_id = data["data"][0]["id"]
        else:
            print(f"Hashtag '{hashtag}' not found.")
            return
        
        if hashtag_id:
            url = f"https://graph.facebook.com/v22.0/{hashtag_id}/recent_media"
            params = {
                "user_id": instagram_account_id,
                "fields": "id,caption,like_count,permalink,media_type",
                "access_token": page_access_token
            }
            response = requests.get(url, params=params)
            data = response.json()
            recent_media_with_hashtag = data.get("data", [])
            if not recent_media_with_hashtag:
                print("No media found for the hashtag.")
                return

            # Sort media by like_count to get "top" posts
            sorted_media = sorted(recent_media_with_hashtag, key=lambda x: x.get("like_count", 0), reverse=True)

            # Process top 5 media (or all if fewer than 5)
            top_media = sorted_media[:5]
            print(top_media)
            for media in top_media:
                media_id = media["id"]
                caption = media.get("caption", "No caption")
                like_count = media.get("like_count", 0)
                permalink = media.get("permalink", "")
                media_type = media.get("media_type", "")

                print(f"\nMedia ID: {media_id}")
                print(f"Permalink: {permalink}")

                # Post a comment
                comment_result = self.post_comment(media_id, "Good post", page_access_token)
                if "id" in comment_result:
                    print(f"Comment posted successfully: {comment_result}")
                else:
                    print(f"Failed to post comment: {comment_result}")


    # Step 3: Post a comment on a media object
    def post_comment(self,media_id, comment_message, access_token):
        url = f"https://graph.facebook.com/{media_id}/comments?message={comment_message}"
        params = {
            "access_token": access_token
        }
        response = requests.post(url, params=params)
        return response.json()