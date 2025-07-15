"""
API client implementations for VisionAgent, LandingAI, Anthropic, and Google Vision
"""

import base64
import json
import time
from typing import Dict, List, Optional, Any
import requests
from PIL import Image
import io
from loguru import logger
from config import API_ENDPOINTS, DEFAULT_VALUES
import anthropic
import google.generativeai as genai
from vision_agent.agent import VisionAgent
from agentic_doc.parse import parse

class APIClientBase:
    """Base class for API clients"""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = 5

    def _retry_request(self, func, *args, **kwargs):
        """Retry failed requests with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

class VisionAgentClient(APIClientBase):
    """Client for VisionAgent API"""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        super().__init__(api_key, timeout, max_retries)
        self.client = VisionAgent(api_key=api_key)

    def analyze_document(self, image_path: str, prompt: str) -> Dict:
        """Analyze document using VisionAgent"""
        try:
            logger.info(f"Analyzing document with VisionAgent: {image_path}")
            image = Image.open(image_path)

            response = self._retry_request(
                self.client.analyze_image,
                image=image,
                prompt=prompt
            )

            if response and 'analysis' in response:
                return {
                    'success': True,
                    'data': response['analysis'],
                    'metadata': response.get('metadata', {})
                }
            else:
                return {
                    'success': False,
                    'error': 'No analysis data in response',
                    'data': None
                }

        except Exception as e:
            logger.error(f"VisionAgent API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    def extract_chart_data(self, image_path: str) -> Dict:
        chart_prompt = """
        Analyze this image and extract all numerical data from charts, graphs, and visual elements.
        Focus on:
        1. Usage history charts (monthly consumption data)
        2. Bar charts, line graphs, pie charts
        3. Tables with numerical data
        4. Rate schedules and pricing information

        Return structured data with:
        - Chart type and title
        - Numerical values and their labels
        - Time periods and units
        - Any trends or patterns
        """

        return self.analyze_document(image_path, chart_prompt)

    def extract_complex_layouts(self, image_path: str) -> Dict:
        layout_prompt = """
        Analyze this complex document layout and extract all structured information.
        Handle:
        1. Multi-column layouts
        2. Nested tables and sections
        3. Header and footer information
        4. Customer and account details
        5. Billing and usage information
        6. Service address and meter data

        Return comprehensive structured data preserving all relationships and hierarchy.
        """

        return self.analyze_document(image_path, layout_prompt)

class LandingAIClient(APIClientBase):
    """Client for LandingAI Agentic Document Extraction"""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        super().__init__(api_key, timeout, max_retries)
        self.client = parse(api_key=api_key)

    def extract_document_data(self, image_path: str) -> Dict:
        """Extract structured data using LandingAI"""
        try:
            logger.info(f"Extracting document data with LandingAI: {image_path}")

            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()

            response = self._retry_request(
                self.client.extract_document,
                image_data=image_data,
                extraction_type="energy_bill"
            )

            if response and 'extracted_data' in response:
                return {
                    'success': True,
                    'data': response['extracted_data'],
                    'locations': response.get('element_locations', {}),
                    'confidence': response.get('confidence_scores', {})
                }
            else:
                return {
                    'success': False,
                    'error': 'No extracted data in response',
                    'data': None
                }

        except Exception as e:
            logger.error(f"LandingAI API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    def extract_tables(self, image_path: str) -> Dict:
        """Extract table data with precise location information"""
        try:
            logger.info(f"Extracting tables with LandingAI: {image_path}")

            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()

            config = {
                "extraction_type": "table",
                "return_locations": True,
                "confidence_threshold": 0.7
            }

            response = self._retry_request(
                self.client.extract_tables,
                image_data=image_data,
                config=config
            )

            if response and 'tables' in response:
                return {
                    'success': True,
                    'tables': response['tables'],
                    'locations': response.get('table_locations', {}),
                    'confidence': response.get('confidence_scores', {})
                }
            else:
                return {
                    'success': False,
                    'error': 'No table data in response',
                    'data': None
                }

        except Exception as e:
            logger.error(f"LandingAI table extraction error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

class AnthropicClient(APIClientBase):
    """Client for Anthropic Claude API as fallback"""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        super().__init__(api_key, timeout, max_retries)
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze_document_text(self, image_path: str, extracted_text: str) -> Dict:
        """Analyze extracted text using Claude"""
        try:
            logger.info(f"Analyzing document text with Anthropic: {image_path}")

            prompt = f"""
Analyze this extracted text from an energy bill and structure it into JSON format.

Extracted Text:
{extracted_text}

Please extract and structure the following information:
1. Document metadata (ID, issuer, dates, type)
2. Customer information (name, account numbers)
3. Financial data (charges, rates, totals)
4. Usage data (current period, historical monthly data)
5. Location/meter specific data

Return valid JSON matching the energy bill schema.
Use null for missing or unclear values.
"""

            response = self._retry_request(
                self.client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            try:
                json_data = json.loads(response_text)
                return {
                    'success': True,
                    'data': json_data,
                    'raw_response': response_text
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON in response',
                    'raw_response': response_text
                }

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    def enhance_extraction(self, partial_data: Dict, image_path: str) -> Dict:
        """Enhance partial extraction results"""
        try:
            image_base64 = self._encode_image(image_path)

            prompt = f"""
