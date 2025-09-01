from playwright.sync_api import sync_playwright, expect

def verify_add_configuration(page):
    """
    Test case for adding a new configuration.
    """
    # 1. Navigate to the app's homepage.
    page.goto("http://localhost:3000/")

    # 2. Set up a handler for the prompt dialog.
    #    This is necessary because Playwright needs to know how to interact with the native browser prompt.
    page.on("dialog", lambda dialog: dialog.accept("new-config.json"))

    # 3. Click the "Add" button, which will trigger the prompt.
    add_button = page.get_by_role("button", name="Add")
    add_button.click()

    # 4. Assert that the page has navigated to the new edit page.
    #    The URL should now be '/edit/new-config.json'.
    expect(page).to_have_url("http://localhost:3000/edit/new-config.json")

    # 5. Assert that the heading for the new configuration is correct.
    #    The heading should be "Add: new-config.json".
    heading = page.get_by_role("heading", name="Add: new-config.json")
    expect(heading).to_be_visible()

    # 6. Take a screenshot for visual verification.
    page.screenshot(path="jules-scratch/verification/add_config_page.png")

if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_add_configuration(page)
            print("Verification script ran successfully.")
        except Exception as e:
            print(f"Verification script failed: {e}")
        finally:
            browser.close()
