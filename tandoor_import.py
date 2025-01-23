import requests
import json
from typing import Dict, Any
import time

class TandoorRecipeImporter:
    def __init__(self, username: str, password: str, base_url: str = "https://tandoor.your.domain"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = self._get_auth_token(username, password)
        self.headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }

    def _get_auth_token(self, username: str, password: str) -> str:
        """Authentication with Tandoor and token generation"""
        auth_url = f"{self.base_url}/api-token-auth/"
        data = {'username': username, 'password': password}
        response = requests.post(auth_url, data=data)
        if response.status_code == 200:
            return response.json()['token']
        raise Exception(f"Authentication failed: {response.text}")

    def _transform_recipe(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform recipe into Tandoor format"""
        ingredients = []
        if recipe_data.get('ingredientGroups'):
            for group in recipe_data['ingredientGroups']:
                for ing in group['ingredients']:
                    ingredients.append({
                        'food': {'name': ing['name']},
                        'amount': str(ing['amount']) if ing['amount'] != 0 else "",
                        'unit': {'name': ing['unit']} if ing['unit'] else None,
                        'note': ing.get('usageInfo', '')
                    })

        # Split instructions into individual steps
        instructions = recipe_data.get('instructions', '').split('\r\n\r\n')
        steps = [{'instruction': step.strip(), 'ingredients': []} for step in instructions if step.strip()]

        # Create keywords from tags and filter empty tags
        keywords = [{'name': tag} for tag in recipe_data.get('tags', []) if tag and tag.strip()]
        keywords.append({'name': 'pyimport'})

        return {
            'name': recipe_data['title'],
            'description': recipe_data.get('additionalDescription', ''),
            'keywords': keywords,
            'steps': steps,
            'working_time': recipe_data.get('preparationTime', 0),
            'source_url': recipe_data.get('siteUrl', ''),
            'servings': recipe_data.get('servings', 0),
            'private': False
        }

    def import_recipe(self, recipe_json: Dict[str, Any]) -> None:
        """Import a single recipe into Tandoor"""
        try:
            # Transform recipe
            tandoor_recipe = self._transform_recipe(recipe_json)
            
            # Create recipe
            response = self.session.post(
                f"{self.base_url}/api/recipe/",
                headers=self.headers,
                json=tandoor_recipe
            )
            
            if response.status_code != 201:
                print(f"Error creating recipe {recipe_json['title']}: {response.text}")
                return

            recipe_id = response.json()['id']

            # Add image if available
            if recipe_json.get('previewImageUrlTemplate'):
                try:
                    # Create image URL and download image
                    image_url = recipe_json['previewImageUrlTemplate'].replace('<format>', 'crop-642x428')
                    image_response = requests.get(image_url)
                    
                    if image_response.status_code == 200:
                        # Prepare multipart form-data
                        files = {
                            'image': ('image.jpg', image_response.content, 'image/jpeg'),
                            'image_url': (None, image_url)
                        }
                        
                        # Upload image
                        image_upload_response = self.session.put(
                            f"{self.base_url}/api/recipe/{recipe_id}/image/",
                            headers={'Authorization': f'Token {self.auth_token}'},
                            files=files
                        )
                        
                        if image_upload_response.status_code != 200:
                            print(f"Error adding image for {recipe_json['title']}")
                    else:
                        print(f"Error downloading image for {recipe_json['title']}")
                        
                except Exception as e:
                    print(f"Error during image upload for {recipe_json['title']}: {str(e)}")

            print(f"Recipe '{recipe_json['title']}' successfully imported")
            time.sleep(1)  # Short pause between requests

        except Exception as e:
            print(f"Error importing {recipe_json.get('title', 'unknown')}: {str(e)}")

def main():
    # Configuration
    username = "YOUR_USERNAME"
    password = "YOUR_PASSWORD"
    
    # Initialize importer
    importer = TandoorRecipeImporter(username, password)
    
    # Read recipe URLs from file
    with open('recipe_urls.txt', 'r') as f:
        urls = f.readlines()

    # Process each recipe
    for url in urls:
        url = url.strip()
        try:
            # Download JSON file
            response = requests.get(url)
            recipe_data = response.json()
            
            # Import recipe
            importer.import_recipe(recipe_data)
            
        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")

if __name__ == "__main__":
    main()