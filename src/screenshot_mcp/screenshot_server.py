from fastmcp import FastMCP
from typing import Any
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from screenshot_mcp.config import CONFIG
import time

from screenshot_mcp.storage import (
    ensure_bucket,
    generate_unique_object_name,
    get_minio_client,
    upload_png_bytes,
)

mcp = FastMCP(
    "ScreenshotMCP",
    instructions=(
        "Creates website screenshots, validates HTTP status, retries failed calls, "
        "uploads the result to MinIO, and returns URL plus MinIO object path."
    )
)

def _take_screenshot(url: str) -> dict[str, Any]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        try:
            response = page.goto(url, wait_until="networkidle", timeout=CONFIG.screenshot_timeout_ms)
            page.wait_for_selector("body", timeout=CONFIG.screenshot_timeout_ms)

            status_code = response.status if response else None
            is_success = status_code is not None and 200 <= status_code < 400

            if not is_success:
                return {
                    "is_success": False,
                    "status_code": status_code,
                    "error": f"Unsuccessful HTTP status: {status_code}",
                    "screenshot_bytes": None,
                }
            
            screenshot_bytes = page.screenshot(full_page=True)

            return {
                "is_success": True,
                "status_code": status_code,
                "error": None,
                "screenshot_bytes": screenshot_bytes,
            }

        except PlaywrightTimeoutError as e:
            return {
                "is_success": False,
                "status_code": None,
                "error": f"Timeout during navigation or rendering: {str(e)}",
                "screenshot_bytes": None,
            }
        except Exception as e:
            return {
                "is_success": False,
                "status_code": None,
                "error": f"Unexpected screenshot error: {str(e)}",
                "screenshot_bytes": None,
            }
        finally:
            browser.close()

@mcp.tool()
def capture_website_screenshot_to_minio(url: str) -> dict[str, Any]:
    """
    Open a website, create screenshot, upload PNG to MinIO, and return metadata.

    Args:
        url: target website URL

    Returns:
        {
          "url": "<input-url>",
          "path": "<bucket>/<object-key>",
          "object_id": "<uuid>",
          "status_code": 200,
          "attempts": 1
        }
    """
    client = get_minio_client()
    ensure_bucket(client, CONFIG.minio_bucket)

    last_error: str | None = None
    last_status: int | None = None

    for attempt in range(1, CONFIG.screenshot_max_attempts + 1):
        result = _take_screenshot(url=url)
        last_status = result.get("status_code")

        if result["is_success"] and result["screenshot_bytes"]:

            object_id, object_name = generate_unique_object_name(
                client=client,
                bucket_name=CONFIG.minio_bucket,
                prefix=CONFIG.minio_prefix,
            )

            upload_png_bytes(
                client=client,
                bucket_name=CONFIG.minio_bucket,
                object_name=object_name,
                data=result["screenshot_bytes"],
            )

            return {
                "url": url,
                "path": f"{CONFIG.minio_bucket}/{object_name}",
                "object_id": object_id,
                "status_code": last_status,
                "attempts": attempt,
            }

        last_error = result["error"]

        if attempt < CONFIG.screenshot_max_attempts:
            time.sleep(min(2 * attempt, 5))

    return {
        "url": url,
        "path": None,
        "object_id": None,
        "status_code": last_status,
        "attempts": CONFIG.screenshot_max_attempts,
        "error": last_error or "Failed after all retry attempts",
    }

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=CONFIG.mcp_host,
        port=CONFIG.mcp_port
        # path=CONFIG.mcp_path,
    )