from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # --- Verify EditPage Height ---
        print("Navigating to EditPage...")
        page.goto("http://localhost:3000/edit/test_config.json", timeout=60000)

        # Wait for a known element on the page to be visible
        expect(page.get_by_role("heading", name="Live JSON Editor")).to_be_visible(timeout=30000)

        print("Taking EditPage screenshot...")
        page.screenshot(path="jules-scratch/verification/editpage_height.png")

        print("Verification script completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        page.screenshot(path="jules-scratch/verification/error.png")
    finally:
        browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)
