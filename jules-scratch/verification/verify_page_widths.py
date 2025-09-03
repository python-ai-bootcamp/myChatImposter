from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # --- Verify HomePage ---
        print("Navigating to HomePage...")
        page.goto("http://localhost:3000/", timeout=60000)

        # Wait for a known element on the page to be visible
        expect(page.get_by_role("heading", name="Configuration Files")).to_be_visible(timeout=30000)

        print("Taking HomePage screenshot...")
        page.screenshot(path="jules-scratch/verification/homepage.png")

        # --- Verify LinkPage ---
        print("Navigating to LinkPage...")
        page.goto("http://localhost:3000/link/test-user", timeout=60000)

        # Wait for a known element on the page to be visible
        expect(page.get_by_role("heading", name="Link Status for User: test-user")).to_be_visible(timeout=30000)

        print("Taking LinkPage screenshot...")
        page.screenshot(path="jules-scratch/verification/linkpage.png")

        print("Verification script completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        page.screenshot(path="jules-scratch/verification/error.png")
    finally:
        browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)
