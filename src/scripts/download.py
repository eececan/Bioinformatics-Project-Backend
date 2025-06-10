import sys
import urllib.request
import urllib.parse
import time
import json 

def url_request(full_url_str, data_payload=None, method=None, headers=None, max_retries=3, timeout_seconds=30):
    """
    Performs an HTTP URL request and returns the decoded text content.
    Handles GET (default) or POST.
    If data_payload is a dict for POST, it will be urlencoded by default unless Content-Type is application/json.
    If you need to send JSON, set headers={'Content-Type': 'application/json'} 
    and pass json.dumps(data_payload).encode('utf-8') as data_payload (making it bytes).
    """
    effective_headers = { 
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0',
        'Accept-Charset': 'utf-8' 
    }
    if headers: 
        effective_headers.update(headers)

    final_method = method
    encoded_data_for_post = None

    if data_payload is not None:
        if final_method is None: 
            final_method = "POST"
        
        if isinstance(data_payload, dict):
            if effective_headers.get('Content-Type', '').lower() == 'application/json':
                try:
                    encoded_data_for_post = json.dumps(data_payload).encode("utf-8")
                except TypeError as e_json:
                    print(f"Download: Error serializing data_payload to JSON: {e_json}")
                    return None
            else: 
                encoded_data_for_post = urllib.parse.urlencode(data_payload).encode("utf-8")
                if 'Content-Type' not in effective_headers: 
                     effective_headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=utf-8'
        elif isinstance(data_payload, bytes): 
            encoded_data_for_post = data_payload
        elif isinstance(data_payload, str): 
            encoded_data_for_post = data_payload.encode("utf-8")
            if final_method == "POST" and 'Content-Type' not in effective_headers:
                 effective_headers['Content-Type'] = 'text/plain; charset=utf-8'
        else:
            print(f"Download: Unsupported POST data_payload type: {type(data_payload)}")
            return None
    
    if final_method is None: 
        final_method = "GET"

    retry_count = 0
    while retry_count < max_retries:
        try:
            req = urllib.request.Request(full_url_str, data=encoded_data_for_post, headers=effective_headers, method=final_method)
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                response_bytes = response.read()
                charset = response.headers.get_content_charset() or 'utf-8'
                try:
                    return response_bytes.decode(charset)
                except UnicodeDecodeError:
                    print(f"Download: UnicodeDecodeError with charset {charset}, trying 'latin-1' for URL: {full_url_str}")
                    return response_bytes.decode('latin-1', errors='replace') 
        except urllib.error.HTTPError as e_http:
            print(f"Download: HTTP Error {e_http.code}: {e_http.reason} for URL: {full_url_str}")
            if e_http.code == 400: 
                print("Download: Received 400 Bad Request. URL or parameters likely malformed or ID not found by API for this endpoint.")
                return None 
            if e_http.code == 403: print("Download: Received 403 Forbidden. Check API key or permissions."); return None
            if e_http.code == 404: print("Download: Received 404 Not Found."); return None
            if e_http.code == 429: print("Download: Received 429 Too Many Requests. API rate limit likely hit.")
            if e_http.code == 429 and retry_count < max_retries -1 : 
                wait_time = 5 * (retry_count + 1) 
                print(f"Download: Waiting {wait_time}s before retry for 429 error...")
                time.sleep(wait_time) 
            elif e_http.code >= 500: 
                pass 
            else: 
                return None
        except urllib.error.URLError as e_url: 
            print(f"Download: URL Error: {e_url.reason} for URL: {full_url_str}")
        except Exception as e_general: 
            print(f"Download: General error for URL {full_url_str}: {type(e_general).__name__} - {e_general}")
        
        retry_count += 1
        if retry_count < max_retries:
            print(f"Download: Retrying ({retry_count}/{max_retries})...")
            sleep_duration = min(1 * (2**(retry_count-1)), 30) 
            time.sleep(sleep_duration) 
        else:
            print(f"Download: Max retries reached for URL: {full_url_str}")
            
    return None 