Feature: Avatar upload
    As a logged-in user
    I want to upload an avatar
    So that it appears on the far right of the navbar

    Background:
        Given uploads are stored in a temporary media folder
        ANd I am logged in as "frank"

    Scenario: Navbar shows an initial when no avatar is stored
        When I open the change avatar page
        Then the navbar shows the initial placeholder
        And the settings dropdown has a "Change Avatar" link

    Scenario: Uploading a valid image
        When I open the change avatar page
        And I upload a valid image named "me.png"
        Then I should see the message "Avatar updated."

    Scenario: Uploading a file that is not an image
        When I open the change avatar page
        And I upload a fake image named "fake.png"
        Then my avatar is not saved
        And the navbar shows the initial placeholder

    Scenario: Removing an avatar
        Given I have uploaded an avatar
        When I remove my avatar
        Then I should see the message "Avatar removed."
        And the navbar shows the initial placeholder
