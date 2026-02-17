# General Feature High Level Description

* Each user will have a periodically refreshed **llm_quota**. 
* After this **llm_quota** is utilized all of the user's owned bots will stop working until next period starts (become stopped, but not un authenticated).
    * once quota is reset, the bots will become automatically started again
---

# Technical Details

### *) New Objects

* **llm_quota:**
    * A new user property (llm_quota) will be added.
    * This property (llm_quota) is an object property of a user and will have the following properties:
        ```json
        {
            "reset_days": "integer representing the days between quota reset",
            "dollars_per_period": "float representing the max number of dollars the user can spend per reset_days period",
            "dollars_used": "float representing currently used dollars since last reset_days period",
            "last_reset": "epoch timestamp listing last time user tokens were refreshed",
            "enabled": "boolean representing the state of the user's quota"
        }
        ```
* **token_menu:**
    * A new global **token_menu** object will be added.
    * This global object (**token_menu**) will be saved in configurations collection.
    * This global object (**token_menu**) will be read into memory by backend once on startup.
    * This object (**token_menu**) will be used later on by **token_consumption_event** handlers.
    * **token_menu** object represent the cost of 1,000,000 tokens by each model and token type (input/output).
    * This is how it will currently look (actual values for first creation if it doesn't exist yet):
        ```json
        {
            "high": {
                "input_tokens": 1.25,
                "cached_input_tokens": 0.125,
                "output_tokens": 10
            },
            "low": {
                "input_tokens": 0.25,
                "cached_input_tokens": 0.025,
                "output_tokens": 2
            }
        }
        ```

### *) Feature Behavior

* **Quota Utilization Procedure:**
    * Currently there is already a mechanism for handling **token_consumption_event** in the `llm_factory` (`TokenConsumptionService.record_event()`) which is documenting every user/bot/feature/model token consumption.
    * The already existing handler of **token_consumption_event** will be extended to calculate a cost of each **token_consumption_event** and update user's `llm_quota.dollars_used` accordingly.

* **llm_quota.dollars_used Update Procedure:**
    * In order to calculate the updated `llm_quota.dollars_used` we need three values:
        1.  **token_menu** (already loaded to memory at startup, no need to read from database)
        2.  **token_consumption_event.reporting_llm_config**
        3.  **token_consumption_event.input_tokens**
        4.  **token_consumption_event.output_tokens**
        5.  **llm_quota** (can be fetched from database by the supplied user_id)

    > **COST CALCULATION EXAMPLE WITH NUMBERS:**
    > 
    > If the following **token_consumption_event** occured:
    > ```json
    > {
    >     "_id" : ObjectId("698f3211eeb9de7e6f01f1c5"),
    >     "user_id" : "action_items_tal",
    >     "input_tokens" : 1009,
    >     "output_tokens" : 292,
    >     "reporting_llm_config" : "low"
    > }
    > ```
    > And the relevant user **llm_quota** was:
    > ```json
    > {
    >     "reset_days": 7,
    >     "dollars_per_period": 1,
    >     "dollars_used": 0.5,
    >     "last_reset": 1769904000000,
    >     "enabled":true
    > }
    > ```
    > The cost of this specific event is: `1009*0.25/1000000 + 292*2/1000000 = 0.00083625`
    > So `dollars_used` is updated to `0.50083625`.

    * When the `llm_quota.dollars_used >= llm_quota.dollars_per_period` then:
        * User's `llm_quota.enabled` will be set to **false**.
        * All of the user's owned bots that are in linked state will be shut down gracefully.
            * Please make sure you reuse the same partial code of reload logic (stop/start) only without the start part.

* **Quota Reset Procedure:**
    * Each user **llm_quota** has a `reset_days` property (default value of 7).
    * Each day at midnight (UTC), all user's `llm_quota.dollars_used` which passed the `llm_quota.reset_days` since their `llm_quota.last_reset` will be reset to 0.
    * If the user was marked as `llm_quota.enabled=false` he will:
        1.  `llm_quota.enabled` be set to **true** again.
        2.  The authenticated bots (which are bot.configurations.user_details.activated=true) of this user will be started again.

### *) Existing Behavior Changes

* **Automatic Bot Linking:**
    1.  Up until now, all authenticated bots were not linked on startup.
    2.  From now on, all bots who meet the following conditions will be automatically started 1 minute after backend startup:
        * 2.1 They are already authenticated.
        * 2.2 Their bot_configuration.configurations.user_details.activated=true.
        * 2.3 Their owner is `user.llm_quota.enabled=true`.
* **backend**
    * the user model (non restricted full one) will now also have the llm_quota as part of it
        * llm_quota will be hidden from regular users using the restricted user model (one used for patch method on profile page)
    * each bot configuration (configurations.user_details) will have a a new boolean property named "activated" which are the bots that will be automatically started at aplication startup or quota reset as long as they meet criteria mentioned in "automatic bot linking" or "quota reset procedure" sections above
        * this property is revealed in both full and restricted bot configuration model
        * its default value is true
* **UI:**
    * **/admin/users page:**
        1.  the grid will have a new column named **Quota Utilization**.
        2.  new column will show percentage used: `ROUNDED_TO_TWO_DECIMAL_POINTS(100 * llm_quota.dollars_used / llm_quota.dollars_per_period)`.
    * **/admin/users/edit/ and /admin/users/create pages:**
        1.  Contain the new **llm_quota** object (added to full user model).
        2.  Not presented to the `role=user` `/operator/profile` page.
    * **`/operator/profile`** will just display the current user's quota utilization in read only mode.

### *) Migration

* All existing users will be added with following data using a script:
    ```json
    "llm_quota": {
        "reset_days": 7,
        "dollars_per_period": 1,
        "dollars_used": 0,
        "last_reset": 0,
        "enabled":true
    }
    ```
* all existing bot confugurations will be added with following data using a script
    ```json
    "bot_configuration": {
        "configurations":{
            "user_details": {
                "activated":false
            }
        }
    }
    ```