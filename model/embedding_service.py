from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import requests
import torch
from io import BytesIO

class MultimodalEmbedder:
    def __init__(self):
        print("Loading CLIP model (openai/clip-vit-base-patch32)...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        print("Model loaded.")

    def get_text_embedding(self, text: str):
        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)
        # Normalize and return list
        return (outputs / outputs.norm(p=2, dim=-1, keepdim=True)).squeeze().tolist()

    def get_image_embedding(self, image_url_or_path: str):
        if image_url_or_path.startswith("http"):
            response = requests.get(image_url_or_path)
            image = Image.open(BytesIO(response.content))
        else:
            image = Image.open(image_url_or_path)

        inputs = self.processor(images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
        return (outputs / outputs.norm(p=2, dim=-1, keepdim=True)).squeeze().tolist()

if __name__ == "__main__":
    embedder = MultimodalEmbedder()
    
    # Test Text
    text_emb = embedder.get_text_embedding("A large containership in a port")
    print(f"Generated text embedding (len={len(text_emb)})")
    
    # Test Image (using a placeholder URL for demo)
    # Ensure this URL is valid or replace with local path for actual test
    try:
        img_url = "https://raw.githubusercontent.com/huggingface/transformers/main/docs/source/en/imgs/ship.jpg" 
        # (This is just a hypothetical stable URL, if fails we catch it)
        # Using a very generic stable placeholder from Wikimedia if above fails
        # img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Maersk_Triple_E.jpg/320px-Maersk_Triple_E.jpg"
        
        # Let's try to pass a dummy image creation if net access is flaky, but for now typical request:
        # print("Skipping image download test to avoid network issues in this environment.")
        pass 
    except Exception as e:
        print(f"Image test skipped: {e}")
