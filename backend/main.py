import functions_framework
from flask import jsonify
from google.cloud import vision, language_v1, translate_v2 as translate

# Initialize Google Cloud clients
vision_client = vision.ImageAnnotatorClient()
language_client = language_v1.LanguageServiceClient()
translate_client = translate.Client()

@functions_framework.http
def analyze_file(request):
    """
    An HTTP-triggered Cloud Function that analyzes an uploaded file.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`.
    """
    # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    if request.method != 'POST':
        return ('Only POST requests are accepted', 405, headers)

    if 'file' not in request.files:
        return ('No file uploaded', 400, headers)

    file = request.files['file']
    file_content = file.read()
    mime_type = file.content_type

    try:
        if mime_type.startswith('image/'):
            results = analyze_image(file_content)
        elif mime_type.startswith('text/'):
            results = analyze_text(file_content)
        elif mime_type == 'application/pdf':
            results = analyze_pdf(file_content)
        else:
            results = {'error': f'Unsupported file type: {mime_type}'}

        return (jsonify(results), 200, headers)

    except Exception as e:
        return (jsonify({'error': str(e)}), 500, headers)


def analyze_image(content):
    """Analyzes image content using the Vision API."""
    image = vision.Image(content=content)
    
    # Perform label detection
    response = vision_client.label_detection(image=image)
    labels = [label.description for label in response.label_annotations]
    
    # Perform image properties detection
    response = vision_client.image_properties(image=image)
    colors = response.image_properties_annotation.dominant_colors.colors
    dominant_colors = [f'RGB:({int(c.color.red)}, {int(c.color.green)}, {int(c.color.blue)})' for c in colors]

    return {
        'type': 'Image Analysis',
        'labels': labels,
        'dominant_colors': dominant_colors
    }


def analyze_text(content):
    """Analyzes text content using Language and Translate APIs."""
    # The content is in bytes, decode it to a string
    text_content = content.decode('utf-8')
    
    # Use Translate API to detect language
    detection = translate_client.detect_language(text_content)
    language = detection['language']
    confidence = detection['confidence']

    # Use Language API for entities
    document = language_v1.Document(content=text_content, type_=language_v1.Document.Type.PLAIN_TEXT)
    response = language_client.analyze_entities(document=document)
    entities = [entity.name for entity in response.entities[:5]] # Get top 5 entities

    return {
        'type': 'Text Analysis',
        'language_code': language,
        'language_confidence': confidence,
        'word_count': len(text_content.split()),
        'entities': entities
    }


def analyze_pdf(content):
    """Performs OCR on a PDF file using the Vision API."""
    # The Vision API can accept PDF content directly
    input_config = vision.InputConfig(content=content, mime_type='application/pdf')
    
    # Specify the feature for text detection (OCR)
    features = [vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)]
    
    # Make the request
    request = vision.AnnotateFileRequest(input_config=input_config, features=features)
    response = vision_client.annotate_file(request=request)

    # Extract text from the first page (for simplicity)
    # A full implementation might handle all pages
    first_page_text = response.responses[0].full_text_annotation.text

    return {
        'type': 'PDF Analysis (OCR)',
        'extracted_text_sample': first_page_text[:500] + '...' # Return a sample
    }
