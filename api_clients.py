"""
API client implementations for VisionAgent, LandingAI, and Anthropic
"""

import base64
import json
import time
from typing import Dict, List, Optional, Any, Union
import requests
from PIL import Image
import io
from loguru import logger
from config import API_ENDPOINTS
import anthropic
import google.generativeai as genai
from vision_agent.vision_agent import VisionAgent
from landing_ai.client import LandingAI

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
            
            # Load and prepare image
            image = Image.open(image_path)
            
            # Call VisionAgent
            response = self._retry_request(
                self.client.analyze_image,
                image=image,
                prompt=prompt
            )
            
            # Parse response
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
        """Extract data from charts and graphs"""
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
        """Extract data from complex document layouts"""
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
        self.client = LandingAI(api_key=api_key)
    
    def extract_document_data(self, image_path: str) -> Dict:
        """Extract structured data using LandingAI"""
        try:
            logger.info(f"Extracting document data with LandingAI: {image_path}")
            
            # Load image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Call LandingAI API
            response = self._retry_request(
                self.client.extract_document,
                image_data=image_data,
                extraction_type="energy_bill"
            )
            
            # Parse response
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
            
            # Configure for table extraction
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
            
            return {
