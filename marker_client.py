#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Set

import requests

# Supported file extensions
SUPPORTED_EXTENTIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}

class DocumentProcessor:
    def __init__(self, url: str = "http://127.0.0.1:8000"):
        self.url = url.rstrip("/")

    def process_document(self, file_path: Path, output_dir: Path, output_format: str = "markdown") -> bool:
        """Process a single document file."""
        if not file_path.exists():
            print(f"Error: File not found - {file_path}")
            return False

        if file_path.suffix.lower() not in SUPPORTED_EXTENTIONS:
            print(f"Error: Unsupported file type - {file_path.suffix}")
            return False

        # Create output directory with document name prefix
        doc_output_dir = output_dir / f"{file_path.stem}__md"
        doc_output_dir.mkdir(exist_ok=True, parents=True)
        (doc_output_dir / "images").mkdir(exist_ok=True)

        # Get MIME type based on file extension
        mime_type = self._get_mime_type(file_path.suffix.lower())

        # Prepare the request
        files = {
            "file": (file_path.name, file_path.open("rb"), mime_type)
        }
        data = {
            "output_format": output_format
        }

        try:
            response = requests.post(
                f"{self.url}/marker/upload",
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("success"):
                print(f"❌ Error processing {file_path}: {result.get('error')}")
                return False

            # Save the text output with explicit UTF-8 encoding
            output_path = doc_output_dir / f"output.{output_format}"
            with output_path.open('w', encoding='utf-8') as f:
                f.write(result["output"])
            print(f"✓ Text saved to: {output_path}")

            # Save images if any
            if result.get("images"):
                for img_name, img_data in result["images"].items():
                    img_path = doc_output_dir / "images" / f"{img_name}.png"
                    img_path.write_bytes(base64.b64decode(img_data))
                    print(f"  Image saved to: {img_path}")

            # Save raw response with explicit UTF-8 encoding
            response_path = doc_output_dir / "response.json"
            with response_path.open('w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  Response saved to: {response_path}")

            return True

        except requests.RequestException as e:
            print(f"❌ Error processing {file_path}: {str(e)}")
            return False

    def find_documents(self, directory: Path, recursive: bool = False) -> List[Path]:
        """Find all supported document files in a directory."""
        all_files = []
        for ext in SUPPORTED_EXTENTIONS:
            if recursive:
                all_files.extend(directory.rglob(f"*{ext}"))
            else:
                all_files.extend(directory.glob(f"*{ext}"))
        return sorted(all_files)

    def _get_mime_type(self, extension: str) -> str:
        """Get the MIME type for a given file extension."""
        # Only keep specific MIME types for document formats that might need special handling
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        return mime_types.get(extension, 'application/octet-stream')


def main():
    parser = argparse.ArgumentParser(
        description="Process documents using the Marker API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Supported file types:
  {', '.join(sorted(SUPPORTED_EXTENTIONS))}

Examples:
  %(prog)s document.pdf                     # Process single document to current directory
  %(prog)s document.docx -o /path/to/output # Process single document to specific directory
  %(prog)s . -r                            # Process all documents in current directory and subdirectories
  %(prog)s /path/to/docs                   # Process all documents in specific directory
"""
    )
    
    # First positional argument can be either a file or directory
    parser.add_argument("input", type=Path,
                       help="File or directory to process")
    
    parser.add_argument("-o", "--output-dir", type=Path,
                       default=Path.cwd(),
                       help="Output directory (default: current directory)")
    
    parser.add_argument("-r", "--recursive", action="store_true",
                       help="Recursively process subdirectories")
    
    parser.add_argument("-u", "--url", 
                       default="http://127.0.0.1:8000",
                       help="Server URL")
    
    parser.add_argument("-f", "--format", 
                       dest="output_format",
                       default="markdown",
                       choices=["markdown", "json", "html"],
                       help="Output format")

    args = parser.parse_args()

    # Create processor instance
    processor = DocumentProcessor(args.url)

    # Ensure output directory exists
    args.output_dir.mkdir(exist_ok=True, parents=True)
    
    if args.input.is_file():
        # Process single document
        processor.process_document(args.input, args.output_dir, args.output_format)
    
    elif args.input.is_dir():
        # Process directory
        documents = processor.find_documents(args.input, args.recursive)
        if not documents:
            print(f"No supported document files found in {args.input}")
            return

        print(f"Found {len(documents)} document files")
        for doc in documents:
            print(f"\nProcessing: {doc}")
            processor.process_document(doc, args.output_dir, args.output_format)
    
    else:
        print(f"Error: Input path does not exist - {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()