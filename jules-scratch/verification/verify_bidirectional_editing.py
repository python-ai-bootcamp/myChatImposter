import json
from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # Navigate to the edit page for a test configuration
        page.goto("http://localhost:3000/edit/test_config.json", timeout=60000)

        # Wait for the form and editor to be ready
        form_user_id_input = page.locator("#root_general_config_user_id")
        json_editor = page.locator('textarea')
        expect(form_user_id_input).to_be_visible(timeout=30000)
        expect(json_editor).to_be_visible(timeout=30000)

        # === Test 1: Edit form, check if JSON editor updates ===

        # Get original JSON from the editor
        original_json_str = json_editor.input_value()
        original_json_data = json.loads(original_json_str)

        # Edit the user_id in the form
        new_user_id_from_form = "user_from_form"
        form_user_id_input.fill(new_user_id_from_form)

        # Assert that the JSON editor content has updated
        expected_json_data = original_json_data.copy()
        expected_json_data[0]['user_id'] = new_user_id_from_form
        expected_json_str = json.dumps(expected_json_data, indent=2)
        expect(json_editor).to_have_value(expected_json_str)

        # === Test 2: Edit JSON editor, check if form updates ===

        # Get current JSON from the editor
        current_json_str = json_editor.input_value()
        current_json_data = json.loads(current_json_str)

        # Edit the user_id in the JSON editor
        new_user_id_from_json = "user_from_json"
        edited_json_data = current_json_data.copy()
        edited_json_data[0]['user_id'] = new_user_id_from_json
        edited_json_str = json.dumps(edited_json_data, indent=2)
        json_editor.fill(edited_json_str)

        # Assert that the form input has updated
        expect(form_user_id_input).to_have_value(new_user_id_from_json)

        # Take a screenshot to visually verify the final state
        page.screenshot(path="jules-scratch/verification/verification.png")

    except Exception as e:
        print(f"An error occurred: {e}")
        page.screenshot(path="jules-scratch/verification/error.png")
    finally:
        browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)