I have partial data extracted from an energy bill. Please analyze the image and enhance/complete the extraction.

Current partial data:
{json.dumps(partial_data, indent=2)}

Please:
1. Fill in missing fields where possible
2. Correct any obvious errors
3. Extract additional details from the image
4. Ensure data consistency and accuracy

Return the enhanced JSON data.
"""

            response = self._retry_request(
                self.client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }}
                    ]
                }]
            )

            response_text = response.content[0].text
            try:
                enhanced_data = json.loads(response_text)
                return {
                    'success': True,
                    'data': enhanced_data,
                    'raw_response': response_text
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Invalid JSON in enhanced response',
                    'raw_response': response_text
                }

        except Exception as e:
            logger.error(f"Anthropic enhancement error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

class GoogleVisionClient(APIClientBase):
    """Client for Google Vision API as additional fallback"""

    def __init__(self, api_key: str, timeout: int = 60, max_retries: int = 3):
        super().__init__(api_key, timeout, max_retries)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro-vision')

    def extract_text_ocr(self, image_path: str) -> Dict:
        """Extract text using Google Vision OCR"""
        try:
            logger.info(f"Extracting text with Google Vision: {image_path}")
            image = Image.open(image_path)

            prompt = """
Extract all text from this energy bill image.
Preserve the layout and structure as much as possible.
Include all numbers, dates, addresses, and other details.
Format the output to maintain readability.
"""

            response = self._retry_request(
                self.model.generate_content,
                [prompt, image]
            )

            if response and response.text:
                return {
                    'success': True,
                    'text': response.text,
                    'metadata': {
                        'extraction_method': 'google_vision',
                        'timestamp': time.time()
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'No text extracted',
                    'text': None
                }

        except Exception as e:
            logger.error(f"Google Vision API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': None
            }

class HybridExtractionClient:
    """Combines multiple API clients for optimal extraction"""

    def __init__(self, vision_agent_key: str, landing_ai_key: str,
                 anthropic_key: str, google_key: str):
        self.vision_agent = VisionAgent(vision_agent_key)
        self.landing_ai = parse(landing_ai_key)
        self.anthropic = AnthropicClient(anthropic_key)
        self.google_vision = GoogleVisionClient(google_key)

    def extract_comprehensive_data(self, image_path: str) -> Dict:
        results = {
            'vision_agent': None,
            'landing_ai': None,
            'anthropic': None,
            'google_vision': None,
            'combined_data': None,
            'confidence_score': 0.0
        }

        # Step 1: VisionAgent for complex layouts
        try:
            va_result = self.vision_agent.extract_complex_layouts(image_path)
            results['vision_agent'] = va_result
            logger.info("VisionAgent extraction completed")
        except Exception as e:
            logger.error(f"VisionAgent extraction failed: {e}")

        # Step 2: LandingAI for structured extraction
        try:
            la_result = self.landing_ai.extract_document_data(image_path)
            results['landing_ai'] = la_result
            logger.info("LandingAI extraction completed")
        except Exception as e:
            logger.error(f"LandingAI extraction failed: {e}")

        # Step 3: Google Vision OCR fallback
        try:
            gv_result = self.google_vision.extract_text_ocr(image_path)
            results['google_vision'] = gv_result
            logger.info("Google Vision OCR completed")
        except Exception as e:
            logger.error(f"Google Vision extraction failed: {e}")

        # Step 4: Combine and enhance with Anthropic
        try:
            combined_data = self._combine_extraction_results(results)

            if combined_data:
                enhanced_result = self.anthropic.enhance_extraction(
                    combined_data, image_path
                )
                if enhanced_result['success']:
                    results['combined_data'] = enhanced_result['data']
                    results['confidence_score'] = self._calculate_confidence(results)
                else:
                    results['combined_data'] = combined_data
                    results['confidence_score'] = 0.5

            logger.info("Data combination and enhancement completed")
        except Exception as e:
            logger.error(f"Data combination failed: {e}")
            results['combined_data'] = self._fallback_extraction(results)
            results['confidence_score'] = 0.3

        return results

    def _combine_extraction_results(self, results: Dict) -> Dict:
        combined = DEFAULT_VALUES.copy()

        # Priority: LandingAI > VisionAgent > Google Vision
        sources = ['landing_ai', 'vision_agent', 'google_vision']

        for source in sources:
            res = results.get(source)
            if res and res.get('success'):
                data = res.get('data', {})
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key in combined and (combined[key] is None or combined[key] == ""):
                            combined[key] = value

        return combined

    def _calculate_confidence(self, results: Dict) -> float:
        confidence = 0.0
        successful_extractions = 0

        for source, result in results.items():
            if source != 'combined_data' and result and result.get('success'):
                successful_extractions += 1
                confidence += result.get('confidence', 0.7)  # Default to 0.7 if not provided

        if successful_extractions > 0:
            return min(confidence / successful_extractions, 1.0)
        return 0.0

    def _fallback_extraction(self, results: Dict) -> Dict:
        fallback_data = DEFAULT_VALUES.copy()

        for source, result in results.items():
            if result and result.get('success'):
                data = result.get('data', {})
                if isinstance(data, dict):
                    for field in ['customerName', 'statementDate', 'totalUsage']:
                        if field in data and data[field]:
                            fallback_data[field] = data[field]

        return fallback_data
