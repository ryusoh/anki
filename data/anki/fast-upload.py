#!/usr/bin/env python3
"""Quick script to upload notes to R2 with parallel uploads"""

import sys
sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import hmac
from hashlib import sha256
import json

# R2 credentials
ACCOUNT_ID = 'd92e0d70ea7ec499cfc8eeaee23972a7'
ACCESS_KEY = '6f753afaa336f6d9fee5e72d2026b9d0'
SECRET_KEY = '2f01428400f6220f7fdf35550af7ee8e63e4f21b9acc9117c1f244a03484aed0'
BUCKET = 'anki-content'

def create_auth(key, content_hash):
    amz_date = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    canonical_uri = f'/{key}'
    canonical_headers = f'host:{ACCOUNT_ID}.r2.cloudflarestorage.com\nx-amz-content-sha256:{content_hash}\nx-amz-date:{amz_date}\n'
    signed_headers = 'host;x-amz-content-sha256;x-amz-date'
    canonical_request = f'PUT\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{content_hash}'
    date_stamp = amz_date[:8]
    credential_scope = f'{date_stamp}/auto/s3/aws4_request'
    string_to_sign = f'AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{sha256(canonical_request.encode()).hexdigest()}'
    
    def sign(key, msg):
        return hmac.new(key, msg.encode('utf-8'), sha256).digest()
    
    k_date = sign(('AWS4' + SECRET_KEY).encode(), date_stamp)
    k_region = sign(k_date, 'auto')
    k_service = sign(k_region, 's3')
    k_signing = sign(k_service, 'aws4_request')
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), sha256).hexdigest()
    
    return f'AWS4-HMAC-SHA256 Credential={ACCESS_KEY}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}', amz_date

def upload_file(note_file, bucket, verbose=False):
    """Upload a single note file."""
    key = f"notes/{note_file.name}"

    with open(note_file, 'rb') as f:
        content = f.read()

    content_hash = hashlib.sha256(content).hexdigest()
    auth, amz_date = create_auth(key, content_hash)

    endpoint = f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com/{bucket}/{key}'

    try:
        req = Request(endpoint, data=content, method='PUT', headers={
            'Authorization': auth,
            'x-amz-content-sha256': content_hash,
            'x-amz-date': amz_date,
            'Content-Encoding': 'gzip',
        })

        response = urlopen(req, timeout=60)
        return True, len(content)
    except Exception as e:
        # ALWAYS print errors (not just when verbose)
        print(f"\n❌ Failed {key}: {type(e).__name__}: {e}")
        return False, 0

def main():
    staging_dir = Path('/Users/lz/Library/Application Support/Anki2/addons21/data/cloudflare/notes')

    if not staging_dir.exists():
        print("Staging directory not found!")
        return

    note_files = sorted(staging_dir.glob("*.json.gz"))
    notes_count = len(note_files)
    
    if notes_count == 0:
        print("No note files found in staging directory!")
        return

    # TEST UPLOAD FIRST
    print("🧪 Testing connection with first file...")
    test_file = note_files[0]
    test_success, test_size = upload_file(test_file, BUCKET, True)
    
    if not test_success:
        print("\n❌ TEST UPLOAD FAILED!")
        print("Check your R2 credentials:")
        print(f"  Account ID: {ACCOUNT_ID}")
        print(f"  Access Key: {ACCESS_KEY[:8]}...")
        print(f"  Bucket: {BUCKET}")
        print("\nCommon issues:")
        print("  1. Credentials expired/invalid")
        print("  2. Bucket doesn't exist")
        print("  3. Network/firewall blocking R2")
        print("  4. R2 API token doesn't have write permission")
        return
    
    print(f"✅ Test upload successful! ({test_size:,} bytes)")
    print(f"\n📤 Starting bulk upload of {notes_count:,} notes with 16 parallel workers...")
    print("   (Press Ctrl+C to cancel)\n")

    uploaded = 0
    failed = 0
    total_bytes = 0
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        future_to_file = {executor.submit(upload_file, nf, BUCKET, False): nf for nf in note_files}
        
        completed = 0
        for future in as_completed(future_to_file):
            try:
                success, size = future.result()
                if success:
                    uploaded += 1
                    total_bytes += size
                else:
                    failed += 1
            except:
                failed += 1
            
            completed += 1
            
            if completed % 1000 == 0 or completed == notes_count:
                progress = (completed / notes_count) * 100
                bar_width = 40
                filled = int(bar_width * completed / notes_count)
                bar = '█' * filled + '░' * (bar_width - filled)
                print(f"\r   [{bar}] {completed:,}/{notes_count:,} ({progress:.1f}%)", end='', flush=True)
    
    print()
    print(f"✅ Done! {uploaded:,} uploaded, {failed} failed ({total_bytes/1024/1024:.1f} MB)")

if __name__ == "__main__":
    main()
