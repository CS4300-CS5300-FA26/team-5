# Story 12: Profile Customization

Feature: Profile Customization
    Scenario: Change display name
        Given I am logged in as "tom"
        When I change my username to "Tom"
        Then I see "Your username has been updated!"
