"""
Configuration file for Energy Bill OCR Pipeline
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class PipelineConfig:
    """Configuration settings for the OCR pipeline"""
    
    # Directory paths
    INPUT_DIR: str = "data/raw_data"
    OUTPUT_DIR: str = "output_json"
    LOG_DIR: str = "logs"
    TEMP_DIR: str = "temp"
    
    # Processing settings
    BATCH_SIZE: int = 10
    MAX_WORKERS: int = 4
    PDF_DPI: int = 300
    IMAGE_FORMAT: str = "PNG"
    
    # API settings
    VISION_AGENT_TIMEOUT: int = 60
    LANDING_AI_TIMEOUT: int = 60
    ANTHROPIC_TIMEOUT: int = 60
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5
    
    # File extensions
    SUPPORTED_FORMATS: List[str] = None
    
    def __post_init__(self):
        if self.SUPPORTED_FORMATS is None:
            self.SUPPORTED_FORMATS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']
    
    def create_directories(self):
        """Create necessary directories if they don't exist"""
        for dir_path in [self.INPUT_DIR, self.OUTPUT_DIR, self.LOG_DIR, self.TEMP_DIR]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

# JSON Schema for energy bill data validation
ENERGY_BILL_SCHEMA = {
    "type": "object",
    "properties": {
        "documentId": {"type": "string"},
        "issuer": {"type": "string"},
        "documentType": {"type": "string"},
        "commodity": {"type": "string"},
        "unit": {"type": "string"},
        "statementDate": {"type": "string", "format": "date"},
        "customerName": {"type": "string"},
        "reportType": {"type": "string"},
        "deliveryCharge": {"type": ["number", "null"]},
        "supplyCharge": {"type": ["number", "null"]},
        "taxCharge": {"type": ["number", "null"]},
        "totalUsage": {"type": ["number", "null"]},
        "deliveryRate": {"type": ["number", "null"]},
        "supplyRate": {"type": ["number", "null"]},
        "taxRate": {"type": ["number", "null"]},
        "usageHistory": {
            "type": "object",
            "additionalProperties": {"type": ["number", "null"]}
        },
        "locations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "accountNumber": {"type": "string"},
                    "serviceAddress": {"type": "string"},
                    "meterNumber": {"type": "string"},
                    "commodity": {"type": "string"},
                    "rateClass": {"type": ["string", "null"]},
                    "unit": {"type": "string"},
                    "usageHistory": {"type": ["object", "null"]},
                    "currentUsage": {"type": ["number", "null"]},
                    "notes": {"type": "object"}
                }
            }
        }
    },
    "required": ["documentId", "issuer", "documentType", "commodity"]
}

# API Configuration
API_ENDPOINTS = {
    "vision_agent": "https://api.landing.ai/v1/vision-agent",
    "landing_ai": "https://api.landing.ai/v1/document-extraction",
    "anthropic": "https://api.anthropic.com/v1/messages"
}

# Default values for extracted data
DEFAULT_VALUES = {
    "documentId": None,
    "issuer": None,
    "documentType": "sampleBill",
    "commodity": None,
    "unit": None,
    "statementDate": None,
    "customerName": None,
    "reportType": None,
    "deliveryCharge": None,
    "supplyCharge": None,
    "taxCharge": None,
    "totalUsage": None,
    "deliveryRate": None,
    "supplyRate": None,
    "taxRate": None,
    "usageHistory": {},
    "locations": []
}

# Logging configuration
LOG_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    "rotation": "1 day",
    "retention": "30 days"
}

# Document processing strategies
PROCESSING_STRATEGIES = {
    "complex_charts": "vision_agent",
    "structured_tables": "landing_ai",
    "mixed_content": "both",
    "fallback": "anthropic"
}

# Field mapping for different extraction methods
FIELD_MAPPINGS = {
    "vision_agent": {
        "customer_name": ["customer_name", "account_holder", "bill_to"],
        "account_number": ["account_number", "account_no", "acct_no"],
        "statement_date": ["statement_date", "bill_date", "date"],
        "total_amount": ["total_amount", "amount_due", "balance"]
    },
    "landing_ai": {
        "tables": ["usage_table", "charges_table", "history_table"],
        "headers": ["document_header", "customer_info", "account_info"],
        "footers": ["payment_info", "contact_info"]
    }
}
