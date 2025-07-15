"""
Utility functions for Energy Bill OCR Pipeline
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np
from PIL import Image
import pdf2image
from loguru import logger
import jsonschema
from config import ENERGY_BILL_SCHEMA, DEFAULT_VALUES

class DocumentProcessor:
    """Handles document preprocessing and format conversion"""
    
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
    
    def pdf_to_images(self, pdf_path: str, output_dir: str = "temp") -> List[str]:
        """Convert PDF to image files"""
        try:
            Path(output_dir).mkdir(exist_ok=True)
            images = pdf2image.convert_from_path(pdf_path, dpi=self.dpi)
            image_paths = []
            
            for i, image in enumerate(images):
                image_path = os.path.join(output_dir, f"{Path(pdf_path).stem}_page_{i+1}.png")
                image.save(image_path, "PNG")
                image_paths.append(image_path)
                
            return image_paths
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
    
    def preprocess_image(self, image_path: str) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance image quality
            image = self.enhance_image(image)
            
            return image
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {e}")
            return None
    
    def enhance_image(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR"""
        from PIL import ImageEnhance, ImageFilter
        
        # Sharpen the image
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Apply slight blur to reduce noise
        image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        return image

class DataValidator:
    """Validates and cleans extracted data"""
    
    def __init__(self):
        self.schema = ENERGY_BILL_SCHEMA
    
    def validate_json(self, data: Dict) -> tuple[bool, List[str]]:
        """Validate JSON against schema"""
        try:
            jsonschema.validate(data, self.schema)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e)]
    
    def clean_extracted_data(self, raw_data: Dict) -> Dict:
        """Clean and normalize extracted data"""
        cleaned_data = DEFAULT_VALUES.copy()
        
        # Clean and validate each field
        for field, value in raw_data.items():
            if field in cleaned_data:
                cleaned_value = self._clean_field_value(field, value)
                cleaned_data[field] = cleaned_value
        
        # Validate locations array
        if 'locations' in raw_data:
            cleaned_data['locations'] = self._clean_locations(raw_data['locations'])
        
        # Validate usage history
        if 'usageHistory' in raw_data:
            cleaned_data['usageHistory'] = self._clean_usage_history(raw_data['usageHistory'])
        
        return cleaned_data
    
    def _clean_field_value(self, field: str, value: Any) -> Any:
        """Clean individual field values"""
        if value is None or value == "":
            return None
        
        # Clean monetary values
        if field in ['deliveryCharge', 'supplyCharge', 'taxCharge']:
            return self._clean_monetary_value(value)
        
        # Clean rate values
        if field in ['deliveryRate', 'supplyRate', 'taxRate']:
            return self._clean_rate_value(value)
        
        # Clean usage values
        if field in ['totalUsage']:
            return self._clean_usage_value(value)
        
        # Clean date values
        if field in ['statementDate']:
            return self._clean_date_value(value)
        
        # Clean string values
        if isinstance(value, str):
            return value.strip()
        
        return value
    
    def _clean_monetary_value(self, value: Union[str, float, int]) -> Optional[float]:
        """Clean monetary values"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[$,]', '', value.strip())
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _clean_rate_value(self, value: Union[str, float, int]) -> Optional[float]:
        """Clean rate values"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove percentage signs and other symbols
            cleaned = re.sub(r'[%$]', '', value.strip())
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _clean_usage_value(self, value: Union[str, float, int]) -> Optional[float]:
        """Clean usage values"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove units and commas
            cleaned = re.sub(r'[kWh,]', '', value.strip())
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _clean_date_value(self, value: Union[str, datetime]) -> Optional[str]:
        """Clean date values"""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        
        if isinstance(value, str):
            # Try to parse various date formats
            date_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%m-%d-%Y",
                "%B %d, %Y",
                "%b %d, %Y"
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(value.strip(), fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        return None
    
    def _clean_locations(self, locations: List[Dict]) -> List[Dict]:
        """Clean locations array"""
        cleaned_locations = []
        
        for location in locations:
            if isinstance(location, dict):
                cleaned_location = {
                    "accountNumber": str(location.get("accountNumber", "")).strip() or None,
                    "serviceAddress": str(location.get("serviceAddress", "")).strip() or None,
                    "meterNumber": str(location.get("meterNumber", "")).strip() or None,
                    "commodity": str(location.get("commodity", "")).strip() or None,
                    "rateClass": str(location.get("rateClass", "")).strip() or None,
                    "unit": str(location.get("unit", "")).strip() or None,
                    "usageHistory": location.get("usageHistory"),
                    "currentUsage": self._clean_usage_value(location.get("currentUsage")),
                    "notes": location.get("notes", {})
                }
                cleaned_locations.append(cleaned_location)
        
        return cleaned_locations
    
    def _clean_usage_history(self, usage_history: Dict) -> Dict:
        """Clean usage history data"""
        cleaned_history = {}
        
        for month, usage in usage_history.items():
            if isinstance(month, str) and usage is not None:
                cleaned_usage = self._clean_usage_value(usage)
                if cleaned_usage is not None:
                    cleaned_history[month.strip()] = cleaned_usage
        
        return cleaned_history

class FileManager:
    """Manages file operations and batch processing"""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_pdf_files(self) -> List[Path]:
        """Get all PDF files from input directory"""
        return list(self.input_dir.glob("*.pdf"))
    
    def create_batches(self, files: List[Path], batch_size: int) -> List[List[Path]]:
        """Create batches of files for processing"""
        batches = []
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            batches.append(batch)
        return batches
    
    def save_json(self, data: Dict, filename: str) -> str:
        """Save JSON data to output directory"""
        output_path = self.output_dir / f"{filename}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(output_path)
    
    def load_json(self, filename: str) -> Optional[Dict]:
        """Load JSON data from file"""
        try:
            file_path = self.output_dir / f"{filename}.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file {filename}: {e}")
            return None

class ProgressTracker:
    """Tracks processing progress and manages resume functionality"""
    
    def __init__(self, log_file: str = "processing_log.json"):
        self.log_file = Path(log_file)
        self.progress_data = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load existing progress data"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading progress file: {e}")
        
        return {
            "processed_files": [],
            "failed_files": [],
            "start_time": None,
            "last_update": None,
            "total_files": 0,
            "processed_count": 0
        }
    
    def save_progress(self):
        """Save current progress to file"""
        self.progress_data["last_update"] = datetime.now().isoformat()
        with open(self.log_file, 'w') as f:
            json.dump(self.progress_data, f, indent=2)
    
    def mark_processed(self, filename: str):
        """Mark file as processed"""
        if filename not in self.progress_data["processed_files"]:
            self.progress_data["processed_files"].append(filename)
            self.progress_data["processed_count"] += 1
            self.save_progress()
    
    def mark_failed(self, filename: str, error: str):
        """Mark file as failed"""
        self.progress_data["failed_files"].append({
            "filename": filename,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.save_progress()
    
    def is_processed(self, filename: str) -> bool:
        """Check if file has been processed"""
        return filename in self.progress_data["processed_files"]
    
    def get_unprocessed_files(self, all_files: List[Path]) -> List[Path]:
        """Get list of unprocessed files"""
        processed_names = set(self.progress_data["processed_files"])
        return [f for f in all_files if f.stem not in processed_names]
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            "total_files": self.progress_data["total_files"],
            "processed_count": self.progress_data["processed_count"],
            "failed_count": len(self.progress_data["failed_files"]),
            "remaining_count": self.progress_data["total_files"] - self.progress_data["processed_count"]
        }
