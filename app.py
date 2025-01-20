from flask import Flask, request, jsonify
import instaloader
import os
import google.generativeai as genai
from gradio_client import Client, handle_file

app = Flask(__name__)

# Initialize Instaloader, Gradio client, and Gemini
L = instaloader.Instaloader()
gradio_client = Client("malavika-2016/scene_analysis")
genai.configure(api_key=os.getenv("GENAI_API_KEY"))  # Add your API key here
model = genai.GenerativeModel("gemini-1.5-flash")

# Function to generate a caption using Gradio API
def generate_caption_with_gradio(image_path):
    result = gradio_client.predict(handle_file(image_path), api_name="/predict")
    return result

# Function to generate description using Gemini
def generate_description_with_gemini(caller_name, caption, date_posted, image_caption):
    prompt = f"Consider '{caller_name}' as either a person’s name or a relationship the user has with them (e.g., 'Father', 'Daughter'). If '{caller_name}' is a name, assume it refers to that person directly. If '{caller_name}' refers to a relationship, understand it as such (e.g., 'Father' means the user’s father). Now, '{caller_name}' has posted on Instagram with this caption: '{caption}', on the date: '{date_posted}'. The image is described as: '{image_caption}'. Provide a summary of this post to the user as if they are receiving an update from their loved one, focusing on the key details and context for better understanding."


    response = model.generate_content(prompt)
    return response.text

@app.route('/download_latest', methods=['POST'])
def download_latest_post():
    # Get the Instagram username and caller name from the request
    insta_username = request.json.get('username')
    caller_name = request.json.get('caller_name')

    if not insta_username:
        return jsonify({"error": "Instagram username is required!"}), 400
    
    if not caller_name:
        return jsonify({"error": "Caller name is required!"}), 400

    try:
        # Load the profile using the given username
        profile = instaloader.Profile.from_username(L.context, insta_username)

        # Get the latest post from the profile
        latest_post = next(profile.get_posts())

        # Define the folder where posts are saved
        post_folder = insta_username  # Folder where the post will be saved
        L.download_post(latest_post, target=post_folder)

        # List files in the folder and find the most recent image
        downloaded_files = os.listdir(post_folder)
        image_files = [file for file in downloaded_files if file.endswith('.jpg') or file.endswith('.png')]

        if not image_files:
            return jsonify({"error": "No image files found in the downloaded post."}), 500

        # Sort the files by modification time and pick the most recent image
        image_files.sort(key=lambda x: os.path.getmtime(os.path.join(post_folder, x)), reverse=True)
        image_path = os.path.join(post_folder, image_files[0])

        # Get caption and date posted
        caption = latest_post.caption
        date_posted = latest_post.date_utc.strftime('%Y-%m-%d %H:%M:%S')

        # Generate the image caption using Gradio
        image_caption = generate_caption_with_gradio(image_path)

        # Generate the description using Gemini
        gemini_response = generate_description_with_gemini(caller_name, caption, date_posted, image_caption)

        return jsonify({
            "description": gemini_response
        }), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
